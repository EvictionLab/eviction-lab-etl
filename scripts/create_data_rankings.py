import os
import re
import sys
import numpy as np
import pandas as pd

DATA_COLS = ['GEOID', 'name', 'parent-location', 'population', 'evictions', 'eviction-rate']

LOW_POP_CUTOFF = 20000
MID_POP_CUTOFF = 100000


# Assign area type based off of population
def area_type(pop):
    if pop < LOW_POP_CUTOFF:
        return 2
    if pop >= LOW_POP_CUTOFF and pop < MID_POP_CUTOFF:
        return 1
    return 0


if __name__ == '__main__':
    data_df = pd.read_csv(
        sys.argv[1],
        engine='python',
        dtype={'GEOID': 'object', 'name': 'object', 'parent-location': 'object'}
    )
    # Get only most recent data, necessary columns
    # FIXME: Uncomment when this lines up
    # max_year = city_data_df['year'].max()
    max_year = 2015
    data_df = data_df.loc[data_df['year'] == max_year][DATA_COLS].copy()

    center_df = pd.read_csv(
        sys.argv[2],
        engine='python',
        dtype={'properties/GEOID': 'object'}
    )
    center_df.rename(columns={
        'properties/GEOID': 'GEOID',
        'geometry/coordinates/0': 'lon',
        'geometry/coordinates/1': 'lat'
    }, inplace=True)
    center_df = center_df[['GEOID', 'lon', 'lat']].copy()
    geoid_len = 7 if 'cities' in sys.argv[1] else 2
    center_df['GEOID'] = center_df['GEOID'].str.zfill(geoid_len)

    df = data_df.merge(center_df, on=['GEOID'], how='left')
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df[['lat', 'lon']] = df[['lat', 'lon']].round(4)
    if 'cities' in sys.argv[1]:
        df['area-type'] = df['population'].apply(area_type)
    df.drop('population', axis=1, inplace=True)

    # Write CSV file
    df.to_csv(sys.argv[3], index=False)
