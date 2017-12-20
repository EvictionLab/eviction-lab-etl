import os
import re
import sys
import numpy as np
import pandas as pd


DATA_COLS = ['GEOID', 'name', 'parent-location', 'evictions', 'eviction-filings', 'eviction-rate', 'eviction-filing-rate']

if __name__ == '__main__':
    city_data_df = pd.read_csv(
        sys.argv[1],
        engine='python',
        dtype={'GEOID': 'object', 'name': 'object', 'parent-location': 'object'}
    )
    # Get only most recent data, necessary columns
    max_year = city_data_df['year'].max()
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

    # Write CSV file
    city_df.to_csv(sys.argv[3], index=False)
