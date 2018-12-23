# Merges eviction data with demographics data, creates data for search,
# creates data used in map data panel, creates ranking data, creates 
# public data for export.

# Edit node commands to use additional memory
mapshaper_cmd = node --max_old_space_size=4096 $$(which mapshaper)
geojson_label_cmd = node --max_old_space_size=4096 $$(which geojson-polygon-labels)

geo_types = states counties cities tracts block-groups
census_geo_types = $(foreach g,$(geo_types),census/$(g).geojson)
sub_eviction_cols = evictions,eviction-filings,eviction-rate,eviction-filing-rate
eviction_cols = $(sub_eviction_cols),low-flag
ts := $(shell date "+%H%M%S")

# build ID to use for source data
BUILD_ID?=2018-11-28

output_files = $(foreach g,$(geo_types),data/$(g).csv)
public_data = data/public/US/all.csv data/public/US/national.csv conf/DATA_DICTIONARY.txt $(foreach g, $(geo_types), grouped_public/$(g).csv data/non-imputed/$(g).csv) 
tool_data = data/rankings/states-rankings.csv data/rankings/cities-rankings.csv data/search/counties.csv data/search/locations.csv data/avg/us.json data/us/national.csv

# Don't delete files created throughout on completion
.PRECIOUS: data/demographics/%.csv
.PHONY: all clean deploy deploy_public_data deploy_app_data deploy_logs help

## all                              : Create all output data
all: $(output_files) $(tool_data) $(public_data)

## clean                            : Remove created files
clean:
	rm -f data/*.csv
	rm -f data/*.gz
	rm -f $(tool_data)
	rm -f log/*.txt

# Based on https://swcarpentry.github.io/make-novice/08-self-doc/
## help                             : Print help
help: create_eviction_data.mk
	perl -ne '/^## / && s/^## //g && print' $<

# DEPLOY TASKS

## deploy                           : Deploy gzipped eviction / demographics data to S3
deploy:
	for f in data/*.csv; do gzip $$f; done
	for f in data/*.gz; do aws s3 cp $$f s3://$(S3_SOURCE_DATA_BUCKET)/$(BUILD_ID)/$$(basename $$f); done

## deploy_app_data                 : Deploy all data files used in the map and rankings tool, remove old exports
deploy_app_data: $(tool_data)
	for f in $^; do aws s3 cp $$f s3://$(S3_TOOL_DATA_BUCKET)/$$f --acl=public-read --cache-control max-age=2628000; done
	aws s3 rm s3://$(S3_EXPORTS_BUCKET) --recursive
	aws cloudfront create-invalidation --distribution-id $(CLOUDFRONT_ID_DEV) --paths "/*"
	aws cloudfront create-invalidation --distribution-id $(CLOUDFRONT_ID_PROD) --paths "/*"

## deploy_public_data               : Create and deploy public data exports
deploy_public_data: $(census_geo_types) $(public_data)
	python3 scripts/create_data_public.py
	aws s3 cp ./data/public s3://$(S3_DATA_DOWNLOADS_BUCKET) --recursive --acl=public-read
	aws s3 cp ./data/non-imputed s3://$(S3_DATA_DOWNLOADS_BUCKET)/non-imputed --recursive --acl=public-read
	aws s3 cp ./conf/DATA_DICTIONARY.txt s3://$(S3_DATA_DOWNLOADS_BUCKET)/DATA_DICTIONARY.txt --acl=public-read
	aws s3 cp ./conf/CHANGELOG.txt s3://$(S3_DATA_DOWNLOADS_BUCKET)/CHANGELOG.txt --acl=public-read
	aws s3 cp ./conf/changes s3://$(S3_DATA_DOWNLOADS_BUCKET)/changes --recursive --acl=public-read
	aws cloudfront create-invalidation --distribution-id $(PUBLIC_DATA_CLOUDFRONT_ID) --paths "/*"

## deploy_logs                      : Deploy a log of the demographics <- eviction merge
deploy_logs:
	cat log/*.txt > log/demographics_eviction_join_log.txt
	aws s3 cp log/demographics_eviction_join_log.txt s3://$(S3_SOURCE_DATA_BUCKET)/$(BUILD_ID)/demographics_eviction_join_log_$(ts).txt
	rm -f log/*.txt

### GENERAL DATA

## data/%.csv                       : Join evictions and demographics
data/%.csv: data/demographics/%.csv data/evictions/%.csv
	python3 scripts/csvjoin.py GEOID,year $^ > $@

### MAP DATA PANEL DATA

## data/avg/us.json                 : Averages of US data
data/avg/us.json: data/us/national.csv
	mkdir -p $(dir $@)
	cat $< | \
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

### PUBLIC EXPORT DATA

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
	aws s3 cp s3://$(S3_SOURCE_DATA_BUCKET)/$(BUILD_ID)/evictions/us.csv.gz - | \
	gunzip -c | \
	python3 scripts/convert_varnames.py | \
	csvcut -c year,renter-occupied-households,$(sub_eviction_cols) > $@

## data/public/US/%.csv             : For US data, pull demographics and full eviction data
data/public/US/%.csv: data/demographics/%.csv data/full-evictions/%.csv
	mkdir -p $(dir $@)
	python3 scripts/csvjoin.py GEOID,year $^ | \
	python3 scripts/convert_col_order.py > $@

### DATA FETCHED FROM S3 SOURCE

## data/full-evictions/cities.csv   : Override full-evictions data for cities/places
data/full-evictions/cities.csv:
	mkdir -p $(dir $@)
	aws s3 cp s3://$(S3_SOURCE_DATA_BUCKET)/$(BUILD_ID)/evictions/cities-unrounded.csv.gz - | \
	gunzip -c | \
	python3 scripts/convert_varnames.py > $@

## data/full-evictions/%.csv        : Pull eviction data, including imputed/subbed
data/full-evictions/%.csv:
	mkdir -p $(dir $@)
	aws s3 cp s3://$(S3_SOURCE_DATA_BUCKET)/$(BUILD_ID)/evictions/$(notdir $@).gz - | \
	gunzip -c | \
	python3 scripts/convert_varnames.py > $@

## data/evictions/%.csv             : Pull eviction data, get only necessary columns
data/evictions/%.csv:
	mkdir -p $(dir $@)
	aws s3 cp s3://$(S3_SOURCE_DATA_BUCKET)/$(BUILD_ID)/evictions/$(notdir $@).gz - | \
	gunzip -c | \
	python3 scripts/convert_varnames.py | \
	python3 scripts/convert_crosswalk_geo.py $* | \
	python3 utils/subset_cols.py GEOID,year,$(eviction_cols) > $@

## data/demographics/%.csv          : Pull demographic data
data/demographics/%.csv:
	$(MAKE) -f fetch_s3_source.mk $@

## data/non-imputed/%.csv:          : Non-imputed data for downloads
data/non-imputed/%.csv:
	mkdir -p $(dir $@)
	aws s3 cp s3://$(S3_SOURCE_DATA_BUCKET)/$(BUILD_ID)/non-imputed/$(notdir $@).gz - | \
	gunzip -c | \
	python3 scripts/convert_varnames.py > $@

## centers/%.geojson                : GeoJSON centers
centers/%.geojson: census/%.geojson
	mkdir -p $(dir $@)
	$(geojson_label_cmd) --style largest $< > $@

## census/%.geojson                 : Census GeoJSON from S3 bucket
census/%.geojson:
	$(MAKE) -f fetch_s3_source.mk $@