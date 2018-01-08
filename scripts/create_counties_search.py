import os
import re
import sys
import numpy as np
import pandas as pd


if __name__ == '__main__':
    county_data_df = pd.read_csv(
        sys.argv[1],
        engine='python',
        dtype={'GEOID': 'object', 'name': 'object', 'parent-location': 'object'}
    )
    county_data_df.drop_duplicates(subset=['GEOID'], inplace=True)
    county_data_df['name'] = county_data_df['name'] + ', ' + county_data_df['parent-location']
    county_data_df = county_data_df[['GEOID', 'name']].copy()

    county_center_df = pd.read_csv(
        sys.argv[2],
        engine='python',
        dtype={'properties/GEOID': 'object'}
    )
    county_center_df.rename(columns={
        'properties/GEOID': 'GEOID',
        'properties/north': 'north',
        'properties/south': 'south',
        'properties/east': 'east',
        'properties/west': 'west',
        'geometry/coordinates/0': 'lon',
        'geometry/coordinates/1': 'lat'
    }, inplace=True)
    county_center_df = county_center_df[['GEOID', 'north', 'south', 'east', 'west', 'lon', 'lat']].copy()
    county_center_df['GEOID'] = county_center_df['GEOID'].str.zfill(5)

    county_df = county_data_df.merge(county_center_df, on=['GEOID'], how='left')
    county_df.replace([np.inf, -np.inf], np.nan, inplace=True)
    county_df[['north', 'south', 'east', 'west', 'lat', 'lon']] = county_df[['north', 'south', 'east', 'west', 'lat', 'lon']].round(4)

    # Write CSV file
    county_df.to_csv(sys.argv[3], index=False)
