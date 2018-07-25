import os
import csv
import sys
import pandas as pd
from data_constants import COUNTY_CROSSWALK

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

if __name__ == '__main__':
    geo = sys.argv[1]
    df = pd.read_csv(
        sys.stdin,
        dtype={
            'GEOID': 'object',
            'name': 'object',
            'parent-location': 'object'
        })

    if geo == 'counties':
        for k, v in COUNTY_CROSSWALK.items():
            if ('name' in df.columns.values
                    and 'parent-location' in df.columns.values):
                df.loc[df['GEOID'] == k,
                       ['GEOID', 'name', 'parent-location']] = [
                           v['GEOID'], v['name'], v['parent-location']
                       ]
            else:
                df.loc[df['GEOID'] == k, 'GEOID'] = v['GEOID']
    elif geo == 'cities':
        city_df = pd.read_csv(
            os.path.join(BASE_DIR, 'conf', 'changed_census_places.csv'),
            dtype={
                'GEOID00': 'object',
                'GEOID10': 'object'
            })
        city_dicts = city_df.to_dict(orient='records')
        city_crosswalk = {
            d['GEOID00']: {
                'GEOID': d['GEOID10'],
                'name': d['NAME10']
            }
            for d in city_dicts
        }

        if 'name' in df.columns.values:
            df.loc[df['GEOID'].isin(city_crosswalk), 'name'] = df.loc[df[
                'GEOID'].isin(city_crosswalk), 'GEOID'].apply(
                    lambda x: city_crosswalk[x]['name'])
        df.loc[df['GEOID'].isin(city_crosswalk), 'GEOID'] = df.loc[df[
            'GEOID'].isin(city_crosswalk), 'GEOID'].apply(
                lambda x: city_crosswalk[x]['GEOID'])
    elif geo in ['tracts', 'block-groups']:
        for k, v in COUNTY_CROSSWALK.items():
            if 'parent-location' in df.columns.values:
                df.loc[df['GEOID'].str.startswith(k),
                       ['GEOID', 'parent-location']] = [
                           v['GEOID'] + df.loc[df['GEOID'].str.startswith(k),
                                               'GEOID'].str.slice(5),
                           v['name'] + ', ' + v['parent-location']
                       ]
            else:
                df.loc[
                    df['GEOID'].str.startswith(k),
                    'GEOID'] = v['GEOID'] + df.loc[df['GEOID'].str.startswith(
                        k), 'GEOID'].str.slice(5)

    df.to_csv(sys.stdout, index=False, quoting=csv.QUOTE_NONNUMERIC)
