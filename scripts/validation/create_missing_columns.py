###
# Generate breakdown of missing data by column name
###
# Output:
# | field                | missing                  | missing_percent            |
# | -------------------- | ------------------------ | -------------------------- |
# | column name          | count of missing entries | percent of missing entries |
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

  # get total number of rows
  row_count=df.shape[0]

  # get columns that have at least one null value
  null_columns=df.columns[df.isnull().any()]

  # count the number of null values per column
  null_count=df[null_columns].isnull().sum()

  # create data frame for missing data
  missing_df=pd.DataFrame({'missing': null_count})

  # add column for percent missing
  missing_df['missing_percent']=missing_df['missing']/row_count

  # output as csv
  missing_df.to_csv(sys.stdout, index=True, index_label='field', quoting=csv.QUOTE_NONNUMERIC)
