## Makefile for creating Census data 2010-2016 from source rather than S3
census_ftp_base = ftp://ftp2.census.gov/geo/tiger/GENZ

block-groups-pattern = cb_*_*_bg_500k.zip
tracts-pattern = cb_*_*_tract_500k.zip
cities-pattern = cb_*_*_place_500k.zip
counties-pattern = cb_*_us_county_500k.zip
states-pattern = cb_*_us_state_500k.zip
zip-codes-pattern = cb_*_us_zcta510_500k.zip

# Including more years than necessary for proof of concept
years = 2010 2011 2012 2013 2014 2015 2016
geo_types = states counties zip-codes cities tracts block-groups
geo_years = $(foreach y,$(years),$(foreach g,$(geo_types),$g-$y))

.PHONY: all

all: $(foreach t, $(geo_years), census/$(t).geojson)

## Census GeoJSON
census/%.geojson:
	mkdir -p census/$*
	wget -np -nd -r -P census/$* -A '$($*-pattern)' $(census_ftp_base)$(lastword $(subst -, ,$*))/shp/
	for f in ./census/$*/*.zip; do unzip -d ./census/$* $$f; done
	mapshaper ./census/$*/*.shp combine-files \
		-each "this.properties.GEOID = '000' + this.properties.GEOID10" where="this.properties.GEOID10" \
		-o $@ combine-layers format=geojson