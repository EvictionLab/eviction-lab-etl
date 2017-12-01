years = 00 10
geo_types = states counties cities tracts block-groups

STATES = $(shell csvcut -c usps conf/state_fips.csv | tail -n 51)
GEO_TARGETS = $(foreach s, $(STATES), data/public_data/$(s)/%.geojson)
CSV_TARGETS = $(foreach s, $(STATES), data/public_data/$(s)/%.csv)
CSV_ALL_TARGETS = $(foreach s, $(STATES), data/public_data/$(s)/all.csv)

mapshaper_cmd = node --max_old_space_size=4096 $$(which mapshaper)

define get_state_fips
	$(eval state=$(subst data/public_data/,,$(@D)))
	$(eval state_fips=$(shell csvgrep -c usps -m $(state) conf/state_fips.csv | tail -n 1 | cut -d ',' -f1))
endef

# Make GeoJSON from grouped_data with stacked attributes
$(GEO_TARGETS): grouped_data/%.csv census/%.geojson
	$(call get_state_fips,$@)
	mkdir -p $(dir $@)
	$(mapshaper_cmd) -i $(lastword $^) field-types=GEOID:str \
		-filter "this.properties.GEOID.slice(0, 2) === '$(state_fips)'" \
		-join $< field-types=GEOID:str keys=GEOID,GEOID -o $@

# Need to combine grouped_data CSVs for GeoJSON merge
grouped_data/%.csv: $(foreach y, $(years), grouped_data/%-$(y).csv)
	python3 utils/csvjoin.py GEOID,n,pl $^ > $@

# Pull state FIPS code from file, CSV source from matching string
$(CSV_TARGETS): data/%.csv
	$(call get_state_fips,$@)
	mkdir -p $(dir $@)
	csvgrep -c GEOID -r '^$(state_fips)' data/$(notdir $@) > $@

# Only filter for state prefix on all.csv
$(CSV_ALL_TARGETS): data/us.csv
	$(call get_state_fips,$@)
	mkdir -p $(dir $@)
	csvgrep -c GEOID -r '^$(state_fips)' $< > $@

# For US data, just copy without filtering
data/public_data/us/%.csv: data/%.csv
	mkdir -p $(dir $@)
	cp data/$(notdir $@) $@

data/public_data/us/all.csv: data/us.csv
	mkdir -p $(dir $@)
	cp $< $@
