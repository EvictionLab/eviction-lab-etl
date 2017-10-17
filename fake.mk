s3_base = https://s3.amazonaws.com/eviction-lab-data/
geo_types = states counties zip-codes cities tracts block-groups

.PHONY: all clean

all: $(foreach g, $(geo_types), data/$(g).csv)

clean: rm -rf data fixtures

data/%.csv: fixtures/context/%.csv fixtures/sample/%.csv
	mkdir -p data
	python3 scripts/create_fake_data.py $^ > $@

fixtures/context/%.csv:
	mkdir -p fixtures/context
	wget -O $@.gz $(s3_base)$@.gz
	gunzip $@.gz

fixtures/sample/%.csv:
	mkdir -p fixtures/sample
	wget -O $@ $(s3_base)$@
