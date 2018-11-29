# Fetches raw data from S3 instead of Census API

years = 00 10
geo_types = states counties cities tracts block-groups
geo_years = $(foreach y,$(years),$(foreach g,$(geo_types),$g-$y))
raw_files = $(foreach f,$(geo_years), data/demographics/raw/$(f).csv)

.PRECIOUS: data/demographics/raw/%.csv
.PHONY: all clean

## all                                         : Fetch all demographics data
all: $(raw_files)

## clean                                       : Remove all demographics files
clean:
	rm -rf data/demographics/raw

# Based on https://swcarpentry.github.io/make-novice/08-self-doc/
## help                                        : Print help
help: demographics.mk
	perl -ne '/^## / && s/^## //g && print' $<

## data/demographics/raw/%.csv                 : Fetch raw demographics data fetched from Census API
data/demographics/raw/%.csv:
	mkdir -p $(dir $@)
	aws s3 cp s3://$(S3_SOURCE_DATA_BUCKET)/demographics/$(DATE)/raw/$*.csv.gz - | \
	gunzip > $@
