s3_base = https://s3.amazonaws.com/eviction-lab-data/
years = 90 00 10
geo_types = states counties cities tracts block-groups
geo_years = $(foreach y,$(years),$(foreach g,$(geo_types),$g-$y))

output_files = $(foreach f, $(geo_years), demographics/$(f).csv)

.PHONY: all clean deploy

all: $(output_files)

clean:
	rm -r demographics

deploy:
	for f in demographics/*.csv; do gzip $$f; done 
	aws s3 cp ./demographics s3://eviction-lab-data/demographics --recursive --acl=public-read

demographics/%.csv:
	mkdir -p demographics
	python3 scripts/demographic_data.py $* > $@