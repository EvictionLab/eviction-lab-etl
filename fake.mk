s3_base = https://s3.amazonaws.com/eviction-lab-data/
geo_types = states counties zip-codes cities tracts block-groups

.PHONY: all clean

all: $(foreach g, $(geo_types), data/$(g).csv)

clean:
	rm -rf data fixtures

data/evictions/%.csv: data/demographics/%.csv fixtures/sample/%.csv
	mkdir -p data/evictions
	python3 scripts/create_fake_data.py $^ > $@

data/demographics/%.csv:
	mkdir -p data/demographics
	wget -O $@ $(s3_base)demographics/$(notdir $@).gz
	gunzip $@.gz

fixtures/sample/%.csv:
	mkdir -p fixtures/sample
	wget -O $@ $(s3_base)$@
