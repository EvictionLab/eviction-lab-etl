## Makefile for creating Census data from source rather than S3
census_ftp_base = ftp://ftp2.census.gov/geo/tiger/GENZ2016/shp/

block-groups-pattern = cb_2016_*_bg_500k.zip
tracts-pattern = cb_2016_*_tract_500k.zip
cities-pattern = cb_2016_*_place_500k.zip
counties-pattern = cb_2016_us_county_500k.zip
states-pattern = cb_2016_us_state_500k.zip
zip-codes-pattern = cb_2016_us_zcta510_500k.zip

geo_types = states counties zip-codes cities tracts block-groups

.PHONY: all

all: $(foreach t, $(geo_types), census/$(t).geojson)

## Census GeoJSON
census/%.geojson:
	mkdir -p census/$*
	wget -np -nd -r -P census/$* -A '$($*-pattern)' $(census_ftp_base)
	for f in ./census/$*/*.zip; do unzip -d ./census/$* $$f; done
	mapshaper ./census/$*/*.shp combine-files \
		-each "this.properties.GEOID = '000' + this.properties.GEOID10" where="this.properties.GEOID10" \
		-o $@ combine-layers format=geojson