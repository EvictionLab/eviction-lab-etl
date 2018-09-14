###
# Generate breakdown of missing data by `group_col`
###

import sys
import csv
import pandas as pd

if __name__ == '__main__':
  df = pd.read_csv(
    sys.stdin,
    dtype = {
      'GEOID': 'object'
    }
  )

  # column name to group by
  group_col = 'parent-location'

  # check if parent location contains a county and state, if so use state to group
  if ',' in df.iloc[0][group_col]:
    df['county'], df['state'] = df[group_col].str.split(', ', 1).str
    group_col = 'state'

  # check if input is states.csv and group by 'name' field instead
  if df.iloc[0][group_col] == 'USA':
    group_col = 'name'

  # count records by `group_col`
  full_counts = df[group_col].value_counts()

  # get all rows that contain at least one null value
  null_data = df[df.isnull().any(axis=1)]

  # create a series containing row counts with missing data grouped by `group_col`
  null_counts = null_data[group_col].value_counts()

  # combine null counts with full counts
  grouped_missing_df=pd.concat([full_counts, null_counts], axis=1).reset_index()

  # rename cols
  grouped_missing_df.columns = ['location', 'total', 'missing']

  # drop rows where there is no missing data
  grouped_missing_df.dropna(subset=['missing'],inplace=True)

  # add missing percent column
  grouped_missing_df['missing_percent']=grouped_missing_df['missing']/grouped_missing_df['total']
  
  # output as csv
  grouped_missing_df.to_csv(sys.stdout, index=False, quoting=csv.QUOTE_NONNUMERIC)