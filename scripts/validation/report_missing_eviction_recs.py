###
# Generate a CSV containing how many eviction records were missed for each place
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
    dtype = { 'GEOID': 'object', 'year': 'object' })
  evictions_df.set_index(['GEOID', 'year'],inplace=True)

  # load data frame with demographic records
  demographics_df = pd.read_csv(
    os.path.join(DEMOGRAPHICS_DATA_DIR, filename),
    dtype = { 'GEOID': 'object', 'year': 'object' })
  demographics_df.set_index(['GEOID', 'year'],inplace=True)

  # outer join evictions and demographics
  new_df = demographics_df.join(evictions_df, how="outer")
  
  # get rows where demographic data is not present
  null_df = new_df[new_df['name'].isnull()].reset_index(level=['GEOID','year'])
  
  # get data frame where eviction records are present
  ev_not_null = evictions_df[evictions_df[['renter-occupied-households','eviction-filings','evictions','eviction-rate','eviction-filing-rate']].notnull().any(axis=1)]
  
  # indexed records with no demographics
  null_dems_df = null_df.set_index(['GEOID', 'year'])

  # inner join to get records that have eviction data but no demographics
  ev_no_dems = ev_not_null.join(null_dems_df[['name', 'parent-location']], how="inner")
  ev_no_dems.reset_index(level=['GEOID','year'], inplace=True)

  # count # of times eviction records occur with no demographic data
  occ_count = ev_no_dems['GEOID'].value_counts()

  # get geoids of locations w/ null data
  geoids = null_df['GEOID'].drop_duplicates().tolist()
  new_df.reset_index(level=['GEOID','year'], inplace=True)

  # get rows that contain population
  pop_df = new_df.loc[new_df['GEOID'].isin(geoids)][['GEOID', 'name', 'population']]
  ordered_pop_df = pop_df[pop_df['population'].notnull()]

  # sort by population, drop duplicate GEOID rows
  out_df = ordered_pop_df.drop_duplicates(['GEOID']).sort_values(by=['population'],ascending=False)

  # add missed eviction record count, strip out where no evictions were missed
  out_df.set_index('GEOID', inplace=True)
  out_df['missed_eviction_records'] = occ_count
  out_df = out_df[out_df['missed_eviction_records'].notnull() & (out_df['missed_eviction_records'] > 0)]
  
  out_df.to_csv(sys.stdout)
  