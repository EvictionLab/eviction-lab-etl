import os
import re
import sys
import csv
import json
import requests
import numpy as np
import pandas as pd
from census import Census
from census_data import *

c = Census(os.getenv('CENSUS_KEY'))

CENSUS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'census')

STATE_FIPS = c.acs5.get(('NAME'), {'for': 'state:*'})
STATE_FIPS_MAP = {s['state']: s['NAME'] for s in STATE_FIPS}

STATE_COUNTY_FIPS = c.acs5.get(('NAME'), {'for': 'county:*', 'in': 'state:*'})
COUNTY_FIPS_MAP = {str(c['state']).zfill(2) + str(c['county']).zfill(3): c['NAME'] for c in STATE_COUNTY_FIPS}

GEO_HIERARCHY = {
    'states': {'for': 'state:*'},
    'counties': {'for': 'county:*', 'in': 'state:*'},
    'cities': {'for': 'place:*', 'in': 'state:*'}
}

CENSUS_JOIN_KEYS = {
    'states': ['state'],
    'counties': ['state', 'county'],
    'cities': ['state', 'place'],
    'tracts': ['state', 'county', 'tract']
}

DATA_CLEANUP_FUNCS = {
    'states': {
        'geoid': lambda x: str(x['state']).zfill(2),
        'parent-location': lambda x: 'USA'
    },
    'counties': {
        'geoid': lambda x: str(x['state']).zfill(2) + str(x['county']).zfill(3),
        'parent-location': lambda x: STATE_FIPS_MAP[x['state']]
    },
    'cities': {
        'geoid': lambda x: str(x['state']).zfill(2) + str(x['place']).zfill(5),
        'parent-location': lambda x: STATE_FIPS_MAP[x['state']]
    },
    'tracts': {
        'geoid': lambda x: str(x['state']).zfill(2) + str(x['county']).zfill(3) + str(x['tract']).zfill(6),
        'parent-location': lambda x: COUNTY_FIPS_MAP.get(str(x['state']).zfill(2) + str(x['county']).zfill(3), STATE_FIPS_MAP[str(x['state']).zfill(2)])
    },
    'block-groups': {
        'geoid': lambda x: str(x['state']).zfill(2) + str(x['county']).zfill(3) + str(x['tract']).zfill(6) + str(x['block group']),
        'parent-location': lambda x: str(x['tract']).lstrip('0')
    }
}


def state_county_sub_data(census_obj, geo_str, census_vars, year):
    geo_df_list = []
    if geo_str == 'tracts' and year != 1990:
        fips_list = STATE_FIPS
    else:
        fips_list = STATE_COUNTY_FIPS
    lookup_dict = {'for': '{}:*'.format(geo_str.replace('-', ' ')[:-1])}
    for f in fips_list:
        if geo_str == 'tracts':
            lookup_dict['in'] = 'county:{} state:{}'.format(
                f.get('county', '*'), f['state']
            )
        elif geo_str == 'block-groups':
            lookup_dict['in'] = 'county:{} state:{}'.format(f['county'], f['state'])
        geo_df_list.append(pd.DataFrame(census_obj.get(
            census_vars, lookup_dict, year=year
        )))
    return pd.concat(geo_df_list)


def generated_cols(df):
    df['pct-renter-occupied'] = df.apply(lambda x: (x['renter-occupied-households'] / x['occupied-housing-units']) * 100 if x['occupied-housing-units'] > 0 else 0, axis=1)
    if 'poverty-pop' in df.columns.values:
        df[['population', 'poverty-pop']] = df[['population', 'poverty-pop']].apply(pd.to_numeric)
        pop_col = 'population'
        if 'total-poverty-pop' in df.columns.values:
            pop_col = 'total-poverty-pop'
            df[[pop_col]] = df[[pop_col]].apply(pd.to_numeric)
        df['poverty-rate'] = df.apply(lambda x: (x['poverty-pop'] / x[pop_col]) * 100 if x[pop_col] > 0 else 0, axis=1)
    else:
        # Should nulls be handled this way here?
        df['poverty-rate'] = np.nan
    for dem in ['hispanic', 'white', 'af-am', 'am-ind', 'asian', 'nh-pi', 'other', 'multiple']:
        if dem + '-pop' in df.columns.values:
            df[[dem + '-pop']] = df[[dem + '-pop']].apply(pd.to_numeric)
            df['pct-{}'.format(dem)] = df.apply(lambda x: (x['{}-pop'.format(dem)] / x['population']) * 100 if x['population'] > 0 else 0, axis=1)
    return df


def clean_data_df(df, geo_str):
    if geo_str == 'tracts':
        df['name'] = df['tract'].apply(lambda x: str(x).lstrip('0'))
    elif geo_str == 'block-groups':
        if df['year'].max() < 2000:
            df['name'] = df['GEOID'].apply(lambda x: (x[5:11] + '.' + x[11]).lstrip('0'))
            df['parent-location'] = df['GEOID'].apply(lambda x: str(x[5:11]).lstrip('0'))
        else:
            df['name'] = df.apply(lambda x: df['tract'].str.lstrip('0') + '.' + df['block group'], axis=1)
    df['name'] = df['name'].apply(lambda x: (str(x).split(',')[0]).lstrip('0'))
    if 'GEOID' not in df.columns.values:
        df['GEOID'] = df.apply(DATA_CLEANUP_FUNCS[geo_str]['geoid'], axis=1)
    if 'parent-location' not in df.columns.values:
        df['parent-location'] = df.apply(DATA_CLEANUP_FUNCS[geo_str]['parent-location'], axis=1)
    df_numeric = [c for c in NUMERIC_COLS if c in df.columns.values]
    df[df_numeric] = df[df_numeric].apply(pd.to_numeric)
    df = generated_cols(df)
    for col in OUTPUT_COLS:
        if col not in df.columns.values:
            df[col] = np.nan
    return df[OUTPUT_COLS].copy()


def get_block_groups_90_data():
    df = pd.read_csv(
        os.path.join(CENSUS_DIR, '90', 'block-groups.csv'),
        dtype={'GEOID': 'object', 'parent-location': 'object'},
        encoding='utf-8'
    )
    df.rename(columns=CENSUS_90_BG_VAR_MAP, inplace=True)
    census_df_list = []
    for year in range(1990, 2000):
        df_copy = df.copy()
        df_copy['year'] = year
        census_df_list.append(df_copy)
    return pd.concat(census_df_list)


def get_block_groups_data(year_str):
    df_list = []
    df_iter = pd.read_csv(
        os.path.join(CENSUS_DIR, year_str, 'block-groups.csv'),
        dtype={'state': 'object', 'county': 'object', 'tract': 'object', 'block group': 'object'},
        encoding='utf-8',
        iterator=True,
        chunksize=10000
    )
    for df in df_iter:
        df['GEOID'] = df.apply(DATA_CLEANUP_FUNCS['block-groups']['geoid'], axis=1)
        df.set_index('GEOID', inplace=True)
        df['name'] = df['tract'].str.lstrip('0') + '.' + df['block group']
        df['parent-location'] = df.apply(DATA_CLEANUP_FUNCS[geo_str]['parent-location'], axis=1)
        df_numeric = [c for c in NUMERIC_COLS if c in df.columns.values]
        df[df_numeric] = df[df_numeric].apply(pd.to_numeric)
        df = generated_cols(df)
        for col in OUTPUT_COLS:
            if col not in df.columns.values:
                df[col] = np.nan
        df_list.append(df[OUTPUT_COLS])
    return pd.concat(df_list)


def get_90_data(geo_str):
    if geo_str == 'states':
        census_sf1_df = pd.DataFrame(c.sf1.get(
            CENSUS_90_SF1_VARS, {'for': 'state:*'}, year=1990
        ))
        census_sf3_df = pd.DataFrame(c.sf3.get(
            CENSUS_90_SF3_VARS, {'for': 'state:*'}, year=1990
        ))
    elif geo_str == 'counties':
        census_sf1_df = pd.DataFrame(c.sf1.get(
            CENSUS_90_SF1_VARS, {'for': 'county:*', 'in': 'state:*'}, year=1990
        ))
        census_sf3_df = pd.DataFrame(c.sf3.get(
            CENSUS_90_SF3_VARS, {'for': 'county:*', 'in': 'state:*'}, year=1990
        ))
    elif geo_str == 'cities':
        census_sf1_df = pd.DataFrame(c.sf1.get(
            CENSUS_90_SF1_VARS, {'for': 'place:*', 'in': 'state:*'}, year=1990
        ))
        census_sf3_df = pd.DataFrame(c.sf3.get(
            CENSUS_90_SF3_VARS, {'for': 'place:*', 'in': 'state:*'}, year=1990
        ))
    else:
        census_sf1_df = state_county_sub_data(c.sf1, geo_str, CENSUS_90_SF1_VARS, 1990)
        census_sf3_df = state_county_sub_data(c.sf3, geo_str, CENSUS_90_SF3_VARS, 1990)

    census_sf1_df.rename(columns=CENSUS_90_SF1_VAR_MAP, inplace=True)
    census_sf3_df.rename(columns=CENSUS_90_SF3_VAR_MAP, inplace=True)
    census_df = pd.merge(census_sf1_df, census_sf3_df, how='left', on=CENSUS_JOIN_KEYS.get(geo_str))

    census_df_list = []
    for year in range(1990, 2000):
        census_copy = census_df.copy()
        census_copy['year'] = year
        census_df_list.append(census_copy)
    return pd.concat(census_df_list)


def get_00_data(geo_str):
    if geo_str == 'states':
        census_sf1_df = pd.DataFrame(c.sf1.get(
            CENSUS_00_SF1_VARS, {'for': 'state:*'}, year=2000
        ))
        census_sf3_df = pd.DataFrame(c.sf3.get(
            CENSUS_00_SF3_VARS, {'for': 'state:*'}, year=2000
        ))
        acs_df = pd.DataFrame(c.acs5.get(
            ACS_VARS, {'for': 'state:*'}, year=2009
        ))
    # For some reason the Census API for 2000 SF3 counties uses quotes instead of
    # apostrophes which breaks JSON validation. Using requests manually to fix
    elif geo_str == 'counties':
        res_sf1 = requests.get('{}2000/sf1?get={}&for=county:*&in=state:*&key={}'.format(
            CENSUS_API_BASE, ','.join(CENSUS_00_SF1_VARS), os.getenv('CENSUS_KEY')
        ))
        census_sf1_json = json.loads(re.sub(r'(?<=[\w\s])"(?=[\w\s])', "'", res_sf1.text))
        census_sf1_df = pd.DataFrame([
            dict(zip(list(CENSUS_00_SF1_VARS) + ['state', 'county'], r)) for r in census_sf1_json[1:]
        ])
        res_sf3 = requests.get('{}2000/sf3?get={}&for=county:*&in=state:*&key={}'.format(
            CENSUS_API_BASE, ','.join(CENSUS_00_SF3_VARS), os.getenv('CENSUS_KEY')
        ))
        census_sf3_json = json.loads(re.sub(r'(?<=[\w\s])"(?=[\w\s])', "'", res_sf3.text))
        census_sf3_df = pd.DataFrame([
            dict(zip(list(CENSUS_00_SF3_VARS) + ['state', 'county'], r)) for r in census_sf3_json[1:]
        ])
        acs_df = pd.DataFrame(c.acs5.get(
            ACS_VARS, {'for': 'county:*', 'in': 'state:*'}, year=2009
        ))
    elif geo_str == 'cities':
        res_sf1 = requests.get('{}2000/sf1?get={}&for=place:*&in=state:*&key={}'.format(
            CENSUS_API_BASE, ','.join(CENSUS_00_SF1_VARS), os.getenv('CENSUS_KEY')
        ))
        census_sf1_json = json.loads(re.sub(r'(?<=[\w\s])"(?=[\w\s])', "'", res_sf1.text))
        census_sf1_df = pd.DataFrame([
            dict(zip(list(CENSUS_00_SF1_VARS) + ['state', 'place'], r)) for r in census_sf1_json[1:]
        ])
        res_sf3 = requests.get('{}2000/sf3?get={}&for=place:*&in=state:*&key={}'.format(
            CENSUS_API_BASE, ','.join(CENSUS_00_SF3_VARS), os.getenv('CENSUS_KEY')
        ))
        census_sf3_json = json.loads(re.sub(r'(?<=[\w\s])"(?=[\w\s])', "'", res_sf3.text))
        census_sf3_df = pd.DataFrame([
            dict(zip(list(CENSUS_00_SF3_VARS) + ['state', 'place'], r)) for r in census_sf3_json[1:]
        ])
        acs_df = pd.DataFrame(c.acs5.get(
            ACS_VARS, {'for': 'place:*', 'in': 'state:*'}, year=2009
        ))
    else:
        census_sf1_df = state_county_sub_data(c.sf1, geo_str, CENSUS_00_SF1_VARS, 2000)
        census_sf3_df = state_county_sub_data(c.sf3, geo_str, CENSUS_00_SF3_VARS, 2000)
        acs_df = state_county_sub_data(c.acs5, geo_str, ACS_VARS, 2009)

    census_sf1_df.rename(columns=CENSUS_00_SF1_VAR_MAP, inplace=True)
    census_sf3_df.rename(columns=CENSUS_00_SF3_VAR_MAP, inplace=True)
    census_df = pd.merge(census_sf1_df, census_sf3_df, how='left', on=CENSUS_JOIN_KEYS.get(geo_str))
    acs_df.rename(columns=ACS_VAR_MAP, inplace=True)

    census_df_list = []
    for year in range(2000, 2005):
        census_copy = census_df.copy()
        census_copy['year'] = year
        census_df_list.append(census_copy)

    acs_df_list = []
    for year in range(2005, 2010):
        acs_copy = acs_df.copy()
        acs_copy['year'] = year
        acs_df_list.append(acs_copy)

    return pd.concat(census_df_list + acs_df_list)


def get_10_data(geo_str):
    if geo_str == 'states':
        census_df = pd.DataFrame(c.sf1.get(
            CENSUS_10_VARS, {'for': 'state:*'}, year=2010
        ))
        acs_12_df = pd.DataFrame(c.acs5.get(
            ACS_12_VARS, {'for': 'state:*'}, year=2012
        ))
        acs_df = pd.DataFrame(c.acs5.get(
            ACS_VARS, {'for': 'state:*'}, year=2015
        ))
    elif geo_str == 'counties':
        census_df = pd.DataFrame(c.sf1.get(
            CENSUS_10_VARS, {'for': 'county:*', 'in': 'state:*'}, year=2010
        ))
        acs_12_df = pd.DataFrame(c.acs5.get(
            ACS_12_VARS, {'for': 'county:*', 'in': 'state:*'}, year=2012
        ))
        acs_df = pd.DataFrame(c.acs5.get(
            ACS_VARS, {'for': 'county:*', 'in': 'state:*'}, year=2015
        ))
    elif geo_str == 'cities':
        census_df = pd.DataFrame(c.sf1.get(
            CENSUS_10_VARS, {'for': 'place:*', 'in': 'state:*'}, year=2010
        ))
        acs_12_df = pd.DataFrame(c.acs5.get(
            ACS_12_VARS, {'for': 'place:*', 'in': 'state:*'}, year=2012
        ))
        acs_df = pd.DataFrame(c.acs5.get(
            ACS_VARS, {'for': 'place:*', 'in': 'state:*'}, year=2015
        ))
    else:
        census_df = state_county_sub_data(c.sf1, geo_str, CENSUS_10_VARS, 2010)
        acs_12_df = state_county_sub_data(c.acs5, geo_str, ACS_12_VARS, 2012)
        acs_df = state_county_sub_data(c.acs5, geo_str, ACS_VARS, 2015)

    census_df.rename(columns=CENSUS_10_VAR_MAP, inplace=True)
    acs_12_df.rename(columns=ACS_12_VAR_MAP, inplace=True)

    # Merge vars that are only in ACS to 2010 census
    if geo_str == 'states':
        acs_merge_keys = ['state']
    elif geo_str == 'counties':
        acs_merge_keys = ['state', 'county']
    elif geo_str == 'cities':
        acs_merge_keys = ['state', 'place']
    elif geo_str == 'tracts':
        acs_merge_keys  = ['state', 'county', 'tract']
    census_df = census_df.merge(acs_12_df, on=acs_merge_keys, how='left')

    acs_df.rename(columns=ACS_VAR_MAP, inplace=True)

    census_df['year'] = 2010
    acs_df_list = []
    for year in range(2011, 2017):
        acs_copy = acs_df.copy()
        acs_copy['year'] = year
        acs_df_list.append(acs_copy)

    return pd.concat([census_df] + acs_df_list)


if __name__ == '__main__':
    data_str = sys.argv[1]
    geo_str = '-'.join(data_str.split('-')[:-1])
    year_str = data_str.split('-')[-1]

    if year_str == '90':
        if geo_str == 'block-groups':
            data_df = get_block_groups_90_data()
        else:
            data_df = get_90_data(geo_str)
    elif year_str == '00':
        if geo_str == 'block-groups':
            data_df = get_block_groups_data(year_str)
        else:
            data_df = get_00_data(geo_str)
    elif year_str == '10':
        if geo_str == 'block-groups':
            data_df = get_block_groups_data(year_str)
        else:
            data_df = get_10_data(geo_str)
    else:
        raise ValueError('An invalid argument was supplied')

    if year_str != '90' and geo_str != 'block-groups':
        data_df = clean_data_df(data_df, geo_str).round(2)
    data_df.to_csv(sys.stdout, index=False, quoting=csv.QUOTE_NONNUMERIC)
