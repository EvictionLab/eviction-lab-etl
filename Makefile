s3_base = https://s3.amazonaws.com/eviction-lab-data/census/
tippecanoe_opts = --detect-shared-borders --no-tile-size-limit --simplification=10 -B 2 --force --maximum-zoom=10

document_id = "1sXrLIcB-AhIftHIIksmHNvzAuXwpWuIBzSIcBhP0YNA"
column-headers-2010 = GEOID,year,evictions,name,parent-location,population,area,average-household-size,renting-occupied-households,poverty-rate,eviction-rate

block-groups-2010-sheet = 1649065693
tracts-2010-sheet = 43684946
cities-2010-sheet = 256916247
counties-2010-sheet = 1698481076
states-2010-sheet = 1452248278
zip-codes-2010-sheet = 708732124

block-groups-2010-row = print "\"" $$2 "\"," $$1 "," $$3 "," substr($$4, 2) ",\"" substr($$5, 2) "," $$6 "," $$7 "," $$8 "," $$9 "," $$10 "," $$11 "," $$12 "," $$13
tracts-2010-row = print "\"" $$2 "\"," $$1 "," $$3 "," substr($$4, 2) ",\"" substr($$5, 2) "," $$5 "," $$6 "," $$7 "," $$8 "," $$9 "," $$10 "," $$11 "," $$12
cities-2010-row = print "\"" $$2 "\"," $$1 "," $$3 "," $$4 ", ," $$5 "," $$6 "," $$7 "," $$8 "," $$9 "," $$10
counties-2010-row = print "\"" $$2 "\"," $$1 "," $$3 "," substr($$4, 2) ",\"" substr($$5, 2) "," $$6 "," $$7 "," $$8 "," $$9 "," $$10 "," $$11
states-2010-row = print "\"" $$2 "\"," $$1 "," $$3 "," $$4 ",USA," $$5 "," $$6 "," $$7 "," $$8 "," $$9 "," $$10
zip-codes-2010-row = print "\"000" substr($$2, 4) "\"," $$1 "," $$3 ",Zip Code " substr($$2, 4) ",Parent Unknown," $$5 "," $$6 "," $$7 "," $$8 "," $$9 "," $$10

years = 2010
geo_types = states counties zip-codes cities tracts block-groups
geo_years = $(foreach y,$(years),$(foreach g,$(geo_types),$g-$y))

# Don't delete files created throughout on completion
.PRECIOUS: tilesets/%.mbtiles json/united-states-geo-names.json data/united-states.csv data/%.csv tiles/%.mbtiles centers/%.geojson census/%.geojson

.PHONY: all clean deploy

all: json/united-states-geo-names.json $(foreach t, $(geo_years), data_tiles/$(t).mbtiles)

clean:

deploy: $(foreach t, $(geo_years), data_tiles/$(t).mbtiles)
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
## NOTE: Using just 2010 initially, but could use all with geo_years
data/united-states.csv: $(foreach g, $(geo_types), data/$(g)-2010.csv)
	mkdir -p data
	echo "$(column_headers)\n" > $@
	for f in $^; do perl -ne 'print if $$. != 1' $$f >> $@; done

## Fetch Google Sheets data, combine into CSV files
data/%.csv:
	mkdir -p data
	echo "$(column-headers-$(lastword $(subst -, ,$*)))" > $@
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

## Census GeoJSON from S3 bucket
census/%.geojson:
	mkdir -p census
	wget -P census $(s3_base)$*.geojson.gz
	gunzip $@.gz