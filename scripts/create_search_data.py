import sys
import numpy as np
import pandas as pd

if __name__ == '__main__':
    df = pd.read_csv(
        sys.argv[1],
        engine='python',
        dtype={
            'GEOID': 'object',
            'name': 'object',
            'parent-location': 'object'
        })
    df.drop_duplicates(subset=['GEOID'], inplace=True)
    if df['parent-location'].iloc[0] == 'USA':
        df['layer'] = 'states'
        geoid_len = 2
    else:
        df['name'] = df['name'] + ', ' + df['parent-location']
        if 'counties' in sys.argv[1]:
            df['layer'] = 'counties'
            geoid_len = 5
        elif 'cities' in sys.argv[1]:
            df['layer'] = 'cities'
            geoid_len = 7
    df = df[['GEOID', 'name', 'layer']].copy()

    center_df = pd.read_csv(
        sys.argv[2], engine='python', dtype={'properties/GEOID': 'object'})
    center_df.rename(
        columns={
            'properties/GEOID': 'GEOID',
            'properties/north': 'north',
            'properties/south': 'south',
            'properties/east': 'east',
            'properties/west': 'west',
            'geometry/coordinates/0': 'lon',
            'geometry/coordinates/1': 'lat'
        },
        inplace=True)
    center_df = center_df[[
        'GEOID', 'north', 'south', 'east', 'west', 'lon', 'lat'
    ]].copy()
    center_df['GEOID'] = center_df['GEOID'].str.zfill(geoid_len)

    output_df = df.merge(center_df, on=['GEOID'], how='left')
    output_df.replace([np.inf, -np.inf], np.nan, inplace=True)
    output_df[['north', 'south', 'east', 'west', 'lat', 'lon']] = output_df[[
        'north', 'south', 'east', 'west', 'lat', 'lon'
    ]].round(4)

    # Write CSV file
    output_df.to_csv(sys.argv[3], index=False)
