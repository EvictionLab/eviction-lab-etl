include Makefile

STATES = $(shell csvcut -c usps conf/state_fips.csv | tail -n 51)

CSV_TARGETS = $(foreach s, $(STATES), data/public_data/$(s)/%.csv)
CSV_ALL_TARGETS = $(foreach s, $(STATES), data/public_data/$(s)/all.csv)
GEO_TARGETS = $(foreach s, $(STATES), data/public_data/$(s)/%.geojson)

OUTPUT_CSV_STATES = $(foreach s, $(STATES), $(foreach g, $(geo_types), data/public_data/$(s)/$(g).csv))
OUTPUT_CSV_ALL_STATES = $(foreach s, $(STATES), data/public_data/$(s)/all.csv)
OUTPUT_GEO_STATES = $(foreach s, $(STATES), $(foreach g, $(geo_types), data/public_data/$(s)/$(g).geojson))

OUTPUT_CSV_US = $(foreach g, $(geo_types), data/public_data/us/$(g).csv) data/public_data/us/all.csv
OUTPUT_GEO_US = $(foreach g, $(geo_types), data/public_data/us/$(g).geojson)

GENERATED_FILES = $(OUTPUT_CSV_US) $(OUTPUT_CSV_STATES) $(OUTPUT_CSV_ALL_STATES) $(OUTPUT_GEO_US) $(OUTPUT_GEO_STATES)

mapshaper_cmd = node --max_old_space_size=8192 $$(which mapshaper)

define get_state_fips
	$(eval state=$(subst data/public_data/,,$(1)))
	$(eval state_fips=$(shell csvgrep -c usps -m $(state) conf/state_fips.csv | tail -n 1 | cut -d ',' -f1))
endef

.PHONY: deploy_data
.PRECIOUS: $(GENERATED_FILES)

deploy_data: $(GENERATED_FILES)
	aws s3 cp ./data/public_data s3://eviction-lab-public-data --recursive --acl=public-read

# Make GeoJSON from grouped public data with stacked attributes
$(GEO_TARGETS): grouped_public/%.csv census/%.geojson
	$(call get_state_fips,$(@D))
	mkdir -p $(dir $@)
	$(mapshaper_cmd) -i $(lastword $^) field-types=GEOID:str,n:str,pl:str \
		-filter "this.properties.GEOID.slice(0, 2) === '$(state_fips)'" \
		-join $< field-types=GEOID:str,n:str,pl:str keys=GEOID,GEOID -o $@

# Need to combine grouped_data CSVs for GeoJSON merge
grouped_public/%.csv: $(foreach y, $(years), grouped_data/%-$(y).csv)
	mkdir -p $(dir $@)
	python3 utils/csvjoin.py GEOID,n,pl $^ > $@

# Pull state FIPS code from file, CSV source from matching string
$(CSV_TARGETS): data/%.csv
	$(call get_state_fips,$(@D))
	mkdir -p $(dir $@)
	csvgrep -c GEOID -r '^$(state_fips)' data/$(notdir $@) > $@

# Only filter for state prefix on all.csv
$(CSV_ALL_TARGETS): data/public_data/us/all.csv
	$(call get_state_fips,$(@D))
	mkdir -p $(dir $@)
	csvgrep -c GEOID -r '^$(state_fips)' $< > $@

# All US geography data without filtering
data/public_data/us/%.geojson: grouped_public/%.csv census/%.geojson
	mkdir -p $(dir $@)
	$(mapshaper_cmd) -i $(lastword $^) field-types=GEOID:str,n:str,pl:str \
		-join $< field-types=GEOID:str,n:str,pl:str keys=GEOID,GEOID -o $@

# For US data, just copy without filtering
data/public_data/us/%.csv: data/%.csv
	mkdir -p $(dir $@)
	cp data/$(notdir $@) $@

data/public_data/us/all.csv: $(foreach g, $(geo_types), data/$(g).csv)
	mkdir -p $(dir $@)
	csvstack $^ > $@
