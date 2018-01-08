s3_base = https://s3.amazonaws.com/eviction-lab-data/
tippecanoe_opts = --attribute-type=GEOID:string --simplification=10 --simplify-only-low-zooms --maximum-zoom=10 --no-tile-stats --force
tile_join_opts = --no-tile-size-limit --force --no-tile-stats

years = 00 10
year_ints = 0 1 2 3 4 5 6 7 8 9
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
small_tile_census_opts = --low-detail=10 --grid-low-zooms $(census_opts)

# Assign layer properties based on minimum zoom
$(foreach g, $(geo_types), $(eval $(g)_census_opts = --minimum-zoom=$($g_min_zoom) --maximum-tile-bytes=$($g_bytes) $(small_tile_census_opts)))
$(foreach g, $(geo_types), $(eval $(g)_centers_opts = -B$($g_min_zoom) --maximum-tile-bytes=1000000))
states_census_opts = --minimum-zoom=$(states_min_zoom) $(census_opts)
counties_census_opts = --minimum-zoom=$(counties_min_zoom) $(census_opts) --maximum-tile-bytes=$(counties_bytes)

mapshaper_cmd = node --max_old_space_size=4096 $$(which mapshaper)

output_tiles = $(foreach t, $(geo_years), tiles/$(t).mbtiles)

# For comma-delimited list
null :=
space := $(null) $(null)
comma := ,

# Don't delete files created throughout on completion
.PRECIOUS: tilesets/%.mbtiles tiles/%.mbtiles census/%.geojson census/%.mbtiles centers/%.mbtiles
.PHONY: all clean deploy deploy_data submit_jobs

all: $(output_tiles)

clean:
	rm -rf centers data grouped_data grouped_public census_data centers_data json tiles tilesets

## Submit jobs to AWS Batch
## Not including deploy_data because of time
submit_jobs:
	python3 utils/submit_jobs.py $(output_tiles)

## Create directories with .pbf file tiles for deployment to S3
deploy:
	mkdir -p tilesets
	for f in tiles/*.mbtiles; do tile-join --no-tile-size-limit --force -e ./tilesets/evictions-$$(basename "$${f%.*}") $$f; done
	aws s3 cp ./tilesets s3://eviction-lab-tilesets --recursive --acl=public-read --content-encoding=gzip --region=us-east-2

### DATA DEPLOYMENT

deploy_data: $(foreach g, $(geo_types), census/$(g).geojson data/public_data/us/$(g).csv grouped_public/$(g).csv) data/public_data/us/all.csv data/rankings/city-rankings.csv
	python3 scripts/create_data_public.py
	aws s3 cp ./data/public_data s3://eviction-lab-public-data --recursive --acl=public-read
	aws s3 cp data/rankings/city-rankings.csv s3://eviction-lab-data/rankings/city-rankings.csv --acl=public-read
	aws s3 cp data/search/counties.csv s3://eviction-lab-data/search/counties.csv --acl=public-read

## COUNTY SEARCH DATA

data/search/counties.csv: data/public_data/us/counties.csv data/search/counties-centers.csv
	python3 scripts/create_counties_search.py $^ $@

data/search/counties-centers.csv: centers/counties.geojson
	mkdir -p $(dir $@)
	in2csv --format json -k features $< > $@

### CITY RANKING DATA

data/rankings/city-rankings.csv: data/public_data/us/cities.csv data/rankings/cities-centers.csv
	python3 scripts/create_data_rankings.py $^ $@

data/rankings/cities-centers.csv: centers/cities.geojson
	mkdir -p $(dir $@)
	in2csv --format json -k features $< > $@

### PUBLIC DATA

# Need to combine grouped_data CSVs for GeoJSON merge
grouped_public/%.csv: $(foreach y, $(years), grouped_data/%-$(y).csv)
	mkdir -p $(dir $@)
	python3 utils/csvjoin.py GEOID,n,pl $^ > $@

# For US data, just copy without filtering
data/public_data/us/%.csv: data/%.csv
	mkdir -p $(dir $@)
	cp data/$(notdir $@) $@

data/public_data/us/all.csv: $(foreach g, $(geo_types), data/$(g).csv)
	mkdir -p $(dir $@)
	csvstack $^ > $@

### MERGE TILES

## Convert geography GeoJSON to .mbtiles
tiles/%.mbtiles: census_data/%.mbtiles centers_data/%.mbtiles
	mkdir -p tiles
	tile-join $(tile_join_opts) -o $@ $^

## Join centers tiles to data for eviction rates
.SECONDEXPANSION:
centers_data/%.mbtiles: centers_data/%.csv centers/$$(subst -$$(lastword $$(subst -, ,$$*)),,$$*).mbtiles
	tile-join -l $(subst -$(lastword $(subst -, ,$*)),,$*)-centers --if-matched $(tile_join_opts) -o $@ -c $^ 

## Get eviction rate properties and GEOID for centers
centers_data/%.csv: grouped_data/%.csv
	mkdir -p centers_data
	cat $< | python3 utils/subset_cols.py GEOID,n,$(subst $(space),$(comma),$(filter e%,$(subst $(comma),$(space),$(shell head -n 1 $<)))) | \
		perl -ne 'if ($$. == 1) { s/"//g; } print;' > $@

## Create census shape tiles from joining data and geography tiles
.SECONDEXPANSION:
census_data/%.mbtiles: grouped_data/%.csv census/$$(subst -$$(lastword $$(subst -, ,$$*)),,$$*).mbtiles
	mkdir -p census_data
	tile-join -l $(subst -$(lastword $(subst -, ,$*)),,$*) --if-matched $(tile_join_opts) -o $@ -c $^

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

## Group data by FIPS code with columns for {ATTR}-{YEAR}
## Secondary expansion allows processing of source so that states-10.csv comes from states.csv
.SECONDEXPANSION:
grouped_data/%.csv: data/$$(subst -$$(lastword $$(subst -, ,$$*)),,$$*).csv
	mkdir -p grouped_data
	cat $< | python3 scripts/process_group_data.py $(lastword $(subst -, ,$*)) | \
		perl -ne 'if ($$. == 1) { s/"//g; } print;' > $@

## Join evictions and demographics
data/%.csv: data/demographics/%.csv data/evictions/%.csv
	python3 utils/csvjoin.py GEOID,year $^ | python3 scripts/process_eviction_cols.py > $@

## Pull eviction data, get only necessary columns
data/evictions/%.csv:
	mkdir -p data/evictions
	wget -O $@.gz $(s3_base)evictions/$(notdir $@).gz
	gunzip -c $@.gz | \
		python3 scripts/convert_crosswalk_geo.py $* | \
		python3 utils/subset_cols.py GEOID,year,$(eviction_cols) > $@

## Pull demographic data
data/demographics/%.csv:
	mkdir -p data/demographics
	wget -O $@.gz $(s3_base)demographics/$(notdir $@).gz
	gunzip $@.gz
