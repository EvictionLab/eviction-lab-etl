# This script removes values flagged as bad from a data set.
#
# - stdin: the data set
# - sys.argv[1]: the path to a csv file that has a list of GEOID,year,value
#     where the "value" column contains the column name to remove data for
#
# NOTE: As of 12-06-18 there are no entries in `conf/bad-values-list.csv`
#   so this script isn't doing much.  However, it remains in case there
#   is a need in the future. 

import os
import csv
import sys
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

if __name__ == '__main__':

  df = pd.read_csv(
    sys.stdin,
    dtype={
        'GEOID': 'object',
        'name': 'object',
        'parent-location': 'object'
    })
  bad_values_df = pd.read_csv(
      sys.argv[1],
      dtype={'GEOID': 'object'}
    )

  for row in bad_values_df.itertuples():
    df.loc[
      (df['GEOID'] == getattr(row, "GEOID")) & (df['year'] == getattr(row, "year")), 
      [getattr(row, "value")]] = [ np.nan ]

  df.to_csv(sys.stdout, index=False, quoting=csv.QUOTE_NONNUMERIC)
