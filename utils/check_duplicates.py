import os
import sys
import csv
import pandas as pd
import sys



if __name__ == '__main__':
    # read output from `fetch_raw_census_data.py` into data frame
    data_df = pd.read_csv(
        sys.stdin,
        dtype={
            'GEOID': 'object',
            'name': 'object',
            'parent-location': 'object'
        })

    dupes = data_df[data_df.duplicated(subset=['GEOID', 'year'], keep=False)]

    if sys.argv[1] == 'drop':
        dupes = dupes.drop_duplicates(subset=['GEOID'])

    dupes.to_csv(sys.stdout)