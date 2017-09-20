## Makefile for creating Census geography data for 1990, 2000, 2010 from source rather than S3
census_ftp_base = ftp://ftp2.census.gov/geo/tiger/GENZ
census_ftp_base_2010 = $(census_ftp_base)2010/shp/
census_ftp_base_2016 = $(census_ftp_base)2016/shp/
# File layout for 1990, 2000 described here https://www.census.gov/geo/maps-data/data/prev_cartbndry_names.html
census_ftp_base_pre = ftp://ftp2.census.gov/geo/tiger/PREVGENZ/
census_ftp_base_1990 = $(census_ftp_base_pre)
census_ftp_base_2000 = $(census_ftp_base_pre)

recent-each-func = "this.properties.GEOID = '000' + this.properties.GEOID10" where="this.properties.GEOID10"
recent-years = 2010 2016

block-groups-1990-each-func = "this.properties.GEOID = this.properties.ST + this.properties.CO + this.properties.TRACT + this.properties.BG"
tracts-each-1990-func = "if (this.properties.TRACTSUF) { this.properties.GEOID = this.properties.ST + this.properties.CO + this.properties.TRACTBASE + this.properties.TRACTSUF; } else { this.properties.GEOID = this.properties.ST + this.properties.CO + this.properties.TRACTBASE + '00'; }"
cities-each-1990-func = "this.properties.GEOID = this.properties.GEOID"
counties-each-1990-func = "this.properties.GEOID = this.properties.ST + this.properties.CO"
states-each-1990-func = "this.properties.GEOID = this.properties.ST"

block-groups-2000-each-func = "this.properties.GEOID = this.properties.STATE + this.properties.COUNTY + this.properties.TRACT + this.properties.BLKGROUP"
tracts-each-2000-func = "this.properties.GEOID = this.properties.STATE + this.properties.COUNTY + this.properties.TRACT"
cities-each-2000-func = "this.properties.GEOID = this.properties.STATE + this.properties.PLACEFP"
counties-each-2000-func = "this.properties.GEOID = this.properties.STATE + this.properties.COUNTY"
states-each-2000-func = "this.properties.GEOID = this.properties.STATE"
zip-codes-each-2000-func = "this.properties.GEOID = '000' + this.properties.ZCTA"

block-groups-1990-pattern = bg*_d90_shp.zip
tracts-1990-pattern = tr*_d90_shp.zip
cities-1990-pattern = pl*_d90_shp.zip
counties-1990-pattern = co*_d90_shp.zip
states-1990-pattern = st*_d90_shp.zip
zip-codes-1990-pattern = zt*_d90_shp.zip

block-groups-2000-pattern = bg*_d00_shp.zip
tracts-2000-pattern = tr*_d00_shp.zip
cities-2000-pattern = pl*_d00_shp.zip
counties-2000-pattern = co*_d00_shp.zip
states-2000-pattern = st*_d00_shp.zip
zip-codes-2000-pattern = zt*_d00_shp.zip

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

years = 1990 2000 2010
geo_types = states counties zip-codes cities tracts block-groups
geo_years = $(foreach y,$(years),$(foreach g,$(geo_types),$g-$y))

.PHONY: all

all: $(foreach t, $(geo_years), census/$(t).geojson)

## Create manual override for 1990 zip codes because not included
census/zip-codes-1990.geojson:
	touch census/zip-codes-1990.geojson

## Census GeoJSON
census/%.geojson:
	mkdir -p census/$*
	$(eval year=$(lastword $(subst -, ,$*)))
	$(eval geo=$(subst -$(year),,$*))
	wget -np -nd -r -P census/$* -A '$($*-pattern)' $(census_ftp_base_$(year))
	for f in ./census/$*/*.zip; do unzip -d ./census/$* $$f; done
	mapshaper ./census/$*/*.shp combine-files \
		-each $(if $(findstring $(year),$(recent-years)),$(recent-each-func),$($(geo)-each-$(year)-func)) \
		-filter-fields GEOID \
		-o $@ combine-layers format=geojson