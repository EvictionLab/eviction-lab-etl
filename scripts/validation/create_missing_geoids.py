###
# Generate breakdown of missing data by column name
###
# Output:
# | state         | eviction_records         | demographic_records        | joined_records              |
# | ------------- | ------------------------ | -------------------------- | --------------------------- |
# | state fips    | # of eviction record     | # of demographic records   | # of records in public data |
###

import os
import sys
import csv
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
EVICTIONS_DATA_DIR = os.path.join(BASE_DIR, 'data', 'full-evictions')
DEMOGRAPHICS_DATA_DIR = os.path.join(BASE_DIR, 'data', 'demographics')

if __name__ == '__main__':

  geography = sys.argv[1]
  filename = geography + '.csv'

  # load data frame with eviction records
  evictions_df = pd.read_csv(
    os.path.join(EVICTIONS_DATA_DIR, filename),
    dtype = { 'GEOID': 'object' })

  # get list of geoids
  evictions_geoids = evictions_df.drop_duplicates('GEOID')['GEOID'].tolist()

  # load data frame with demographic records
  demographics_df = pd.read_csv(
    os.path.join(DEMOGRAPHICS_DATA_DIR, filename),
    dtype = { 'GEOID': 'object' })

  # get unique geoids
  demographics_geoids = demographics_df.drop_duplicates('GEOID')['GEOID'].tolist()

  # get geoids that appear in eviction records but not demographics
  geoids_w_no_dem = list(set(evictions_geoids) - set(demographics_geoids))

  # output as csv
  data = []
  for item in geoids_w_no_dem:
    data.append({ 'type': geography, 'GEOID': item })
  output_df = pd.DataFrame(data)
  output_df.to_csv(sys.stdout, index=False, quoting=csv.QUOTE_NONNUMERIC)
