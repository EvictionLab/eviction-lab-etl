### The following environment variables must be set
# S3_SOURCE_DATA_BUCKET
# S3_TOOL_DATA_BUCKET
# S3_TILESETS_BUCKET
# S3_DATA_DOWNLOADS_BUCKET
# S3_EXPORTS_BUCKET
tippecanoe_opts = --attribute-type=GEOID:string --simplification=10 --simplify-only-low-zooms --maximum-zoom=10 --no-tile-stats --force
tile_join_opts = --no-tile-size-limit --force --no-tile-stats

years = 00 10
geo_types = states counties cities tracts block-groups
geo_years = $(foreach y,$(years),$(foreach g,$(geo_types),$g-$y))

sub_eviction_cols = evictions,eviction-filings,eviction-rate,eviction-filing-rate
eviction_cols = $(sub_eviction_cols),low-flag

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
tool_data = data/rankings/states-rankings.csv data/rankings/cities-rankings.csv data/search/counties.csv data/search/locations.csv data/avg/us.json data/us/national.csv
public_data = data/public/US/all.csv data/public/US/national.csv conf/DATA_DICTIONARY.txt $(foreach g, $(geo_types), census/$(g).geojson grouped_public/$(g).csv data/non-imputed/$(g).csv) 

# For comma-delimited list
null :=
space := $(null) $(null)
comma := ,

# Don't delete files created throughout on completion
.PRECIOUS: tilesets/%.mbtiles tiles/%.mbtiles census/%.geojson census/%.mbtiles centers/%.mbtiles data/search/%.csv
.PHONY: all clean deploy deploy_public_data deploy_data submit_jobs help

## all                              : Create all output data
all: $(output_tiles)

## clean                            : Remove created files
clean:
	rm -rf centers data grouped_data grouped_public census_data centers_data json tiles tilesets
	rm -rf census/*.mbtiles

# Based on https://swcarpentry.github.io/make-novice/08-self-doc/
## help                             : Print help
help: Makefile
	perl -ne '/^## / && s/^## //g && print' $<

## submit_jobs                      : Submit jobs to AWS Batch
submit_jobs:
	python3 utils/submit_jobs.py $(output_tiles) deploy_data

## deploy                           : Create directories with .pbf file tiles, copy to S3
deploy:
	mkdir -p tilesets
	for f in tiles/*.mbtiles; do tile-join --no-tile-size-limit --force -e ./tilesets/evictions-$$(basename "$${f%.*}") $$f; done
	aws s3 cp ./tilesets s3://$(S3_TILESETS_BUCKET) --recursive --acl=public-read --content-encoding=gzip --region=us-east-2 --cache-control max-age=2628000

### DATA DEPLOYMENT

## deploy_data                      : Deploy all data files used in the map and rankings tool, remove old exports
deploy_data: $(tool_data)
	for f in $^; do aws s3 cp $$f s3://$(S3_TOOL_DATA_BUCKET)/$$f --acl=public-read --cache-control max-age=2628000; done
	aws s3 rm s3://$(S3_EXPORTS_BUCKET) --recursive
	aws cloudfront create-invalidation --distribution-id $(CLOUDFRONT_ID_DEV) --paths /*
	aws cloudfront create-invalidation --distribution-id $(CLOUDFRONT_ID_PROD) --paths /*

## deploy_public_data               : Create and deploy public data
deploy_public_data: $(public_data)
	python3 scripts/create_data_public.py
	aws s3 cp ./data/public s3://$(S3_DATA_DOWNLOADS_BUCKET) --recursive --acl=public-read
	aws s3 cp ./data/non-imputed s3://$(S3_DATA_DOWNLOADS_BUCKET)/non-imputed --recursive --acl=public-read
	aws s3 cp ./conf/DATA_DICTIONARY.txt s3://$(S3_DATA_DOWNLOADS_BUCKET)/DATA_DICTIONARY.txt --acl=public-read
	aws cloudfront create-invalidation --distribution-id $(PUBLIC_DATA_CLOUDFRONT_ID) --paths /*

## data/avg/us.json                 : Averages of US data
data/avg/us.json: data/us/national.csv
	mkdir -p $(dir $@)
	cat $< | \
	python3 scripts/convert_varnames.py | \
	python3 scripts/create_us_average.py > $@

## data/us/national.csv             : US data by year for tool
data/us/national.csv: data/public/US/national.csv
	mkdir -p $(dir $@)
	cp $< $@

### SEARCH DATA

## data/search/locations.csv        : Search data for counties and states
data/search/locations.csv: data/search/counties.csv data/search/states.csv
	csvstack $^ > $@

## data/search/%.csv                : Create search data
data/search/%.csv: data/%.csv data/search/%-centers.csv
	python3 scripts/create_search_data.py $^ $@

## data/search/%-centers.csv        : Convert geography centers to CSV
data/search/%-centers.csv: centers/%.geojson
	mkdir -p $(dir $@)
	in2csv --format json -k features $< > $@

### CITY RANKING DATA

## data/rankings/%-rankings.csv     : Create rankings data
data/rankings/%-rankings.csv: data/%.csv data/rankings/%-centers.csv
	python3 scripts/create_data_rankings.py $^ $@

## data/rankings/%-centers.csv      : Convert GeoJSON centers to CSV for rankings
data/rankings/%-centers.csv: centers/%.geojson
	mkdir -p $(dir $@)
	in2csv --format json -k features $< > $@

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
	mkdir -p $(dir $@)
	aws s3 cp s3://$(S3_SOURCE_DATA_BUCKET)/$@.gz - | \
	gunzip -c | \
	$(mapshaper_cmd) -i - field-types=GEOID:str \
		-each "this.properties.west = +this.bounds[0].toFixed(4); \
			this.properties.south = +this.bounds[1].toFixed(4); \
			this.properties.east = +this.bounds[2].toFixed(4); \
			this.properties.north = +this.bounds[3].toFixed(4);" \
		-o $@

### PUBLIC DATA

## grouped_public/%.csv             : Need to combine full data CSVs for GeoJSON merge
grouped_public/%.csv: data/public/US/%.csv
	mkdir -p $(dir $@)
	cat $< | \
	python3 scripts/process_group_data.py | \
	perl -ne 'if ($$. == 1) { s/"//g; } print;' > $@

## data/public/US/all.csv           : Full US public data
data/public/US/all.csv: $(foreach g, $(geo_types), data/public/US/$(g).csv)
	mkdir -p $(dir $@)
	csvstack $^ > $@

## data/public/US/national.csv      : US data by year
data/public/US/national.csv:
	mkdir -p $(dir $@)
	aws s3 cp s3://$(S3_SOURCE_DATA_BUCKET)/evictions/us.csv.gz - | \
	gunzip -c | \
	python3 scripts/convert_varnames.py | \
	csvcut -c year,renter-occupied-households,$(sub_eviction_cols) > $@

## data/public/US/%.csv             : For US data, pull demographics and full eviction data
data/public/US/%.csv: data/demographics/%.csv data/full-evictions/%.csv
	mkdir -p $(dir $@)
	python3 utils/csvjoin.py GEOID,year $^ > $@

### GENERAL DATA

# Secondary expansion allows processing of source so that states-10.csv comes from states.csv
## grouped_data/%.csv               : Group data by FIPS code with columns for {ATTR}-{YEAR}
.SECONDEXPANSION:
grouped_data/%.csv: data/$$(subst -$$(lastword $$(subst -, ,$$*)),,$$*).csv
	mkdir -p $(dir $@)
	cat $< | \
	python3 scripts/process_group_data.py $(lastword $(subst -, ,$*)) | \
	perl -ne 'if ($$. == 1) { s/"//g; } print;' > $@

## data/%.csv                       : Join evictions and demographics
data/%.csv: data/demographics/%.csv data/evictions/%.csv
	python3 utils/csvjoin.py GEOID,year $^ > $@

### S3 SOURCE DATA

## data/non-imputed/%.csv:          : Non-imputed data for downloads
data/non-imputed/%.csv:
	mkdir -p $(dir $@)
	aws s3 cp s3://$(S3_SOURCE_DATA_BUCKET)/non-imputed/$(notdir $@).gz - | \
	gunzip -c | \
	python3 scripts/convert_varnames.py > $@

## data/full-evictions/cities.csv   : Override full-evictions data for cities/places
data/full-evictions/cities.csv:
	mkdir -p $(dir $@)
	aws s3 cp s3://$(S3_SOURCE_DATA_BUCKET)/evictions/cities-unrounded.csv.gz - | \
	gunzip -c | \
	python3 scripts/convert_varnames.py > $@

## data/full-evictions/%.csv        : Pull eviction data, including imputed/subbed
data/full-evictions/%.csv:
	mkdir -p $(dir $@)
	aws s3 cp s3://$(S3_SOURCE_DATA_BUCKET)/evictions/$(notdir $@).gz - | \
	gunzip -c | \
	python3 scripts/convert_varnames.py > $@

## data/evictions/%.csv             : Pull eviction data, get only necessary columns
data/evictions/%.csv:
	mkdir -p $(dir $@)
	aws s3 cp s3://$(S3_SOURCE_DATA_BUCKET)/evictions/$(notdir $@).gz - | \
	gunzip -c | \
	python3 scripts/convert_varnames.py | \
	python3 scripts/convert_crosswalk_geo.py $* | \
	python3 utils/subset_cols.py GEOID,year,$(eviction_cols) > $@

## data/demographics/%.csv          : Pull demographic data
data/demographics/%.csv:
	mkdir -p $(dir $@)
	aws s3 cp s3://$(S3_SOURCE_DATA_BUCKET)/demographics/$(notdir $@).gz - | \
	gunzip -c > $@
