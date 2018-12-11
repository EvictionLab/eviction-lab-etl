# In cases where the geography has changed, like Broomfield, CO 
# there may be duplicate demographic records for a GEOID and year.
# This script finds the duplicates, calculates weights, and combines
# the duplicate entries into a single entry.

import os
import sys
import csv
import pandas as pd
import sys
from data_constants import (COUNT_COLS,RATE_COLS)


if __name__ == '__main__':
  # read output from `fetch_raw_census_data.py` into data frame
  data_df = pd.read_csv(
    sys.stdin,
    dtype={
      'GEOID': 'object',
      'name': 'object',
      'parent-location': 'object'
    })

  # grab the duplicates
  dupes = data_df[data_df.duplicated(subset=['GEOID', 'year'], keep=False)]

  # if there are no duplicates, return the existing dataframe
  if dupes.empty:
    data_df.to_csv(sys.stdout, index=False)
    exit()

  # get total populations
  total_pop_df = pd.DataFrame(
    dupes.groupby(['GEOID', 'year' ])['population'].sum()).reset_index()
  total_pop_df.rename(columns={'population': 'total_pop'}, inplace=True)

  # calculate weights with total pop
  dupes = dupes.merge(total_pop_df, on=['GEOID', 'year'], how='left')
  dupes['weight'] = dupes['population']/dupes['total_pop']
  for r in RATE_COLS:
    dupes[r] = dupes[r]*dupes['weight']
  dupes.drop(columns=['weight'], inplace=True)

  # Sum up duplicate rows with calculated weights
  singles_df = pd.DataFrame(
      dupes.groupby(['GEOID',
                          'year'])[COUNT_COLS + RATE_COLS].sum()).reset_index()

  # Drop the duplicated rows
  data_df.drop_duplicates(subset=['GEOID', 'year'], keep=False, inplace=True)

  # Add the merged rows
  output_df = pd.concat([ data_df, singles_df ])
  
  output_df.to_csv(sys.stdout, index=False)
