import sys
import pandas as pd
from functools import reduce
from utils_validation import log_dem_eviction_comparison

INT_COLS = ['imputed', 'subbed', 'low-flag']

if __name__ == '__main__':
    join_keys = sys.argv[1].split(',')
    dtypes = {k: 'object' for k in join_keys}
    dtypes['name'] = 'object'
    dtypes['parent-location'] = 'object'

    # demographics dataframe
    dem_df = pd.read_csv(sys.argv[2], dtype=dtypes)

    # dataframe containing names and parent locations
    names_df = dem_df.drop_duplicates('GEOID', keep='last')[['GEOID', 'name', 'parent-location']]
    names_df.set_index('GEOID', inplace=True)

    # drop name / parent-location from demographics
    dem_df = dem_df.drop(['name', 'parent-location'], axis=1)

    # eviction dataframe
    ev_df = pd.read_csv(sys.argv[3], dtype=dtypes)

    log_dem_eviction_comparison('demographics <- eviction data', dem_df, ev_df, on=join_keys)
    # join demographics with evictions
    ev_df.set_index(join_keys, inplace=True)
    dem_df.set_index(join_keys, inplace=True)
    joined_df = dem_df.join(ev_df, how='outer')

    # join names and parent locations
    joined_df.reset_index(level=['year'])
    output_df = pd.merge(names_df, joined_df, how='outer', left_index=True, right_index=True)

    # remove rows with no names
    output_df = output_df[output_df['name'].notnull()]

    # Handle int cols
    for col in INT_COLS:
        if col in output_df.columns:
            output_df[col] = output_df[col].fillna(0).astype(int)

    output_df.to_csv(sys.stdout)