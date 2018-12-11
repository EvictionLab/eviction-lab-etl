
BUILD_ID?=2018-11-28
mapshaper_cmd = node --max_old_space_size=4096 $$(which mapshaper)


.PHONY: help

# Based on https://swcarpentry.github.io/make-novice/08-self-doc/
## help                                        : Print help
help: process_demographics.mk
	perl -ne '/^## / && s/^## //g && print' $<

## data/demogaphics/raw/%.csv           : get raw demographic data from S3 bucket
data/demogaphics/raw/%.csv:
	mkdir -p $(dir $@)
	aws s3 cp s3://$(S3_SOURCE_DATA_BUCKET)/$(BUILD_ID)/demogaphics/raw/$*.csv.gz - | \
	gunzip -c > $@

## data/demogaphics/%.csv           : get crosswalked demographic data from S3 bucket
data/demogaphics/%.csv:
	mkdir -p $(dir $@)
	aws s3 cp s3://$(S3_SOURCE_DATA_BUCKET)/$(BUILD_ID)/demogaphics/$*.csv.gz - | \
	gunzip -c > $@

## data/%.csv                       : get eviction / demographic data from S3 bucket
data/%.csv:
	mkdir -p $(dir $@)
	aws s3 cp s3://$(S3_SOURCE_DATA_BUCKET)/$(BUILD_ID)/$*.csv.gz - | \
	gunzip -c > $@

## census/%.geojson                 : Census GeoJSON from S3 bucket
census/%.geojson:
	mkdir -p $(dir $@)
	aws s3 cp s3://$(S3_SOURCE_DATA_BUCKET)/$(BUILD_ID)/$@.gz - | \
	gunzip -c | \
	$(mapshaper_cmd) -i - field-types=GEOID:str \
		-each "this.properties.west = +this.bounds[0].toFixed(4); \
			this.properties.south = +this.bounds[1].toFixed(4); \
			this.properties.east = +this.bounds[2].toFixed(4); \
			this.properties.north = +this.bounds[3].toFixed(4);" \
		-o $@