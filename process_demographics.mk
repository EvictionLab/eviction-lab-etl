# Tasks to processes raw census data and map 2000 data to 2010 geography

years = 00 10
geo_types = states counties cities tracts
geo_years = $(foreach y,$(years),$(foreach g,$(geo_types),$g-$y))
output_files = $(foreach f, $(geo_types), data/demographics/$(f).csv)
ts := $(shell date "+%H%M%S")

.PRECIOUS: data/demographics/%.csv
.PHONY: all clean test_function help

## all                                         : Create all demographics data
all: $(output_files)

# Based on https://swcarpentry.github.io/make-novice/08-self-doc/
# help                                        : Print help
help: process_demographics_server.mk
	perl -ne '/^## / && s/^## //g && print' $<

clean:
	rm -rf data/demographics
	rm -f log/*.txt

## deploy                                      : Compress demographic data and deploy to S3
deploy:
	for f in data/demographics/*.csv; do gzip $$f; done
	for f in data/demographics/*.gz; do aws s3 cp $$f s3://$(S3_SOURCE_DATA_BUCKET)/$(BUILD_ID)/demographics/$$(basename $$f); done

deploy_logs:
	cat log/*.txt > log/crosswalk_log.txt
	aws s3 cp log/crosswalk_log.txt s3://$(S3_SOURCE_DATA_BUCKET)/$(BUILD_ID)/demographics/crosswalk_log_$(ts).txt
	rm -f log/*.txt

## data/demographics/raw/%.csv                 : Fetch raw demographics data fetched from Census API
.SECONDARY:
data/demographics/raw/%.csv:
	$(MAKE) -f fetch_s3_source.mk $@

### DEMOGRAPHIC DATA

## data/demographics/%.csv                     : Create crosswalked demographic data for geographies
data/demographics/%.csv: $(foreach y, $(years), data/demographics/years/%-$(y).csv)
	csvstack $^ | python3 scripts/convert_crosswalk_geo.py $* | \
	python3 scripts/remove_bad_values.py conf/bad-values-list.csv > $@

## data/demographics/years/%.csv               : Create demographic data grouped by geography and year
data/demographics/years/%.csv: data/demographics/raw/%.csv
	mkdir -p $(dir $@)
	cat data/demographics/raw/$*.csv | python3 scripts/convert_census_vars.py > $@

## data/demographics/years/tracts-00.csv       : Create tracts-00 demographics, convert with weights
data/demographics/years/tracts-10.csv: data/demographics/raw/tracts-10.csv 
	mkdir -p $(dir $@)
	cat data/demographics/raw/tracts-10.csv | \
	python3 scripts/rename_tracts_10.py > $@

## data/demographics/years/tracts-00.csv       : Create tracts-00 demographics, convert with weights
data/demographics/years/tracts-00.csv: data/demographics/raw/tracts-00.csv
	mkdir -p $(dir $@)
	cat data/demographics/raw/tracts-00.csv | \
	python3 scripts/convert_00_geo.py tracts conf/tracts-weights.csv conf/count_rate_cols.csv conf/hh_pop_housing.csv | \
	python3 scripts/convert_census_vars.py > $@
