## Makefile for creating Census data 2000 and 2010 from source rather than S3
census_ftp_base = ftp://ftp2.census.gov/geo/tiger/GENZ

block-groups-2010-pattern = gz_*_*_150_*_500k.zip
tracts-2010-pattern = gz_*_*_140_*_500k.zip
cities-2010-pattern = gz_*_*_160_*_500k.zip
counties-2010-pattern = gz_*_*_050_*_500k.zip
states-2010-pattern = gz_*_*_040_*_500k.zip
zip-codes-2010-pattern = gz_*_*_860_*_500k.zip

block-groups-2016-pattern = cb_*_*_bg_500k.zip
tracts-2016-pattern = cb_*_*_tract_500k.zip
cities-2016-pattern = cb_*_*_place_500k.zip
counties-2016-pattern = cb_*_us_county_500k.zip
states-2016-pattern = cb_*_us_state_500k.zip
zip-codes-2016-pattern = cb_*_us_zcta510_500k.zip

years = 2010 #2000
geo_types = states counties zip-codes cities tracts block-groups
geo_years = $(foreach y,$(years),$(foreach g,$(geo_types),$g-$y))

.PHONY: all

all: $(foreach t, $(geo_years), census/$(t).geojson)

## Census GeoJSON (works 2010-present)
census/%.geojson:
	mkdir -p census/$*
	wget -np -nd -r -P census/$* -A '$($*-pattern)' $(census_ftp_base)$(lastword $(subst -, ,$*))/shp/
	for f in ./census/$*/*.zip; do unzip -d ./census/$* $$f; done
	mapshaper ./census/$*/*.shp combine-files \
		-each "this.properties.GEOID = '000' + this.properties.GEOID10" where="this.properties.GEOID10" \
		-o $@ combine-layers format=geojson