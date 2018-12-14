# Submits jobs to AWS batch

years = 00 10
geo_types = states counties cities tracts block-groups
geo_years = $(foreach y,$(years),$(foreach g,$(geo_types),$g-$y))
geojson_files = $(foreach f,$(geo_types), census/$(f).geojson)
eviction_lab_tiles = $(foreach t, $(geo_years), tiles/$(t).mbtiles)
raw_demographics = $(foreach f,$(geo_years), data/demographics/raw/$(f).csv)
crosswalked_demographics = $(foreach f,$(geo_types), data/demographics/$(f).csv)
eviction_lab_data = $(foreach f,$(geo_types), data/$(f).csv)

.PHONY: help clean census_geographies census_demographics crosswalked_demographics eviction_lab_data deploy_app_data deploy_public_data tiles

clean:
	rm -rf census census_data centers centers_data grouped_data tiles tilesets data
	rm -f log/*.txt

# Based on https://swcarpentry.github.io/make-novice/08-self-doc/
## help                                        : Print help
help: Makefile
	perl -ne '/^## / && s/^## //g && print' $<

## census_geographies         : Submit job to create 2010 census GeoJSON
census_geographies:
	python3 utils/submit_jobs.py $(geojson_files)

## census_demographics        : Submit raw census demographics jobs to AWS Batch
census_demographics:
	python3 utils/submit_jobs.py $(raw_demographics)

## crosswalk_demographics     : Submit crosswalk demographics jobs to AWS Batch
crosswalked_demographics:
	python3 utils/submit_jobs.py $(crosswalked_demographics)

## eviction_lab_data          : Submit raw census demographics jobs to AWS Batch
eviction_lab_data:
	python3 utils/submit_jobs.py $(eviction_lab_data)

## deploy_app_data            : Submit jobs to deploy data for the map and rankings
deploy_app_data:
	python3 utils/submit_jobs.py deploy_app_data

## deploy_public_data         : Submit jobs to create and deploy public data
deploy_public_data:
	python3 utils/submit_jobs.py deploy_public_data

## tiles                      : Submit tile jobs to AWS Batch
tiles:
	python3 utils/submit_jobs.py $(eviction_lab_tiles)
