s3_base = https://s3.amazonaws.com/eviction-lab-data/
years = 00 10
geo_types = states counties cities tracts block-groups
geo_years = $(foreach y,$(years),$(foreach g,$(geo_types),$g-$y)) msa-10

county_fips = $(shell cat conf/fips_codes.txt)

output_files = $(foreach f, $(geo_types), data/demographics/$(f).csv)

cols_301 = p0010001,p0080001,p0110001,p0110002,p0110003,p0110004,p0110005
cols_327 = h0010001,h0040002,h0040001,h0080002
cols_333 = h061a001

.SECONDARY: $(foreach f, $(county_fips), census/%/block-groups/$(f).csv)
.PHONY: all clean deploy

all: $(output_files)

clean:
	rm -rf data/demographics

# Deploy using for loop rather than recursive because of files below
deploy:
	for f in data/demographics/*.csv; do gzip $$f; done
	for f in data/demographics/*.gz; do aws s3 cp $$f s3://eviction-lab-data/demographics/$$(basename $$f) --acl=public-read; done

data/demographics/%.csv: $(foreach y, $(years), data/demographics/years/%-$(y).csv)
	csvstack $^ > $@

data/demographics/msa.csv: data/demographics/years/msa-10.csv
	cp $< $@

# Dependency only needed for block groups, but otherwise command is the same
data/demographics/years/%.csv: census/00/block-groups.csv census/10/block-groups.csv
	mkdir -p data/demographics/years
	python3 scripts/demographic_data.py $* > $@

census/%/block-groups.csv: $(foreach f, $(county_fips), census/%/block-groups/$(f).csv)
	csvstack $^ > $@

census/10/block-groups/%.csv:
	mkdir -p $(dir $@)
	$(eval y=$(subst census/,,$(subst /block-groups/$(notdir $@),,$@)))
	python3 scripts/get_block_groups.py $* $(y) > $@

census/00/block-groups/%.csv:
	mkdir -p $(dir $@)
	$(eval y=$(subst census/,,$(subst /block-groups/$(notdir $@),,$@)))
	python3 scripts/get_block_groups.py $* $(y) > $@
