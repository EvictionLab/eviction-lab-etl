import os
import re
import sys
import csv
import json
import requests
import numpy as np
import pandas as pd
from census import Census

CENSUS_API_BASE = 'https://api.census.gov/data/'

ACS_VAR_MAP = {
    'NAME': 'name',
    'B01003_001E': 'population',
    'B17001_002E': 'poverty-pop',
    'B25010_001E': 'average-household-size',
    'B25111_001E': 'median-gross-rent',
    'B25001_001E': 'housing-units',
    'B25002_003E': 'vacant-housing-units',
    'B25003_001E': 'occupied-housing-units',
    'B25003_003E': 'renter-occupied-households',
    'B19013_001E': 'median-household-income',
    'B25077_001E': 'median-property-value',
    'B03002_012E': 'hispanic-pop',
    'B03002_003E': 'white-pop',
    'B03002_004E': 'af-am-pop',
    'B03002_005E': 'am-ind-pop',
    'B03002_006E': 'asian-pop',
    'B03002_007E': 'nh-pi-pop',
    'B03002_008E': 'other-pop',
    'B03002_009E': 'multiple-pop'
}

ACS_12_VAR_MAP = {
    'B17001_002E': 'poverty-pop',
    'B25111_001E': 'median-gross-rent',
    'B19013_001E': 'median-household-income',
    'B25077_001E': 'median-property-value'
}

BG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'census', '90')

CENSUS_90_BG_VAR_MAP = {
    'p0010001': 'population',
    'h0010001': 'housing-units',
    'h0040002': 'vacant-housing-units',
    'h0040001': 'occupied-housing-units',
    'h0080002': 'renter-occupied-households',
    'h061a001': 'median-property-value',
    # Average household size?
    'p0080001': 'hispanic-pop',
    'p0110001': 'white-pop',
    'p0110002': 'af-am-pop',
    'p0110003': 'am-ind-pop',
    # Combines Asian and Native Hawaiian, treating as nh-pi-pop
    'p0110004': 'nh-pi-pop',
    'p0110005': 'other-pop'
}

CENSUS_90_VAR_MAP = {
    'ANPSADPI': 'name',
    'P0010001': 'population',
    # Can't find one single summary stat for overall poverty
    'H043A001': 'median-gross-rent',
    'H0010001': 'housing-units',
    'H0040002': 'vacant-housing-units',
    'H0040001': 'occupied-housing-units',
    'H0080002': 'renter-occupied-households',
    'P080A001': 'median-household-income',
    'H061A001': 'median-property-value',
    # Average household size?
    'P0100001': 'hispanic-pop',
    'P0120001': 'white-pop',
    'P0120002': 'af-am-pop',
    'P0120003': 'am-ind-pop',
    # Combines Asian and Native Hawaiian, treating as nh-pi-pop
    'P0120004': 'asian-pop',
    'P0120005': 'other-pop'
}

CENSUS_00_VAR_MAP = {
    'NAME': 'name',
    'P001001': 'population',
    # total-poverty-pop is "Population for whom poverty status is determined"
    'P087001': 'total-poverty-pop',
    'P087002': 'poverty-pop',
    'P017001': 'average-household-size',
    'H063001': 'median-gross-rent',
    'H001001': 'housing-units',
    'H002003': 'vacant-housing-units',
    'H002002': 'occupied-housing-units',
    'H007003': 'renter-occupied-households',
    'P053001': 'median-household-income',
    'H076001': 'median-property-value',
    'P007010': 'hispanic-pop',
    'P007011': 'white-pop',
    'P007012': 'af-am-pop',
    'P007013': 'am-ind-pop',
    'P007014': 'asian-pop',
    'P007015': 'nh-pi-pop',
    'P007016': 'other-pop',
    'P007017': 'multiple-pop'
}

CENSUS_10_VAR_MAP = {
    'NAME': 'name',
    'P0030001': 'population',
    'H00010001': 'housing-units',
    'H0030003': 'vacant-housing-units',
    'H0040001': 'occupied-housing-units',
    'H0040004': 'renter-occupied-households',
    'H0120001': 'average-household-size',
    'P0040003': 'hispanic-pop',
    'P0050003': 'white-pop',
    'P0050004': 'af-am-pop',
    'P0050005': 'am-ind-pop',
    'P0050006': 'asian-pop',
    'P0050007': 'nh-pi-pop',
    'P0050008': 'other-pop',
    'P0050009': 'multiple-pop'
}

# TODO: Add int cols to compress size
NUMERIC_COLS = [
    'population',
    'poverty-pop',
    'average-household-size',
    'median-gross-rent',
    'housing-units',
    'vacant-housing-units',
    'occupied-housing-units',
    'renter-occupied-households',
    'median-household-income',
    'median-property-value',
    'hispanic-pop',
    'white-pop',
    'af-am-pop',
    'am-ind-pop',
    'asian-pop',
    'nh-pi-pop',
    'other-pop',
    'multiple-pop'
]

OUTPUT_COLS = [
    'GEOID',
    'name',
    'parent-location',
    'year',
    'population',
    'poverty-rate',
    'average-household-size',
    'renter-occupied-households',
    'pct-renter-occupied',
    'median-gross-rent',
    'median-household-income',
    'median-property-value',
    'pct-white',
    'pct-af-am',
    'pct-hispanic',
    'pct-am-ind',
    'pct-asian',
    'pct-nh-pi',
    'pct-multiple',
    'pct-other'
]

ACS_VARS = tuple(ACS_VAR_MAP.keys())
ACS_12_VARS = tuple(ACS_12_VAR_MAP.keys())
CENSUS_90_VARS = tuple(CENSUS_90_VAR_MAP.keys())
CENSUS_00_VARS = tuple(CENSUS_00_VAR_MAP.keys())
CENSUS_10_VARS = tuple(CENSUS_10_VAR_MAP.keys())

c = Census(os.getenv('CENSUS_KEY'))

STATE_FIPS = c.acs5.get(('NAME'), {'for': 'state:*'})
STATE_FIPS_MAP = {s['state']: s['NAME'] for s in STATE_FIPS}

STATE_COUNTY_FIPS = c.acs5.get(('NAME'), {'for': 'county:*', 'in': 'state:*'})
COUNTY_FIPS_MAP = {str(c['state']).zfill(2) + str(c['county']).zfill(3): c['NAME'] for c in STATE_COUNTY_FIPS}

GEO_HIERARCHY = {
    'states': {'for': 'state:*'},
    'counties': {'for': 'county:*', 'in': 'state:*'},
    'cities': {'for': 'place:*', 'in': 'state:*'}
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
        'parent-location': lambda x: x['tract'].zfill(6)
    }
}


def state_county_sub_data(census_obj, geo_str, census_vars, year):
    geo_df_list = []
    fips_list = STATE_FIPS if geo_str == 'tracts' else STATE_COUNTY_FIPS
    lookup_dict = {'for': '{}:*'.format(geo_str.replace('-', ' ')[:-1])}
    for f in fips_list:
        if geo_str == 'tracts':
            lookup_dict['in'] = 'state:{}'.format(f['state'])
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
        df['name'] = df['name'].apply(lambda x: x[13:])
    elif geo_str == 'block-groups':
        if df['year'].max() < 2000:
            df['name'] = df['GEOID'].apply(lambda x: x[5:11] + '.' + x[11])
            df['parent-location'] = df['GEOID'].apply(lambda x: x[5:11])
        else:
            df['name'] = df.apply(lambda x: df['tract'] + '.' + df['block group'], axis=1)
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
    df = pd.read_csv(os.path.join(BG_DIR, 'block-groups-90.csv'), dtype={'GEOID': 'object'})
    df.rename(columns=CENSUS_90_BG_VAR_MAP, inplace=True)
    census_df_list = []
    for year in range(1990, 2000):
        df_copy = df.copy()
        df_copy['year'] = year
        census_df_list.append(df_copy)
    return pd.concat(census_df_list)


def get_90_data(geo_str):
    if geo_str == 'states':
        census_df = pd.DataFrame(c.sf3.get(
            CENSUS_90_VARS, {'for': 'state:*'}, year=1990
        ))
    elif geo_str == 'counties':
        census_df = pd.DataFrame(c.sf3.get(
            CENSUS_90_VARS, {'for': 'county:*', 'in': 'state:*'}, year=1990
        ))
    elif geo_str == 'cities':
        census_df = pd.DataFrame(c.sf3.get(
            CENSUS_90_VARS, {'for': 'place:*', 'in': 'state:*'}, year=1990
        ))
    else:
        census_df = state_county_sub_data(c.sf3, geo_str, CENSUS_90_VARS, 1990)

    census_df.rename(columns=CENSUS_90_VAR_MAP, inplace=True)
    census_df_list = []
    for year in range(1990, 2000):
        census_copy = census_df.copy()
        census_copy['year'] = year
        census_df_list.append(census_copy)
    return pd.concat(census_df_list)


def get_00_data(geo_str):
    if geo_str == 'states':
        census_df = pd.DataFrame(c.sf3.get(
            CENSUS_00_VARS, {'for': 'state:*'}, year=2000
        ))
        acs_df = pd.DataFrame(c.acs5.get(
            ACS_VARS, {'for': 'state:*'}, year=2009
        ))
    # For some reason the Census API for 2000 SF3 counties uses quotes instead of
    # apostrophes which breaks JSON validation. Using requests manually to fix
    elif geo_str == 'counties':
        # census_df = pd.DataFrame(c.sf3.get(
        #     CENSUS_00_VARS, {'for': 'county:*', 'in': 'state:*'}, year=2000
        # ))
        res = requests.get('{}2000/sf3?get={}&for=county:*&in=state:*&key={}'.format(
            CENSUS_API_BASE, ','.join(CENSUS_00_VARS), os.getenv('CENSUS_KEY')
        ))
        census_json = json.loads(re.sub(r'(?<=[\w\s])"(?=[\w\s])', "'", res.text))
        census_df = pd.DataFrame([
            dict(zip(list(CENSUS_00_VARS) + ['state', 'county'], r)) for r in census_json[1:]
        ])
        acs_df = pd.DataFrame(c.acs5.get(
            ACS_VARS, {'for': 'county:*', 'in': 'state:*'}, year=2009
        ))
    elif geo_str == 'cities':
        # census_df = pd.DataFrame(c.sf3.get(
        #     CENSUS_00_VARS, {'for': 'place:*', 'in': 'state:*'}, year=2000
        # ))
        res = requests.get('{}2000/sf3?get={}&for=place:*&in=state:*&key={}'.format(
            CENSUS_API_BASE, ','.join(CENSUS_00_VARS), os.getenv('CENSUS_KEY')
        ))
        census_json = json.loads(re.sub(r'(?<=[\w\s])"(?=[\w\s])', "'", res.text))
        census_df = pd.DataFrame([
            dict(zip(list(CENSUS_00_VARS) + ['state', 'place'], r)) for r in census_json[1:]
        ])
        acs_df = pd.DataFrame(c.acs5.get(
            ACS_VARS, {'for': 'place:*', 'in': 'state:*'}, year=2009
        ))
    else:
        census_df = state_county_sub_data(c.sf3, geo_str, CENSUS_00_VARS, 2000)
        acs_df = state_county_sub_data(c.acs5, geo_str, ACS_VARS, 2009)

    census_df.rename(columns=CENSUS_00_VAR_MAP, inplace=True)
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
    elif geo_str == 'block-groups':
        acs_merge_keys = ['state', 'county', 'tract', 'block group']
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
        data_df = get_00_data(geo_str)
    elif year_str == '10':
        data_df = get_10_data(geo_str)
    else:
        raise ValueError('An invalid argument was supplied')

    data_df = clean_data_df(data_df, geo_str).round(2)
    data_df.to_csv(sys.stdout, index=False, quoting=csv.QUOTE_NONNUMERIC)
