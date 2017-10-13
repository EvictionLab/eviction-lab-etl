s3_base = https://s3.amazonaws.com/eviction-lab-data/
tippecanoe_opts = --detect-shared-borders --no-feature-limit --no-tile-size-limit --no-tiny-polygon-reduction --simplification=10 -B 2 --minimum-zoom=2 --maximum-zoom=10 --force
geo_types = states counties zip-codes cities tracts block-groups

# For comma-delimited list
null :=
space := $(null) $(null)
comma := ,

# Don't delete files created throughout on completion
.PRECIOUS: tilesets/%.mbtiles json/united-states-search.json tiles/%.mbtiles census/%.geojson
# Delete files that are intermediate dependencies, not final products
.INTERMEDIATE: data/%.xlsx data/%.csv centers/%.geojson grouped_data/%.csv
.PHONY: all clean deploy

all: json/united-states-search.json $(foreach t, $(geo_types), tiles/$(t).mbtiles)

clean:
	rm -rf centers data grouped_data census_data centers_data json tiles tilesets

## Submit job to AWS Batch
submit_job:
	aws batch submit-job --job-name etl-job --job-definition eviction-lab-etl-job --job-queue eviction-lab-etl-job-queue

## Create directories with .pbf file tiles for deployment to S3
deploy: json/united-states-search.json $(foreach t, $(geo_types), tiles/$(t).mbtiles)
	mkdir -p tilesets
	for f in $(geo_types); do tile-join --no-tile-size-limit --force -e ./tilesets/evictions-$$f ./tiles/$$f.mbtiles; done
	aws s3 cp ./tilesets s3://eviction-lab-tilesets --recursive --acl=public-read --content-encoding=gzip --region=us-east-2
	aws s3 cp $< s3://eviction-lab-tilesets/$(notdir $<) --acl=public-read --region=us-east-2

## Convert geography GeoJSON to .mbtiles
tiles/%.mbtiles: census_data/%.geojson centers_data/%.geojson
	mkdir -p tiles
	tippecanoe -L $*:$< -L $*-centers:$(word 2,$^) $(tippecanoe_opts) -o $@

## Join center geography to grouped data, dropping attributes that don't start with eviction-rate-
centers_data/%.geojson: grouped_data/%.csv centers/%.geojson
	mkdir -p centers_data
	mapshaper -i $(word 2,$^) field-types=GEOID:str -join $< field-types=GEOID:str keys=GEOID,GEOID \
		-filter "this.properties.name != undefined" \
		-filter-fields $(subst $(space),$(comma),$(filter eviction-rate-%,$(subst $(comma),$(space),$(shell head -n 1 $<)))) \
		-o $@

## Join census geography to grouped data, add bbox property
census_data/%.geojson: grouped_data/%.csv census/%.geojson
	mkdir -p census_data
	mapshaper -i $(word 2,$^) field-types=GEOID:str \
		-join $< field-types=GEOID:str keys=GEOID,GEOID \
		-filter "this.properties.name != undefined" \
		-each "this.properties.west = this.bounds[0]; this.properties.south = this.bounds[1]; this.properties.east = this.bounds[2]; this.properties.north = this.bounds[3];" \
		-o $@

## JSON for autocomplete, pulls latest population data
json/united-states-search.json: grouped_data/united-states.csv grouped_data/united-states-centers.csv
	$(eval pop_col=$(lastword $(sort $(filter population-%,$(subst $(comma),$(space),$(shell head -n 1 $<))))))
	csvjoin -I -c GEOID $^ | \
		csvcut -c GEOID,name,parent-location,$(pop_col),layer,longitude,latitude | \
		csvgrep -c layer -r "(states|counties|zip-codes|cities)" | \
		csvtojson --colParser='{"GEOID":"string", "$(pop_col)": "number", "longitude": "number", "latitude": "number"}' > $@

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
	head -n 1 $< > $@
	for f in $^; do perl -ne 'print if $$. != 1' $$f >> $@; done

## Group data by FIPS code with columns for {ATTR}-{YEAR}
grouped_data/%.csv: data/%.csv
	mkdir -p grouped_data
	cat $< | python scripts/group_census_data.py > $@

## Fetch Google Sheets data, combine into CSV files
data/%.csv: data/%.xlsx
	in2csv $< > $@

## Get source data from S3 bucket Excel files
data/%.xlsx:
	mkdir -p data
	wget -P data $(s3_base)$@

## GeoJSON centers
centers/%.geojson: census/%.geojson
	mkdir -p centers
	geojson-polygon-labels --by-feature $< > $@

## Census GeoJSON from S3 bucket
census/%.geojson:
	mkdir -p census
	wget -P census $(s3_base)$@.gz
	gunzip $@.gz