# Makefile for creating Census geography data for 2010 from source rather than S3
s3_bucket = eviction-lab-etl-data
census_ftp_base = ftp://ftp2.census.gov/geo/tiger/GENZ2010/

block-groups-pattern = gz_*_*_150_*_500k.zip
tracts-pattern = gz_*_*_140_*_500k.zip
cities-pattern = gz_*_*_160_*_500k.zip
counties-pattern = gz_*_*_050_*_500k.zip
states-pattern = gz_*_*_040_*_500k.zip

block-groups-geoid = "this.properties.GEOID = this.properties.STATE + this.properties.COUNTY + this.properties.TRACT + this.properties.BLKGRP"
tracts-geoid = "this.properties.GEOID = this.properties.STATE + this.properties.COUNTY + this.properties.TRACT"
cities-geoid = "this.properties.GEOID = this.properties.STATE + this.properties.PLACE"
counties-geoid = "this.properties.GEOID = this.properties.STATE + this.properties.COUNTY"
states-geoid =  "this.properties.GEOID = this.properties.STATE"

geo_types = states counties cities tracts block-groups
GENERATED_FILES = $(foreach t, $(geo_types), census/$(t).geojson)

.PHONY: all deploy help

## all                 : Create all census GeoJSON
all: $(GENERATED_FILES)

# Based on https://swcarpentry.github.io/make-novice/08-self-doc/
## help                : Print help
help: census.mk
	perl -ne '/^## / && s/^## //g && print' $<

## deploy              : Deploy gzipped census data to S3
deploy: $(foreach f, $(GENERATED_FILES), $(f).gz)
	for f in $^; do aws s3 cp $$f s3://$(s3_bucket)/$$f --acl=public-read; done

## census/%.geojson.gz : Gzip census GeoJSON
census/%.geojson.gz: census/%.geojson
	gzip $<

## census/%.geojson    : Download and clean census GeoJSON
.SECONDARY:
census/%.geojson:
	mkdir -p census/$*
	wget --no-use-server-timestamps -np -nd -r -P census/$* -A '$($*-pattern)' $(census_ftp_base)
	for f in ./census/$*/*.zip; do unzip -d ./census/$* $$f; done
	mapshaper ./census/$*/*.shp combine-files \
		-each $($*-geoid) \
		-filter "!this.properties.GEOID.startsWith('72')" \
		-filter-fields GEOID \
		-o $@ combine-layers format=geojson
	python3 scripts/convert_census_geojson.py $@