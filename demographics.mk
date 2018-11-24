years = 00 10
geo_types = states counties cities tracts block-groups
geo_years = $(foreach y,$(years),$(foreach g,$(geo_types),$g-$y))

county_fips = $(shell cat conf/fips_codes.txt)

census_cols = 'af-am-pop,am-ind-pop,asian-pop,block group,county,hispanic-pop,median-gross-rent,median-household-income,median-property-value,multiple-pop,name,nh-pi-pop,occupied-housing-units,other-pop,population,poverty-pop,rent-burden,renter-occupied-households,state,total-poverty-pop,tract,white-pop,year,GEOID'

output_files = $(foreach f, $(geo_types), data/demographics/$(f).csv)

build_date := $(shell date +%F)
THIS_FILE := $(lastword $(MAKEFILE_LIST))

.PRECIOUS: census/00/%.csv census/10/block-groups/%.csv data/demographics/raw/%.csv data/demographics/%.csv log/%.txt
.SECONDARY: $(foreach f, $(county_fips), census/%/block-groups/$(f).csv)
.PHONY: all clean deploy deploy_raw deploy_logs deploy_years

## all                                         : Create all demographics data
all: $(output_files)

## clean                                       : Remove created demographics files
clean:
	rm -rf data/demographics
	rm -rf log/

# Based on https://swcarpentry.github.io/make-novice/08-self-doc/
## help                                        : Print help
help: demographics.mk
	perl -ne '/^## / && s/^## //g && print' $<

## deploy                                      : Compress demographic data and deploy to S3
deploy: deploy_raw
	for f in data/demographics/*.csv; do gzip $$f; done
	for f in data/demographics/*.gz; do aws s3 cp $$f s3://$(S3_SOURCE_DATA_BUCKET)/demographics/$(build_date)/$$(basename $$f); done

deploy_raw:
	for f in data/demographics/raw/*.csv; do gzip $$f; done
	for f in data/demographics/raw/*.gz; do aws s3 cp $$f s3://$(S3_SOURCE_DATA_BUCKET)/demographics/$(build_date)/raw/$$(basename $$f); done

deploy_logs:
	for f in log/*.txt; do aws s3 cp $$f s3://$(S3_SOURCE_DATA_BUCKET)/demographics/$(build_date)/log/$$(basename $$f); done

## submit_jobs                                 : Submit jobs to AWS Batch
submit_jobs:
	python3 utils/submit_jobs.py $(output_files)

### DEMOGRAPHIC DATA

## data/demographics/%.csv                     : Create crosswalked demographic data for geographies
data/demographics/%.csv: $(foreach y, $(years), data/demographics/years/%-$(y).csv)
	csvstack $^ | python3 scripts/convert_crosswalk_geo.py $* > $@

## log/%.txt
log/%.txt: 
	mv ./log/build_log.txt $@

## data/demographics/raw/%.csv                 : Create raw demographics data fetched from Census API
data/demographics/raw/%.csv:
	mkdir -p $(dir $@)
	python3 scripts/fetch_raw_census_data.py $* > $@

## data/demographics/raw/block-groups-00.csv:
data/demographics/raw/block-groups-00.csv:  census/00/block-groups.csv
	mkdir -p $(dir $@)
	python3 scripts/fetch_raw_census_data.py $* > $@

## data/demographics/raw/block-groups-10.csv:
data/demographics/raw/block-groups-10.csv:  census/10/block-groups.csv
	mkdir -p $(dir $@)
	python3 scripts/fetch_raw_census_data.py $* > $@

## data/demographics/years/%.csv               : Create demographic data grouped by geography and year
data/demographics/years/%.csv: data/demographics/raw/%.csv
	mkdir -p $(dir $@)
	cat $< | python3 scripts/convert_census_vars.py > $@

## data/demographics/years/tracts-00.csv       : Create tracts-00 demographics, convert with weights
data/demographics/years/tracts-00.csv: census/00/tracts-weights.csv data/demographics/raw/tracts-00.csv
	mkdir -p $(dir $@)
	cat data/demographics/raw/tracts-00.csv | \
	python3 scripts/convert_00_geo.py tracts census/00/tracts-weights.csv | \
	python3 scripts/convert_census_vars.py > $@

## data/demographics/years/block-groups-00.csv : Create block-groups-00 demographics, convert with weights
data/demographics/years/block-groups-00.csv: census/00/block-groups-weights.csv data/demographics/raw/block-groups-00.csv
	mkdir -p $(dir $@)
	cat data/demographics/raw/block-groups-00.csv | \
	python3 scripts/convert_00_geo.py block-groups $< | \
	python3 scripts/convert_census_vars.py > $@

## data/demographics/years/block-groups-10.csv : Create block-groups-10 demographics
data/demographics/years/block-groups-10.csv: data/demographics/raw/block-groups-10.csv
	mkdir -p $(dir $@)
	cat data/demographics/raw/block-groups-10.csv | \
	python3 scripts/convert_census_vars.py > $@

## census/%/block-groups.csv                   : Consolidate block groups by county
census/%/block-groups.csv: $(foreach f, $(county_fips), census/%/block-groups/$(f).csv)
	csvstack $^ > $@

## census/10/block-groups/%.csv                : Create 2010 block groups files
census/10/block-groups/%.csv:
	mkdir -p $(dir $@)
	$(eval y=$(subst census/,,$(subst /block-groups/$(notdir $@),,$@)))
	python3 scripts/fetch_raw_block_groups.py $* $(y) | \
	csvcut -c $(census_cols) > $@ 

## census/00/block-groups/%.csv                : Create 2000 block groups files
census/00/block-groups/%.csv:
	mkdir -p $(dir $@)
	$(eval y=$(subst census/,,$(subst /block-groups/$(notdir $@),,$@)))
	python3 scripts/fetch_raw_block_groups.py $* $(y) | \
	csvcut -c $(census_cols) > $@ 

### WEIGHTS

## census/00/%-geocorr.csv                     : Calculate allocation factors for geography level
census/00/%-geocorr.csv: census/00/geocorr.csv
	python3 scripts/recalc_afacts.py $* $^ > census/00/$*-geocorr.csv

## census/00/%-weights.csv                     : Generate weights for 2000 census geographies
census/00/%-weights.csv: census/00/%-geocorr.csv census/00/nhgis_blk2000_blk2010_ge.csv
	python3 scripts/create_00_weights.py $* $^ > $@

# Uses estimates of geography breakdown from Missouri Census Data Center http://mcdc2.missouri.edu/websas/geocorr2k.html
## census/00/geocorr.csv                       : Download Missouri Census Data Center geography weights
census/00/geocorr.csv:
	mkdir -p $(dir $@)
	aws s3 cp s3://$(S3_SOURCE_DATA_BUCKET)/relationships/geocorr.pop2k.gsv.gz - | \
	gunzip > $@

## census/00/nhgis_blk2000_blk2010_ge.csv      : Download NHGIS 2000 data crosswalks
census/00/nhgis_blk2000_blk2010_ge.csv: census/00/crosswalks.zip
	unzip -d $(dir $@) $<
	touch $@

## census/00/crosswalks.zip                    : Download NHGIS block group crosswalks zip file
.INTERMEDIATE:
census/00/crosswalks.zip:
	mkdir -p $(dir $@)
	aws s3 cp s3://$(S3_SOURCE_DATA_BUCKET)/relationships/nhgis_blk2000_blk2010_ge.zip $@
