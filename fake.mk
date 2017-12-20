s3_base = https://s3.amazonaws.com/eviction-lab-data/
geo_types = states counties cities tracts block-groups

.PRECIOUS: data/demographics/%.csv data/evictions/%.csv
.PHONY: all clean deploy

all: $(foreach g, $(geo_types), data/evictions/$(g).csv)

clean:
	rm -rf data fixtures

# Deploy using for loop rather than recursive because of files below
deploy:
	for f in data/evictions/*.csv; do gzip $$f; done
	for f in data/evictions/*.gz; do aws s3 cp $$f s3://eviction-lab-data/evictions/$$(basename $$f) --acl=public-read; done

data/evictions/%.csv: data/demographics/%.csv fixtures/sample/%.csv
	mkdir -p data/evictions
	python3 scripts/create_data_fake.py $^ > $@

data/demographics/%.csv:
	mkdir -p data/demographics
	wget -O $@.gz $(s3_base)demographics/$(notdir $@).gz
	gunzip $@.gz

fixtures/sample/%.csv:
	mkdir -p fixtures/sample
	wget -O $@ $(s3_base)$@
