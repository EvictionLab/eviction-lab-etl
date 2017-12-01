years = 00 10
geo_types = states counties cities tracts block-groups

GEO_TARGETS = $(foreach g, $(geo_types), data/public_data/%/$(g).geojson)
GEO_SOURCES = $(foreach g, $(geo_types), data/grouped/$(g).csv)

US_TARGETS = $(foreach g, $(geo_types), data/public_data/us/$(g).csv)
CSV_TARGETS = $(foreach g, $(geo_types), data/public_data/%/$(g).csv)
CSV_SOURCES = $(foreach g, $(geo_types), data/$(g).csv)

mapshaper_cmd = node --max_old_space_size=4096 $$(which mapshaper)

define get_state_fips
	$(eval state_fips=$(shell csvgrep -c usps -m $(1) conf/state_fips.csv | tail -n 1 | cut -d ',' -f1))
endef

# Make GeoJSON
$(GEO_TARGETS): $(GEO_SOURCES)
	mkdir -p data/public_data/$*
	$(call get_state_fips,$*)
	$(eval geo=$(notdir $(basename $@)))
	$(mapshaper_cmd) census/$(geo).geojson -join $< \
		keys=GEOID:str,GEOID:str where="this.properties.GEOID.startsWith('$(state_fips)')" -o $@

# Need to combine grouped_data CSVs for GeoJSON merge
grouped_data/%.csv: $(foreach y, $(years), grouped_data/%-$(y).csv)
	python3 utils/csvjoin.py GEOID,n,pl $^ > $@

# Pull state FIPS code from file, CSV source from matching string
$(CSV_TARGETS): $(CSV_SOURCES)
	mkdir -p data/public_data/$*
	$(call get_state_fips,$*)
	csvgrep -c GEOID -r '^$(state_fips)' data/$(notdir $@) > $@

# Only filter for state prefix on all.csv
data/public_data/%/all.csv: data/us.csv
	mkdir -p data/public_data/$*
	$(call get_state_fips,$*)
	csvgrep -c GEOID -r '^$(state_fips)' $< > $@

# For US data, just copy without filtering
$(US_TARGETS): $(CSV_SOURCES)
	mkdir -p data/public_data/us
	cp data/$(notdir $@) $@

data/public_data/us/all.csv: data/us.csv
	mkdir -p data/public_data/us
	cp $< $@
