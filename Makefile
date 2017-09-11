census_ftp_base = ftp://ftp2.census.gov/geo/tiger/GENZ2016/shp/

block-groups-pattern = cb_2016_*_bg_500k.zip
tracts-pattern = cb_2016_*_tract_500k.zip
cities-pattern = cb_2016_*_place_500k.zip
counties-pattern = cb_2016_us_county_500k.zip
states-pattern = cb_2016_us_state_500k.zip
zip-codes-pattern = cb_2016_us_zcta510_500k.zip

tippecanoe_opts = --detect-shared-borders --no-tile-size-limit --simplification=10 -B 2 --force --maximum-zoom=10

document_id = "1sXrLIcB-AhIftHIIksmHNvzAuXwpWuIBzSIcBhP0YNA"
column_headers = GEOID,year,evictions,name,parent-location,population,area,average-household-size,renting-occupied-households,poverty-rate,eviction-rate

block-groups-sheet = 1649065693
tracts-sheet = 43684946
cities-sheet = 256916247
counties-sheet = 1698481076
states-sheet = 1452248278
zip-codes-sheet = 708732124

block-groups-row = print "\"" $$2 "\"," $$1 "," $$3 "," substr($$4, 2) ",\"" substr($$5, 2) "," $$6 "," $$7 "," $$8 "," $$9 "," $$10 "," $$11 "," $$12 "," $$13
tracts-row = print "\"" $$2 "\"," $$1 "," $$3 "," substr($$4, 2) ",\"" substr($$5, 2) "," $$5 "," $$6 "," $$7 "," $$8 "," $$9 "," $$10 "," $$11 "," $$12
cities-row = print "\"" $$2 "\"," $$1 "," $$3 "," $$4 ", ," $$5 "," $$6 "," $$7 "," $$8 "," $$9 "," $$10
counties-row = print "\"" $$2 "\"," $$1 "," $$3 "," substr($$4, 2) ",\"" substr($$5, 2) "," $$6 "," $$7 "," $$8 "," $$9 "," $$10 "," $$11
states-row = print "\"" $$2 "\"," $$1 "," $$3 "," $$4 ",USA," $$5 "," $$6 "," $$7 "," $$8 "," $$9 "," $$10
zip-codes-row = print "\"000" substr($$2, 4) "\"," $$1 "," $$3 ",Zip Code " substr($$2, 4) ",Parent Unknown," $$5 "," $$6 "," $$7 "," $$8 "," $$9 "," $$10

geo_types = states counties zip-codes cities tracts block-groups

# Don't delete files created throughout on completion
.PRECIOUS: tilesets/%.mbtiles json/united-states-geo-names.json data/united-states.csv data/%.csv tiles/%.mbtiles centers/%.geojson census/%.geojson

.PHONY: all clean deploy

all: json/united-states-geo-names.json $(foreach t, $(geo_types), data_tiles/$(t).mbtiles)

clean:

deploy: $(foreach t, $(geo_types), data_tiles/$(t).mbtiles)
	mkdir -p tilesets
	for f in $(geo_types); do tile-join --no-tile-size-limit --force -e ./tilesets/evictions-$$f ./data_tiles/$$f.mbtiles; done

# Join polygon tiles to data
data_tiles/%.mbtiles: data/%.csv tiles/%.mbtiles
	mkdir -p data_tiles
	tile-join --if-matched --no-tile-size-limit --force -x GEOID -o $@ -c $^

# JSON for autocomplete
json/united-states-geo-names.json: data/united-states.csv
	mkdir -p json
	csvtojson $< --includeColumns='["name","parent-location","population"]' --colParser='{"population":"number"}' > $@

## Combined CSV data
data/united-states.csv: data/block-groups.csv data/tracts.csv data/cities.csv data/counties.csv data/states.csv data/zip-codes.csv
	mkdir -p data
	echo "$(column_headers)\n" > $@
	for f in $^; do perl -ne 'print if $$. != 1' $$f >> $@; done

## Fetch Google Sheets data, combine into CSV files
data/%.csv:
	mkdir -p data
	echo "$(column_headers)" > $@
	curl "https://docs.google.com/spreadsheets/d/$(document_id)/export?gid=$($*-sheet)&format=csv" | \
	awk 'BEGIN { FS = "," } (substr($$1,1,1) ~ /^[0-9]/ ) { $($*-row) }' >> $@ 

## Create tiles from all geographies
tiles/%.mbtiles: census/%.geojson centers/%.geojson
	mkdir -p tiles
	tippecanoe -L $*:$< -L $*-centers:$(word 2,$^) $(tippecanoe_opts) -o $@

## GeoJSON centers
centers/%.geojson: census/%.geojson
	mkdir -p centers
	geojson-polygon-labels --by-feature $< > $@

## Census GeoJSON
census/%.geojson: 
	mkdir -p census/$*
	wget -np -nd -r -P census/$* -A '$($*-pattern)' $(census_ftp_base)
	for f in ./census/$*/*.zip; do unzip -d ./census/$* $$f; done
	mapshaper ./census/$*/*.shp combine-files \
		-each "this.properties.GEOID = '000' + this.properties.GEOID10" where="this.properties.GEOID10" \
		-o $@ combine-layers format=geojson
