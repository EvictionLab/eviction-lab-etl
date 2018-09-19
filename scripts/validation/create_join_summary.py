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
PUBLIC_DATA_DIR = os.path.join(BASE_DIR, 'data', 'public', 'US')
EVICTIONS_DATA_DIR = os.path.join(BASE_DIR, 'data', 'full-evictions')
DEMOGRAPHICS_DATA_DIR = os.path.join(BASE_DIR, 'data', 'demographics')

if __name__ == '__main__':

  geography = sys.argv[1]
  filename = geography + '.csv'

  # load data frame with eviction records
  evictions_df = pd.read_csv(
    os.path.join(EVICTIONS_DATA_DIR, filename),
    dtype = { 'GEOID': 'object' })

  # load data frame with demographic records
  demographics_df = pd.read_csv(
    os.path.join(DEMOGRAPHICS_DATA_DIR, filename),
    dtype = { 'GEOID': 'object' })

  # load data frame with joined records
  joined_df = pd.read_csv(
    os.path.join(PUBLIC_DATA_DIR, filename),
    dtype = { 'GEOID': 'object' })
  
  # get counts of records by state
  evict_count = evictions_df['GEOID'].apply(lambda x: x[:2]).value_counts()
  dem_count = demographics_df['GEOID'].apply(lambda x: x[:2]).value_counts()
  joined_count = joined_df['GEOID'].apply(lambda x: x[:2]).value_counts()

  output_df = pd.DataFrame({
    'eviction_records': evict_count,
    'demographic_records': dem_count,
    'joined_records': joined_count
  })

  # output as csv
  output_df.to_csv(sys.stdout, index=True, index_label='state', quoting=csv.QUOTE_NONNUMERIC)
