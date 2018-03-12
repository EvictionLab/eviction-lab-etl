s3_bucket = eviction-lab-data
s3_tool_data_bucket = eviction-lab-tool-data
s3_base = https://s3.amazonaws.com/$(s3_bucket)/
tippecanoe_opts = --attribute-type=GEOID:string --simplification=10 --simplify-only-low-zooms --maximum-zoom=10 --no-tile-stats --force
tile_join_opts = --no-tile-size-limit --force --no-tile-stats

years = 00 10
geo_types = states counties cities tracts block-groups
geo_years = $(foreach y,$(years),$(foreach g,$(geo_types),$g-$y))

eviction_cols = evictions,eviction-filings

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

# Edit mapshaper command to use additional memory
mapshaper_cmd = node --max_old_space_size=4096 $$(which mapshaper)

output_tiles = $(foreach t, $(geo_years), tiles/$(t).mbtiles)
tool_data = data/rankings/states-rankings.csv data/rankings/cities-rankings.csv data/search/counties.csv data/avg/us.json

# For comma-delimited list
null :=
space := $(null) $(null)
comma := ,

# Don't delete files created throughout on completion
.PRECIOUS: tilesets/%.mbtiles tiles/%.mbtiles census/%.geojson census/%.mbtiles centers/%.mbtiles
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
	aws s3 cp ./tilesets s3://eviction-lab-tilesets --recursive --acl=public-read --content-encoding=gzip --region=us-east-2 --cache-control max-age=2628000

### DATA DEPLOYMENT

## deploy_data                      : Deploy all data files used in the map and rankings tool
deploy_data: $(tool_data)
	for f in $^; do aws s3 cp $$f s3://$(s3_tool_data_bucket)/$$f --acl=public-read --cache-control max-age=2628000; done
	aws cloudfront create-invalidation --distribution-id $(CLOUDFRONT_ID_DEV) --paths /*
	aws cloudfront create-invalidation --distribution-id $(CLOUDFRONT_ID_PROD) --paths /*

## deploy_public_data               : Create and deploy public data
deploy_public_data: data/public/US/all.csv $(foreach g, $(geo_types), census/$(g).geojson grouped_public/$(g).csv)
	python3 scripts/create_data_public.py
	aws s3 cp ./data/public s3://eviction-lab-public-data --recursive --acl=public-read
	aws cloudfront create-invalidation --distribution-id $(PUBLIC_DATA_CLOUDFRONT_ID) --paths /*

## data/avg/us.json                 : Averages of US data
data/avg/us.json: grouped_public/states.csv
	mkdir -p $(dir $@)
	python3 scripts/create_us_average.py $< > $@

### COUNTY SEARCH DATA

## data/search/counties.csv         : Create county search data
data/search/counties.csv: data/public/US/counties.csv data/search/counties-centers.csv
	python3 scripts/create_counties_search.py $^ $@

## data/search/counties-centers.csv : Convert counties centers to CSV
data/search/counties-centers.csv: centers/counties.geojson
	mkdir -p $(dir $@)
	in2csv --format json -k features $< > $@

### CITY RANKING DATA

## data/rankings/%-rankings.csv     : Create rankings data
data/rankings/%-rankings.csv: data/public/US/%.csv data/rankings/%-centers.csv
	python3 scripts/create_data_rankings.py $^ $@

## data/rankings/%-centers.csv      : Convert GeoJSON centers to CSV for rankings
data/rankings/%-centers.csv: centers/%.geojson
	mkdir -p $(dir $@)
	in2csv --format json -k features $< > $@

### PUBLIC DATA

## grouped_public/%.csv             : Need to combine grouped_data CSVs for GeoJSON merge
grouped_public/%.csv: $(foreach y, $(years), grouped_data/%-$(y).csv)
	mkdir -p $(dir $@)
	python3 utils/csvjoin.py GEOID,n,pl $^ > $@

## data/public/US/%.csv             : For US data, just copy without filtering
data/public/US/%.csv: data/%.csv
	mkdir -p $(dir $@)
	cp data/$(notdir $@) $@

## data/public/US/all.csv           : Full US public data
data/public/US/all.csv: $(foreach g, $(geo_types), data/$(g).csv)
	mkdir -p $(dir $@)
	csvstack $^ > $@

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
	geojson-polygon-labels --style largest $< > $@

## census/%.geojson                 : Census GeoJSON from S3 bucket
census/%.geojson:
	mkdir -p $(dir $@)
	wget --no-use-server-timestamps -P census $(s3_base)$@.gz
	gunzip $@.gz
	$(mapshaper_cmd) -i $@ field-types=GEOID:str \
		-each "this.properties.west = +this.bounds[0].toFixed(4); \
			this.properties.south = +this.bounds[1].toFixed(4); \
			this.properties.east = +this.bounds[2].toFixed(4); \
			this.properties.north = +this.bounds[3].toFixed(4);" \
		-o $@ force

### DATA

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
	python3 utils/csvjoin.py GEOID,year $^ | \
	python3 scripts/process_eviction_cols.py > $@

## data/evictions/%.csv             : Pull eviction data, get only necessary columns
data/evictions/%.csv:
	mkdir -p $(dir $@)
	wget --no-use-server-timestamps -O $@.gz $(s3_base)evictions/$(notdir $@).gz
	gunzip -c $@.gz | \
	python3 scripts/convert_crosswalk_geo.py $* | \
	python3 utils/subset_cols.py GEOID,year,$(eviction_cols) > $@

## data/demographics/%.csv          : Pull demographic data
data/demographics/%.csv:
	mkdir -p $(dir $@)
	wget --no-use-server-timestamps -O $@.gz $(s3_base)demographics/$(notdir $@).gz
	gunzip $@.gz
