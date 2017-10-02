s3_base = https://s3.amazonaws.com/eviction-lab-data/census/
tippecanoe_opts = --detect-shared-borders --no-tile-size-limit --simplification=10 -B 2 --force --maximum-zoom=10

document_id = "1sXrLIcB-AhIftHIIksmHNvzAuXwpWuIBzSIcBhP0YNA"
column-headers = GEOID,year,evictions,name,parent-location,population,area,average-household-size,renting-occupied-households,poverty-rate,eviction-rate

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
zip-codes-row = print "\"" substr($$2, 4) "\"," $$1 "," $$3 ",Zip Code " substr($$2, 4) ",Parent Unknown," $$5 "," $$6 "," $$7 "," $$8 "," $$9 "," $$10

geo_types = states counties zip-codes cities tracts block-groups

# Don't delete files created throughout on completion
.PRECIOUS: tilesets/%.mbtiles json/united-states-geo-names.json grouped_data/united-states.csv data_tiles/%.mbtiles census/%.geojson
# Delete files that are intermediate dependencies, not final products
.INTERMEDIATE: data/%.csv tiles/%.mbtiles centers/%.geojson grouped_data/%.csv
.PHONY: all clean deploy

all: json/united-states-geo-names.json $(foreach t, $(geo_types), data_tiles/$(t).mbtiles)

clean:
	rm -rf centers data grouped_data data_tiles json tiles tilesets

## Submit job to AWS Batch
submit_job:
	aws batch submit-job --job-name etl-job --job-definition eviction-lab-etl-job --job-queue eviction-lab-etl-job-queue

## Create directories with .pbf file tiles for deployment to S3
deploy: $(foreach t, $(geo_types), data_tiles/$(t).mbtiles)
	mkdir -p tilesets
	for f in $(geo_types); do tile-join --no-tile-size-limit --force -e ./tilesets/evictions-$$f ./data_tiles/$$f.mbtiles; done
	aws s3 cp ./tilesets s3://eviction-lab-tilesets --recursive --acl=public-read --content-encoding=gzip --region=us-east-2

## Join polygon tiles to data
data_tiles/%.mbtiles: grouped_data/%.csv tiles/%.mbtiles
	mkdir -p data_tiles
	tile-join --if-matched --no-tile-size-limit --force -x GEOID -o $@ -c $^

## JSON for autocomplete
json/united-states-geo-names.json: grouped_data/united-states.csv
	mkdir -p json
	csvcut -c name,parent-location $< | csvjson > $@

## Combined CSV data
grouped_data/united-states.csv: $(foreach g, $(geo_types), grouped_data/$(g).csv)
	mkdir -p grouped_data
	head -n 1 $< > $@
	for f in $^; do perl -ne 'print if $$. != 1' $$f >> $@; done

## Group data by FIPS code with columns for {ATTR}-{YEAR}
grouped_data/%.csv: data/%.csv
	mkdir -p grouped_data
	cat $< | python scripts/group_census_data.py > $@

## Fetch Google Sheets data, combine into CSV files
data/%.csv:
	mkdir -p data
	echo "$(column-headers)" > $@
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