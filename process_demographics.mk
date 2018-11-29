# Tasks to processes raw census data and map 2000 data to 2010 geography

years = 00 10
geo_types = states counties cities tracts block-groups
geo_years = $(foreach y,$(years),$(foreach g,$(geo_types),$g-$y))
output_files = $(foreach f, $(geo_types), data/demographics/$(f).csv)
build_date := $(shell date +%F)
ts := $(shell date "+%H%M%S")

.PRECIOUS: census/00/%.csv data/demographics/%.csv
.PHONY: all clean deploy deploy_logs

## all                                         : Create all demographics data
all: $(output_files)

## clean                                       : Remove created demographics files
clean:
	rm -f data/demographics/*.csv
	rm -f log/*.txt

# Based on https://swcarpentry.github.io/make-novice/08-self-doc/
## help                                        : Print help
help: demographics.mk
	perl -ne '/^## / && s/^## //g && print' $<

## deploy                                      : Compress demographic data and deploy to S3
deploy:
	for f in data/demographics/*.csv; do gzip $$f; done
	for f in data/demographics/*.gz; do aws s3 cp $$f s3://$(S3_SOURCE_DATA_BUCKET)/demographics/$(build_date)/$$(basename $$f); done

deploy_logs:
	cat log/*.txt > log/$(ts)_process_log.txt
	aws s3 cp log/$(ts)_process_log.txt s3://$(S3_SOURCE_DATA_BUCKET)/demographics/$(build_date)/$(ts)_process_log.txt
	rm -f log/*.txt

## submit_jobs                                 : Submit jobs to AWS Batch
submit_jobs:
	python3 utils/submit_jobs.py $(output_files)

### DEMOGRAPHIC DATA

## data/demographics/%.csv                     : Create crosswalked demographic data for geographies
data/demographics/%.csv: $(foreach y, $(years), data/demographics/years/%-$(y).csv)
	csvstack $^ | python3 scripts/convert_crosswalk_geo.py $* > $@

## data/demographics/years/%.csv               : Create demographic data grouped by geography and year
data/demographics/years/%.csv:
	mkdir -p $(dir $@)
	cat data/demographics/raw/$*.csv | python3 scripts/convert_census_vars.py > $@

## data/demographics/years/tracts-00.csv       : Create tracts-00 demographics, convert with weights
data/demographics/years/tracts-00.csv: census/00/tracts-weights.csv
	mkdir -p $(dir $@)
	cat data/demographics/raw/tracts-00.csv | \
	python3 scripts/convert_00_geo.py tracts census/00/tracts-weights.csv | \
	python3 scripts/convert_census_vars.py > $@

## data/demographics/years/block-groups-00.csv : Create block-groups-00 demographics, convert with weights
data/demographics/years/block-groups-00.csv: census/00/block-groups-weights.csv
	mkdir -p $(dir $@)
	cat data/demographics/raw/block-groups-00.csv | \
	python3 scripts/convert_00_geo.py block-groups $< | \
	python3 scripts/convert_census_vars.py > $@

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
