# Checks values of crosswalked demographics to make sure they fall
# within valid ranges.

geo_types = states counties cities tracts block-groups

pct_cols = poverty-rate pct-renter-occupied pct-white pct-af-am pct-hispanic pct-am-ind pct-asian pct-nh-pi pct-multiple pct-other
all_cols = $(pct_cols) rent-burden median-household-income median-property-value

all: $(foreach f,$(all_cols), validation/$(f).csv)

clean:
	rm -rf validation

# Based on https://swcarpentry.github.io/make-novice/08-self-doc/
## help                                        : Print help
help: check_values.mk
	perl -ne '/^## / && s/^## //g && print' $<

tmp/%/block-groups.csv: data/demographics/block-groups.csv
	mkdir -p $(dir $@)
	csvcut -c GEOID,year,$* data/demographics/block-groups.csv | \
	csvsql --query 'select GEOID,year,"$*" from stdin where "$*" > 100;' > $@

tmp/%/tracts.csv: data/demographics/tracts.csv
	mkdir -p $(dir $@)
	csvcut -c GEOID,year,$* data/demographics/tracts.csv | \
	csvsql --query 'select GEOID,year,"$*" from stdin where "$*" > 100;' > $@

tmp/%/counties.csv: data/demographics/counties.csv
	mkdir -p $(dir $@)
	csvcut -c GEOID,year,$* data/demographics/counties.csv | \
	csvsql --query 'select GEOID,year,"$*" from stdin where "$*" > 100;' > $@

tmp/%/cities.csv: data/demographics/cities.csv
	mkdir -p $(dir $@)
	csvcut -c GEOID,year,$* data/demographics/cities.csv | \
	csvsql --query 'select GEOID,year,"$*" from stdin where "$*" > 100;' > $@

tmp/%/states.csv: data/demographics/states.csv
	mkdir -p $(dir $@)
	csvcut -c GEOID,year,$* data/demographics/states.csv | \
	csvsql --query 'select GEOID,year,"$*" from stdin where "$*" > 100;' > $@

tmp/rent-burden/%.csv: data/demographics/%.csv
	mkdir -p $(dir $@)
	csvcut -c GEOID,year,rent-burden $< | \
	csvsql --query 'select GEOID,year,"rent-burden" from stdin where "rent-burden" > 50.1;' > $@

tmp/rent-burden/block-groups.csv: data/demographics/block-groups.csv
	mkdir -p $(dir $@)
	csvcut -c GEOID,year,rent-burden data/demographics/block-groups.csv | \
	csvsql --query 'select GEOID,year,"rent-burden" from stdin where "rent-burden" > 50.1;' > $@

tmp/median-property-value/%.csv: data/demographics/%.csv
	mkdir -p $(dir $@)
	csvcut -c GEOID,year,median-property-value $< | \
	csvsql --query 'select GEOID,year,"median-property-value" from stdin where "median-property-value" > 2000001;' > $@

tmp/median-household-income/%.csv: data/demographics/%.csv
	mkdir -p $(dir $@)
	csvcut -c GEOID,year,median-household-income $< | \
	csvsql --query 'select GEOID,year,"median-household-income" from stdin where "median-household-income" > 250001;' > $@

validation/%.csv: $(foreach f,$(geo_types), tmp/%/$(f).csv)
	mkdir -p $(dir $@)
	csvstack $^ > $@

validation/rent-burden.csv: $(foreach f,$(geo_types), tmp/rent-burden/$(f).csv)
	mkdir -p $(dir $@)
	csvstack $^ > $@

validation/median-property-value.csv: $(foreach f,$(geo_types), tmp/median-property-value/$(f).csv)
	mkdir -p $(dir $@)
	csvstack $^ > $@

validation/median-household-income.csv: $(foreach f,$(geo_types), tmp/median-household-income/$(f).csv)
	mkdir -p $(dir $@)
	csvstack $^ > $@

compare/%.csv:
	mkdir -p $(dir $@)
	aws s3 cp s3://$(S3_SOURCE_DATA_BUCKET)/$(firstword $(subst _, ,$*))/$(lastword $(subst _, ,$*)).csv.gz - | \
	gunzip -c > $@

.SECONDEXPANSION:
compare/%.json: compare/%.csv compare/$(BUILD_ID)_$$(subst $$(firstword $$(subst _, ,$$*))_,,$$*).csv
	mkdir -p $(dir $@)
	csvdiff --style=pretty --output=$@ GEOID,year $^

tmp/badboys/%.csv: validation/%.csv
	mkdir -p $(dir $@)
	echo "value" | csvjoin $< - | \
	sed -r 's/([0-9]*),([0-9]*),([0-9\.]*),/\1,\2,\3,$*/g;' | \
	csvcut -c GEOID,year,value > $@

conf/bad-values-list.csv: $(foreach c,$(all_cols), tmp/badboys/$(c).csv)
	csvstack $^ > $@

## data/demographics/%.csv          : Pull demographic data
data/demographics/%.csv:
	$(MAKE) -f fetch_s3_source.mk $@