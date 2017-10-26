s3_base = https://s3.amazonaws.com/eviction-lab-data/
tippecanoe_opts = --attribute-type=GEOID:string --simplification=10 --maximum-zoom=10 --no-tile-stats --force
tile_join_opts = --no-tile-size-limit --force --no-tile-stats

years = 90 00 10
year_ints = 0 1 2 3 4 5 6 7 8 9
geo_types = states counties zip-codes cities tracts block-groups
geo_years = $(foreach y,$(years),$(foreach g,$(geo_types),$g-$y))

states_min_zoom = 2
counties_min_zoom = 2
cities_min_zoom = 4
zip-codes_min_zoom = 6
tracts_min_zoom = 6
block-groups_min_zoom = 7

states_bytes = 1000000
counties_bytes = 5000000
cities_bytes = 200000
zip-codes_bytes = 200000
tracts_bytes = 200000
block-groups_bytes = 200000

census_opts = --detect-shared-borders --coalesce-smallest-as-needed
small_tile_census_opts = --low-detail=10 --grid-low-zooms $(census_opts)

# Assign layer properties based on minimum zoom
$(foreach g, $(geo_types), $(eval $(g)_census_opts = --minimum-zoom=$($g_min_zoom) --maximum-tile-bytes=$($g_bytes) $(small_tile_census_opts)))
$(foreach g, $(geo_types), $(eval $(g)_centers_opts = -B$($g_min_zoom) --maximum-tile-bytes=1000000))
states_census_opts = --minimum-zoom=$(states_min_zoom) $(census_opts)
counties_census_opts = --minimum-zoom=$(counties_min_zoom) $(census_opts) --maximum-tile-bytes=$(counties_bytes)

mapshaper_cmd = node --max_old_space_size=4096 $$(which mapshaper)

# For comma-delimited list
null :=
space := $(null) $(null)
comma := ,

# Don't delete files created throughout on completion
.PRECIOUS: tilesets/%.mbtiles tiles/%.mbtiles census/%.geojson census/%.mbtiles centers/%.mbtiles
.PHONY: all clean deploy

all: $(foreach t, $(geo_years), tiles/$(t).mbtiles)

clean:
	rm -rf centers data grouped_data census_data centers_data json tiles tilesets

## Submit job to AWS Batch
submit_jobs:
	for g in $(geo_years); do aws batch submit-job --job-name etl-job --job-definition eviction-lab-etl-job --job-queue eviction-lab-etl-job-queue --container-overrides command="make tiles/$(g).mbtiles && make deploy"; done

## Create directories with .pbf file tiles for deployment to S3
deploy:
	mkdir -p tilesets
	for f in tiles/*.mbtiles; do tile-join --no-tile-size-limit --force -e ./tilesets/evictions-$$(basename "$${f%.*}") $$f; done
	aws s3 cp ./tilesets s3://eviction-lab-tilesets/fixtures --recursive --acl=public-read --content-encoding=gzip --region=us-east-2

### MERGE TILES

## Convert geography GeoJSON to .mbtiles
tiles/%.mbtiles: census_data/%.mbtiles centers_data/%.mbtiles
	mkdir -p tiles
	tile-join $(tile_join_opts) -o $@ $^

# Join centers tiles to data for eviction rates
.SECONDEXPANSION:
centers_data/%.mbtiles: centers_data/%.csv centers/$$(subst -$$(lastword $$(subst -, ,$$*)),,$$*).mbtiles
	tile-join -l $(subst -$(lastword $(subst -, ,$*)),,$*)-centers --if-matched -x GEOID $(tile_join_opts) -o $@ -c $^ 

# Get eviction rate properties and GEOID for centers
centers_data/%.csv: year_data/%.csv
	mkdir -p centers_data
	cat $< | python3 scripts/subset_cols.py GEOID,n,$(subst $(space),$(comma),$(filter er-%,$(subst $(comma),$(space),$(shell head -n 1 $<)))) | \
		perl -ne 'if ($$. == 1) { s/"//g; } print;' > $@

# Create census shape tiles from joining data and geography tiles
.SECONDEXPANSION:
census_data/%.mbtiles: year_data/%.csv census/$$(subst -$$(lastword $$(subst -, ,$$*)),,$$*).mbtiles
	mkdir -p census_data
	tile-join -l $(subst -$(lastword $(subst -, ,$*)),,$*) --if-matched -x GEOID $(tile_join_opts) -o $@ -c $^

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
	$(mapshaper_cmd) -i $@ field-types=GEOID:str \
		-each "this.properties.west = this.bounds[0]; this.properties.south = this.bounds[1]; this.properties.east = this.bounds[2]; this.properties.north = this.bounds[3];" \
		-o $@ force

### DATA

## Get data for a given year by the last two digits
## Secondary expansion allows processing of source so that states-10.csv comes from states.csv
.SECONDEXPANSION:
year_data/%.csv: grouped_data/$$(subst -$$(lastword $$(subst -, ,$$*)),,$$*).csv
	mkdir -p year_data
	$(eval year_str=$(shell echo $(lastword $(subst -, ,$*)) | head -c 1))
	$(eval cols=$(subst $(comma),$(space),$(shell head -n 1 $<)))
	$(eval year_patterns=$(foreach i,$(year_ints),%-$(year_str)$(i)))
	cat $< | python3 scripts/subset_cols.py GEOID,n,pl,$(subst $(space),$(comma),$(filter $(year_patterns),$(cols))) | \
		perl -ne 'if ($$. == 1) { s/"//g; } print;' > $@

## Group data by FIPS code with columns for {ATTR}-{YEAR}
grouped_data/%.csv: data/%.csv
	mkdir -p grouped_data
	cat $< | python3 scripts/group_census_data.py | perl -ne 'if ($$. == 1) { s/"//g; } print;' > $@

## Pulls fixture data, uncomment below targets for real data
data/%.csv:
	mkdir -p data
	wget -O $@.gz $(s3_base)fixture-$@.gz
	gunzip $@.gz

## Fetch Excel data, combine into CSV files
# data/%.csv: data/%.xlsx
# 	in2csv $< > $@

## Get source data from S3 bucket Excel files
# data/%.xlsx:
# 	mkdir -p data
# 	wget -P data $(s3_base)$@
