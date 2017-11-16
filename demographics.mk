census_90_ftp_base = ftp://ftp.census.gov/census_1990/
s3_base = https://s3.amazonaws.com/eviction-lab-data/
years = 90 00 10
geo_types = states counties cities tracts block-groups
geo_years = $(foreach y,$(years),$(foreach g,$(geo_types),$g-$y))

output_files = $(foreach f, $(geo_types), data/demographics/$(f).csv)

cols_301 = p0010001,p0080001,p0110001,p0110002,p0110003,p0110004,p0110005
cols_327 = h0010001,h0040002,h0040001,h0080002
cols_333 = h061a001

.SECONDARY: census/90/stf%.csv
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
data/demographics/years/%.csv: census/90/block-groups-90.csv
	mkdir -p data/demographics/years
	python3 scripts/demographic_data.py $* > $@

census/90/block-groups-90.csv: $(foreach c, 301 327 333, census/90/stf$(c).csv)
	python3 scripts/join_90_block_groups.py $^ > $@

census/90/stf%.csv:
	mkdir -p census/90
	wget -np -nH -r -P $(dir $@) -A 'stf$**.dbf' $(census_90_ftp_base)
	for f in census/90/census_1990/CD90_3A_*/stf$**.dbf*; do in2csv -f dbf $$f > $$f.csv; done
	csvstack census/90/census_1990/CD90_3A_*/stf$**.csv | \
		csvgrep -c sumlev -m 150 | \
		csvcut -c statefp,cnty,tractbna,blckgr,$(cols_$*) > $@
