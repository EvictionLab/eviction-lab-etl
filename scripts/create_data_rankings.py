import os
import re
import sys
import numpy as np
import pandas as pd

DATA_COLS = [
    'GEOID', 'name', 'parent-location', 'population',
    'evictions', 'eviction-filings', 'eviction-rate', 'eviction-filing-rate'
]

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
    city_data_df = pd.read_csv(
        sys.argv[1],
        engine='python',
        dtype={'GEOID': 'object', 'name': 'object', 'parent-location': 'object'}
    )
    # Get only most recent data, necessary columns
    # FIXME: Uncomment when this lines up
    # max_year = city_data_df['year'].max()
    max_year = 2016
    city_data_df = city_data_df.loc[city_data_df['year'] == max_year][DATA_COLS].copy()

    city_center_df = pd.read_csv(
        sys.argv[2],
        engine='python',
        dtype={'properties/GEOID': 'object'}
    )
    city_center_df.rename(columns={
        'properties/GEOID': 'GEOID',
        'geometry/coordinates/0': 'lon',
        'geometry/coordinates/1': 'lat'
    }, inplace=True)
    city_center_df = city_center_df[['GEOID', 'lon', 'lat']].copy()
    city_center_df['GEOID'] = city_center_df['GEOID'].str.zfill(7)

    city_df = city_data_df.merge(city_center_df, on=['GEOID'], how='left')
    city_df.replace([np.inf, -np.inf], np.nan, inplace=True)
    city_df[['lat', 'lon']] = city_df[['lat', 'lon']].round(4)
    city_df['area-type'] = city_df['population'].apply(area_type)
    city_df.drop('population', axis=1, inplace=True)

    # Write CSV file
    city_df.to_csv(sys.argv[3], index=False)
