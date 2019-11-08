# Fetches raw data from the Census API

years = 00 10
geo_types = states counties cities tracts
geo_years = $(foreach y,$(years),$(foreach g,$(geo_types),$g-$y))
county_fips = $(shell cat conf/fips_codes.txt)
raw_files = $(foreach f,$(geo_years), data/demographics/raw/$(f).csv)
ts := $(shell date "+%H%M%S")

# use this build ID if one is not set in the environment variables
BUILD_ID?=2018-11-28

.PRECIOUS: data/demographics/raw/%.csv
.PHONY: all clean help deploy deploy_logs

## all                                         : Create all demographics data
all: $(raw_files)

## clean                                       : Remove created demographics files
clean:
	rm -rf data/demographics/raw
	rm -f log/*.txt

# Based on https://swcarpentry.github.io/make-novice/08-self-doc/
## help                                        : Print help
help: fetch_raw_census_api.mk
	perl -ne '/^## / && s/^## //g && print' $<

## deploy                                       : Deploy raw census files to S3
deploy:
	for f in data/demographics/raw/*.csv; do gzip $$f; done
	for f in data/demographics/raw/*.gz; do aws s3 cp $$f s3://$(S3_SOURCE_DATA_BUCKET)/$(BUILD_ID)/demographics/raw/$$(basename $$f); done

## deploy_logs                                  : Deploy fetch logs to S3
deploy_logs:
	cat log/*.txt > log/fetch_log.txt
	aws s3 cp log/fetch_log.txt s3://$(S3_SOURCE_DATA_BUCKET)/$(BUILD_ID)/demographics/raw/fetch_log_$(ts).txt
	rm -f log/*.txt

### DEMOGRAPHIC DATA

## data/demographics/raw/%.csv                 : Create raw demographics data fetched from Census API
data/demographics/raw/%.csv:
	mkdir -p $(dir $@)
	python3 scripts/fetch_raw_census_data.py $* | \
	python3 scripts/fix_duplicates.py > $@
