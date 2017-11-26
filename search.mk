include Makefile

geo_types = states counties cities tracts block-groups
.PHONY: search clean_search

search: json/united-states-search.json
clean_search: rm -rf json search grouped_data/united-states*.csv

## General search file, and search index files from first or first two characters of name
json/united-states-search.json: grouped_data/united-states.csv grouped_data/united-states-centers.csv
	mkdir -p search
	python3 scripts/create_search_index.py $^ $@ search

## Convert the united-states-centers.geojson to CSV for merge later
grouped_data/united-states-centers.csv: json/united-states-centers.geojson
	in2csv --format geojson $< | csvcut -c GEOID,layer,longitude,latitude > $@

## Create combined GeoJSON file with all center points, layer added as property
json/united-states-centers.geojson: $(foreach g, $(geo_types), centers/$(g).geojson)
	mkdir -p json
	for g in $(geo_types); do mapshaper -i centers/$$g.geojson -each "this.properties.layer = \"$$g\"" -o centers/$$g.geojson format=geojson force; done
	mapshaper -i $^ combine-files -merge-layers -o $@ format=geojson

## Combined CSV data
grouped_data/united-states.csv: $(foreach g, $(geo_types), grouped_data/$(g).csv)
	mkdir -p grouped_data
	head -n 1 $< | perl -ne 'print "layer," . $$_' > $@
	for g in $(geo_types); do perl -ne 'print "$$g," . $$_ if $$. != 1' grouped_data/$$g.csv >> $@; done