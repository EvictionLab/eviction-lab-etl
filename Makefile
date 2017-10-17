s3_base = https://s3.amazonaws.com/eviction-lab-data/
tippecanoe_opts = --simplification=10 --maximum-zoom=10 --maximum-tile-bytes=1000000 --low-detail=10 --force
tile_join_opts = --no-tile-size-limit --force

geo_types = states counties zip-codes cities tracts block-groups

states_min_zoom = 2
counties_min_zoom = 2
cities_min_zoom = 4
zip-codes_min_zoom = 6
tracts_min_zoom = 7
block-groups_min_zoom = 9

census_opts = --detect-shared-borders --coalesce-smallest-as-needed
# Assign layer properties based on minimum zoom
$(foreach g, $(geo_types), $(eval $(g)_census_opts = --minimum-zoom=$($g_min_zoom) $(census_opts)))
$(foreach g, $(geo_types), $(eval $(g)_centers_opts = -B$($g_min_zoom)))

mapshaper_cmd = node --max_old_space_size=4096 $$(which mapshaper)

# For comma-delimited list
null :=
space := $(null) $(null)
comma := ,

# Don't delete files created throughout on completion
.PRECIOUS: tilesets/%.mbtiles json/united-states-search.json tiles/%.mbtiles census/%.geojson
# Delete files that are intermediate dependencies, not final products
.INTERMEDIATE: data/%.xlsx data/%.csv centers/%.geojson grouped_data/%.csv
.PHONY: all clean deploy

all: $(foreach t, $(geo_types), tiles/$(t).mbtiles)

clean:
	rm -rf centers data grouped_data census_data centers_data json tiles tilesets

## Submit job to AWS Batch
submit_job:
	aws batch submit-job --job-name etl-job --job-definition eviction-lab-etl-job --job-queue eviction-lab-etl-job-queue

## Create directories with .pbf file tiles for deployment to S3
deploy: all
	mkdir -p tilesets
	for f in $(geo_types); do tile-join --no-tile-size-limit --force -e ./tilesets/evictions-$$f ./tiles/$$f.mbtiles; done
	aws s3 cp ./tilesets s3://eviction-lab-tilesets --recursive --acl=public-read --content-encoding=gzip --region=us-east-2
	aws s3 cp $< s3://eviction-lab-tilesets/$(notdir $<) --acl=public-read --region=us-east-2
	aws s3 cp search s3://eviction-lab-tilesets/search --acl=public-read --region=us-east-2

### MERGE TILES

## Convert geography GeoJSON to .mbtiles
tiles/%.mbtiles: census_data/%.mbtiles centers_data/%.mbtiles
	mkdir -p tiles
	tile-join $(tile_join_opts) -o $@ $^

# Join centers tiles to data for eviction rates
centers_data/%.mbtiles: centers_data/%.csv centers/%.mbtiles
	tile-join -l $*-centers --if-matched -x GEOID $(tile_join_opts) -o $@ -c $^ 

# Get eviction rate properties and GEOID for centers
centers_data/%.csv: grouped_data/%.csv
	mkdir -p centers_data
	csvcut -c GEOID,$(subst $(space),$(comma),$(filter er-%,$(subst $(comma),$(space),$(shell head -n 1 $<)))) $< > $@

# Create census shape tiles from joining data and geography tiles
census_data/%.mbtiles: grouped_data/%.csv census/%.mbtiles
	mkdir -p census_data
	tile-join -l $* --if-matched -x GEOID $(tile_join_opts) -o $@ -c $^

### SEARCH - currently disabled, reenable with json/united-states-search.json target

## General search file, and search index files from first or first two characters of name
json/united-states-search.json: grouped_data/united-states.csv grouped_data/united-states-centers.csv
	mkdir -p search
	python scripts/create_search_index.py $^ $@ search

## Convert the united-states-centers.geojson to CSV for merge later
grouped_data/united-states-centers.csv: json/united-states-centers.geojson
	in2csv --format geojson $< | csvcut -c GEOID,layer,longitude,latitude > $@

## Create combined GeoJSON file with all center points, layer added as property
json/united-states-centers.geojson: $(foreach g, $(geo_types), centers/$(g).geojson)
	mkdir -p json
	for g in $(geo_types); do mapshaper -i centers/$$g.geojson -each "this.properties.layer = \"$$g\"" -o centers/$$g.geojson format=geojson force; done
	mapshaper -i $^ combine-files -merge-layers -o $@ format=geojson

## Combined CSV data
grouped_data/united-states.csv: $(foreach g, $(geo_types), grouped_data/$(g).csv)
	mkdir -p grouped_data
	head -n 1 $< | perl -ne 'print "layer," . $$_' > $@
	for g in $(geo_types); do perl -ne 'print "$$g," . $$_ if $$. != 1' grouped_data/$$g.csv >> $@; done

### GEOGRAPHY 

## Center .mbtiles with flags for centers based on layer
centers/%.mbtiles: centers/%.geojson
	tippecanoe -L $*-centers:$< $(tippecanoe_opts) $($*_centers_opts) -o $@

## Census .mbtiles with specific flags for census geography
census/%.mbtiles: census/%.geojson
	tippecanoe -L $*:$< $(tippecanoe_opts) $($*_census_opts) -o $@

## GeoJSON centers
centers/%.geojson: census/%.geojson
	mkdir -p centers
	geojson-polygon-labels --by-feature $< > $@

## Census GeoJSON from S3 bucket
census/%.geojson:
	mkdir -p census
	wget -P census $(s3_base)$@.gz
	gunzip $@.gz
	$(mapshaper_cmd) -i - field-types=GEOID:str \
		-each "this.properties.west = this.bounds[0]; this.properties.south = this.bounds[1]; this.properties.east = this.bounds[2]; this.properties.north = this.bounds[3];" \
		-o $@ force

### DATA

## Group data by FIPS code with columns for {ATTR}-{YEAR}
grouped_data/%.csv: data/%.csv
	mkdir -p grouped_data
	cat $< | python scripts/group_census_data.py > $@

## Fetch Excel data, combine into CSV files
data/%.csv: data/%.xlsx
	in2csv $< > $@

## Get source data from S3 bucket Excel files
data/%.xlsx:
	mkdir -p data
	wget -P data $(s3_base)$@