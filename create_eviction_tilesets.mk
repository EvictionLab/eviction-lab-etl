### The following environment variables must be set

tippecanoe_opts = --attribute-type=GEOID:string --simplification=10 --simplify-only-low-zooms --maximum-zoom=10 --no-tile-stats --force
tile_join_opts = --no-tile-size-limit --force --no-tile-stats

years = 00 10
geo_types = states counties cities tracts
geo_years = $(foreach y,$(years),$(foreach g,$(geo_types),$g-$y))

states_min_zoom = 2
counties_min_zoom = 2
cities_min_zoom = 4
tracts_min_zoom = 6
block-groups_min_zoom = 7

states_bytes = 1000000
counties_bytes = 5000000
cities_bytes = 200000
tracts_bytes = 200000
block-groups_bytes = 300000

census_opts = --detect-shared-borders --coalesce-smallest-as-needed

# build ID to deploy to if not set
BUILD_ID?=2018-12-14

# For comma-delimited list
null :=
space := $(null) $(null)
comma := ,

# Assign layer properties based on minimum zoom
$(foreach g, $(geo_types), $(eval $(g)_census_opts = --minimum-zoom=$($g_min_zoom) --maximum-tile-bytes=$($g_bytes) $(census_opts)))
$(foreach g, $(geo_types), $(eval $(g)_centers_opts = -B$($g_min_zoom) --maximum-tile-bytes=1000000))

# Center data column options
$(foreach g, $(geo_years), $(eval $(g)_center_cols = GEOID,n))
cities-10_center_cols = GEOID,n,p-10

# Edit node commands to use additional memory
mapshaper_cmd = node --max_old_space_size=4096 $$(which mapshaper)
geojson_label_cmd = node --max_old_space_size=4096 $$(which geojson-polygon-labels)

output_tiles = $(foreach t, $(geo_years), tiles/$(t).mbtiles)

all: $(output_tiles)

## deploy                           : Create directories with .pbf file tiles, copy to S3
deploy:
	mkdir -p tilesets
	for f in tiles/*.mbtiles; do tile-join --no-tile-size-limit --force -e ./tilesets/evictions-$$(basename "$${f%.*}") $$f; done
	aws s3 cp ./tilesets s3://$(S3_TILESETS_BUCKET)/$(BUILD_ID) --recursive --acl=public-read --content-encoding=gzip --region=us-east-2 --cache-control max-age=2628000

### MERGE TILES

## tiles/%.mbtiles                  : Convert geography GeoJSON to .mbtiles
tiles/%.mbtiles: census_data/%.mbtiles centers_data/%.mbtiles
	mkdir -p $(dir $@)
	tile-join $(tile_join_opts) -o $@ $^

## centers_data/%.mbtiles           : Join centers tiles to data for eviction rates
.SECONDEXPANSION:
centers_data/%.mbtiles: centers_data/%.csv centers/$$(subst -$$(lastword $$(subst -, ,$$*)),,$$*).mbtiles
	tile-join -l $(subst -$(lastword $(subst -, ,$*)),,$*)-centers --if-matched $(tile_join_opts) -o $@ -c $^ 

## centers_data/%.csv               : Get eviction rate properties and GEOID for centers
centers_data/%.csv: grouped_data/%.csv
	mkdir -p $(dir $@)
	cat $< | \
	python3 utils/subset_cols.py $($*_center_cols),$(subst $(space),$(comma),$(filter e%,$(subst $(comma),$(space),$(shell head -n 1 $<)))) | \
	perl -ne 'if ($$. == 1) { s/"//g; } print;' > $@

## census_data/%.mbtiles            : Create census shape tiles from joining non-eviction data and geography tiles
.SECONDEXPANSION:
census_data/%.mbtiles: grouped_data/%.csv census/$$(subst -$$(lastword $$(subst -, ,$$*)),,$$*).mbtiles
	mkdir -p $(dir $@)
	$(eval exclude_cols=$(foreach c, $(filter e%,$(subst $(comma),$(space),$(shell head -n 1 $<))), -x $c))
	tile-join -l $(subst -$(lastword $(subst -, ,$*)),,$*) --if-matched $(tile_join_opts) $(exclude_cols) -o $@ -c $^

### GEOGRAPHY

## centers/%.mbtiles                : Center .mbtiles with flags for centers based on layer
centers/%.mbtiles: centers/%.geojson
	tippecanoe -L $*-centers:$< $(tippecanoe_opts) $($*_centers_opts) -o $@

## census/%.mbtiles                 : Census .mbtiles with specific flags for census geography
census/%.mbtiles: census/%.geojson
	tippecanoe -L $*:$< $(tippecanoe_opts) $($*_census_opts) -o $@

## centers/%.geojson                : GeoJSON centers
centers/%.geojson: census/%.geojson
	mkdir -p $(dir $@)
	$(geojson_label_cmd) --style largest $< > $@

## census/%.geojson                 : Census GeoJSON from S3 bucket
census/%.geojson:
	$(MAKE) -f fetch_s3_source.mk $@

### GENERAL DATA

# Secondary expansion allows processing of source so that states-10.csv comes from states.csv
## grouped_data/%.csv               : Group data by FIPS code with columns for {ATTR}-{YEAR}
.SECONDEXPANSION:
grouped_data/%.csv: data/$$(subst -$$(lastword $$(subst -, ,$$*)),,$$*).csv
	mkdir -p $(dir $@)
	cat $< | \
	python3 scripts/process_group_data.py $(lastword $(subst -, ,$*)) | \
	perl -ne 'if ($$. == 1) { s/"//g; } print;' > $@

## data/%.csv                       : Eviction and demographic data from S3
data/%.csv:
	$(MAKE) -f fetch_s3_source.mk $@