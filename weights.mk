s3_base = https://s3.amazonaws.com/eviction-lab-data/

census/00/%-weights.csv: census/00/geocorr.csv census/00/nhgis_blk2000_blk2010_ge.csv
	python3 scripts/create_00_weights.py $* $^ > $@

# Uses estimates of geography breakdown from Missouri Census Data Center http://mcdc2.missouri.edu/websas/geocorr2k.html
census/00/geocorr.csv:
	wget -O $@.gz $(s3_base)relationships/$(notdir $@).gz
	gunzip $@.gz

# Downloading NHGIS 2000 data crosswalks
census/00/nhgis_blk2000_blk2010_ge.csv: census/00/crosswalks.zip
	unzip -d $(dir $@) $<
	touch $@

.INTERMEDIATE:
census/00/crosswalks.zip:
	mkdir -p $(dir $@)
	wget -O $@ http://assets.nhgis.org/crosswalks/nhgis_blk2000_blk2010_ge.zip