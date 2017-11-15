s3_base = https://s3.amazonaws.com/eviction-lab-data/
years = 90 00 10
geo_types = states counties cities tracts block-groups
geo_years = $(foreach y,$(years),$(foreach g,$(geo_types),$g-$y))

state_fips = 01 02 04 05 06 08 09 10 11 12 13 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 44 45 46 47 48 49 50 51 53 54 55 56

output_files = $(foreach f, $(geo_years), demographics/$(f).csv)

.PHONY: all clean deploy

all: $(output_files)

clean:
	rm -r demographics

deploy:
	for f in demographics/*.csv; do gzip $$f; done 
	aws s3 cp ./demographics s3://eviction-lab-data/demographics --recursive --acl=public-read

# Dependency only needed for block groups, but otherwise command is the same
# TODO: Load 1990 census all from files?
demographics/%.csv: census_90/block-groups-90.csv
	mkdir -p demographics
	python3 scripts/demographic_data.py $* > $@

census/90/block-groups-90.csv: $(foreach f, $(state_fips), census/90/src/$(f).csv)
	csvstack $^ > $@

census/90/src/%.csv: census/90/src/%.zip
	unzip -o -d $(dir $<) $<
	in2csv $(dir $<)STF3A_$*.dbf | csvgrep -c sumlev -m 150 > $@

census/90/src/%.zip:
	mkdir -p census/90/src
	wget -O $@ https://www2.cdc.gov/nceh/lead/census90/house11/files/stf3a_$*.zip