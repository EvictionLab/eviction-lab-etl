import sys
import pandas as pd
from functools import reduce

INT_COLS = ['imputed', 'subbed', 'low-flag']

if __name__ == '__main__':
    join_keys = sys.argv[1].split(',')
    dtypes = {k: 'object' for k in join_keys}
    dtypes['name'] = 'object'
    dtypes['parent-location'] = 'object'
    df_list = []
    # demographics dataframe
    dem_df = pd.read_csv(sys.argv[2], dtype=dtypes)
    # dataframe containing names and parent locations
    names_df = dem_df.drop_duplicates('GEOID')[['GEOID', 'name', 'parent-location']]
    names_df.set_index('GEOID', inplace=True)
    # drop name / parent-location from demographics
    dem_df = dem_df.drop(['name', 'parent-location'], axis=1)
    # eviction dataframe
    ev_df = pd.read_csv(sys.argv[3], dtype=dtypes)
    # join demographics with evictions
    ev_df.set_index(join_keys, inplace=True)
    dem_df.set_index(join_keys, inplace=True)
    joined_df = dem_df.join(ev_df, how='outer')
    # join names and parent locations
    joined_df.reset_index(level=['year'])
    output_df = pd.merge(names_df, joined_df, how='outer', left_index=True, right_index=True)

    # Handle int cols
    for col in INT_COLS:
        if col in output_df.columns:
            output_df[col] = output_df[col].fillna(0).astype(int)

    output_df.to_csv(sys.stdout)
