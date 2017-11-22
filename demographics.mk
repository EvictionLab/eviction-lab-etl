census_90_ftp_base = ftp://ftp.census.gov/census_1990/
s3_base = https://s3.amazonaws.com/eviction-lab-data/
years = 90 00 10
geo_types = states counties cities tracts block-groups
geo_years = $(foreach y,$(years),$(foreach g,$(geo_types),$g-$y))

census_90_dirs = $(shell cat conf/census_90_dirs.txt)
county_fips = $(shell cat conf/fips_codes.txt)

output_files = $(foreach f, $(geo_types), data/demographics/$(f).csv)

cols_301 = p0010001,p0080001,p0110001,p0110002,p0110003,p0110004,p0110005
cols_327 = h0010001,h0040002,h0040001,h0080002
cols_333 = h061a001

.SECONDARY: $(foreach f, $(county_fips), census/%/block-groups/$(f).csv)
.PRECIOUS: $(foreach $(c), 301 327 333, census/90/%/stf$(c).csv) $(foreach y, $(years), census/$(y)/block-groups.csv)
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

# Dependency only needed for block groups, but otherwise command is the same
data/demographics/years/%.csv: census/90/block-groups.csv census/00/block-groups.csv census/10/block-groups.csv
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

# Census 1990
census/90/block-groups.csv: $(foreach c, 301 327 333, census/90/stf$(c).csv)
	python3 scripts/join_90_block_groups.py $^ > $@

census/90/stf%.csv: $(foreach d, $(census_90_dirs), census/90/$(d)/stf%.csv)
	csvstack $^ > $@

census/90/%/stf301.csv census/90/%/stf327.csv census/90/%/stf333.csv:
	mkdir -p $(dir $@)
	$(eval c=$(subst stf,,$(notdir $(basename $@))))
	wget --no-use-server-timestamps -nc -np -nd -r -P $(dir $@) -A 'stf$(c)*.dbf' $(census_90_ftp_base)CD90_3A_$*/
	for f in $(dir $@)stf$(c)*.dbf; do in2csv -f dbf $$f > $$f.csv; done
	csvstack $(dir $@)stf$(c)*.csv | \
		csvgrep -c sumlev -m 150 | \
		python3 utils/subset_cols.py statefp,cnty,tractbna,blckgr,$(cols_$(c)) > $@

# Not present, manually overriding
census/90/PR/stf327.csv census/90/PR/stf333.csv:
	touch $@
