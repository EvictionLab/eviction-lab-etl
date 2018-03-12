s3_base = https://s3.amazonaws.com/eviction-lab-data/
years = 00 10
geo_types = states counties cities tracts block-groups
geo_years = $(foreach y,$(years),$(foreach g,$(geo_types),$g-$y)) msa-10

county_fips = $(shell cat conf/fips_codes.txt)

output_files = $(foreach f, $(geo_types), data/demographics/$(f).csv)

.SECONDARY: $(foreach f, $(county_fips), census/%/block-groups/$(f).csv)
.PHONY: all clean deploy

## all                                         : Create all demographics data
all: $(output_files)

## clean                                       : Remove created demographics files
clean:
	rm -rf data/demographics

# Based on https://swcarpentry.github.io/make-novice/08-self-doc/
## help                                        : Print help
help: demographics.mk
	perl -ne '/^## / && s/^## //g && print' $<

## deploy                                      : Compress demographic data and deploy to S3
deploy:
	for f in data/demographics/*.csv; do gzip $$f; done
	for f in data/demographics/*.gz; do aws s3 cp $$f s3://eviction-lab-data/demographics/$$(basename $$f) --acl=public-read; done

### DEMOGRAPHIC DATA

## data/demographics/%.csv                     : Create crosswalked demographic data for each geography and year group
data/demographics/%.csv: $(foreach y, $(years), data/demographics/years/%-$(y).csv)
	csvstack $^ | python3 scripts/convert_crosswalk_geo.py $* > $@

## data/demographics/msa.csv                   : Copy over MSA data
data/demographics/msa.csv: data/demographics/years/msa-10.csv
	cp $< $@

## data/demographics/years/%.csv               : Create demographic data grouped by geography and year
data/demographics/years/%.csv:
	mkdir -p $(dir $@)
	python3 scripts/create_data_demographics.py $* > $@

## data/demographics/years/tracts-00.csv       : Create tracts-00 demographics, convert with weights
data/demographics/years/tracts-00.csv: census/00/tracts-weights.csv
	mkdir -p $(dir $@)
	python3 scripts/create_data_demographics.py tracts-00 > $@
	python3 scripts/convert_00_geo.py tracts $@ $<

## data/demographics/years/block-groups-00.csv : Create block-groups-00 demographics, convert with weights
data/demographics/years/block-groups-00.csv: census/00/block-groups-weights.csv census/00/block-groups.csv
	mkdir -p $(dir $@)
	python3 scripts/create_data_demographics.py block-groups-00 > $@
	python3 scripts/convert_00_geo.py block-groups $@ $<

## data/demographics/years/block-groups-10.csv : Create block-groups-10 demographics
data/demographics/years/block-groups-10.csv: census/10/block-groups.csv
	mkdir -p $(dir $@)
	python3 scripts/create_data_demographics.py block-groups-10 > $@

## census/%/block-groups.csv                   : Consolidate block groups by county
census/%/block-groups.csv: $(foreach f, $(county_fips), census/%/block-groups/$(f).csv)
	csvstack $^ > $@

## census/10/block-groups/%.csv                : Create 2010 block groups files
census/10/block-groups/%.csv:
	mkdir -p $(dir $@)
	$(eval y=$(subst census/,,$(subst /block-groups/$(notdir $@),,$@)))
	python3 scripts/create_block_groups.py $* $(y) > $@

## census/00/block-groups/%.csv                : Create 2000 block groups files
census/00/block-groups/%.csv:
	mkdir -p $(dir $@)
	$(eval y=$(subst census/,,$(subst /block-groups/$(notdir $@),,$@)))
	python3 scripts/create_block_groups.py $* $(y) > $@

### WEIGHTS

## census/00/%-weights.csv                     : Generate weights for 2000 census geographies
census/00/%-weights.csv: census/00/geocorr.csv census/00/nhgis_blk2000_blk2010_ge.csv
	python3 scripts/create_00_weights.py $* $^ > $@

# Uses estimates of geography breakdown from Missouri Census Data Center http://mcdc2.missouri.edu/websas/geocorr2k.html
## census/00/geocorr.csv                       : Download Missouri Census Data Center geography weights
census/00/geocorr.csv:
	mkdir -p $(dir $@)
	wget -O $@.gz $(s3_base)relationships/$(notdir $@).gz
	gunzip $@.gz

## census/00/nhgis_blk2000_blk2010_ge.csv      : Download NHGIS 2000 data crosswalks
census/00/nhgis_blk2000_blk2010_ge.csv: census/00/crosswalks.zip
	unzip -d $(dir $@) $<
	touch $@

## census/00/crosswalks.zip                    : Download NHGIS block group crosswalks zip file
.INTERMEDIATE:
census/00/crosswalks.zip:
	mkdir -p $(dir $@)
	wget -O $@ http://assets.nhgis.org/crosswalks/nhgis_blk2000_blk2010_ge.zip
