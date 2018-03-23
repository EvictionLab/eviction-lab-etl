import os
import re
import sys
import csv
import json
import numpy as np
import pandas as pd
from census import Census
from data_constants import *


if os.getenv('CENSUS_KEY'):
    c = Census(os.getenv('CENSUS_KEY'))
else:
    raise Exception('Environment variable CENSUS_KEY not specified')

CENSUS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'census')

# Pull data for 50 states
STATE_FIPS = [r for r in c.acs5.get(('NAME'), {'for': 'state:*'}) if r['state'] != '72']
STATE_FIPS_MAP = {s['state']: s['NAME'] for s in STATE_FIPS}

STATE_COUNTY_FIPS = [
    r for r in c.acs5.get(('NAME'), {'for': 'county:*', 'in': 'state:*'}) if r['state'] != '72'
]
COUNTY_FIPS_MAP = {
    str(c['state']).zfill(2) + str(c['county']).zfill(3): c['NAME'] for c in STATE_COUNTY_FIPS
}

REMOVE_CITY_SUFFIXES = [
    'town', 'city', 'CDP', 'municipality', 'borough', '(balance)', 'village',
    'consolidated government', 'metro government', 'metropolitan government',
    'unified governm', 'unified government'
]

CENSUS_JOIN_KEYS = {
    'states': ['state'],
    'counties': ['state', 'county'],
    'cities': ['state', 'place'],
    'tracts': ['state', 'county', 'tract']
}

# Census tract names follow rules described here:
# https://www.census.gov/geo/reference/gtc/gtc_ct.html
def create_tract_name(tract):
    tract_name = str(tract).lstrip('0')
    if tract_name[-2:] == '00':
        return tract_name[:-2]
    else:
        return tract_name[:-2] + '.' + tract_name[-2:]

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
        'parent-location': lambda x: COUNTY_FIPS_MAP.get(str(x['state']).zfill(2) + str(x['county']).zfill(3), STATE_FIPS_MAP[str(x['state']).zfill(2)])
    },
    'msa': {
        'geoid': lambda x: str(x['state']).zfill(2) + str(x['metropolitan statistical area/micropolitan statistical area']).zfill(6),
        'parent-location': lambda x: STATE_FIPS_MAP[str(x['state']).zfill(2)]
    }
}

def crosswalk_county(df):
    for k, v in COUNTY_CROSSWALK.items():
        if 'name' in df.columns.values and 'parent-location' in df.columns.values:
            df.loc[df['GEOID'] == k, ['GEOID', 'name', 'parent-location']] = [v['GEOID'], v['name'], v['parent-location']]
        elif 'GEOID' in df.columns.values:
            df.loc[df['GEOID'] == k, 'GEOID'] = v['GEOID']
    return df


def clean_data_df(df, geo_str):
    if geo_str == 'cities':
        for s in REMOVE_CITY_SUFFIXES:
            df.loc[df['name'].str.endswith(s), 'name'] = df.loc[df['name'].str.endswith(s)]['name'].str.slice(0,-len(s))
            df['name'] = df['name'].str.strip()
    elif geo_str == 'tracts':
        df['name'] = df['tract'].apply(create_tract_name)
    elif geo_str == 'block-groups':
        df['name'] = df['GEOID'].apply(lambda x: create_tract_name(x[5:11]) + '.' + x[11])
    elif geo_str == 'msa':
        df = df.loc[df['name'].str.contains('Metro Area')].copy()
    else:
        df['name'] = df['name'].apply(lambda x: (str(x).split(',')[0]).lstrip('0'))
    if 'GEOID' not in df.columns.values:
        df['GEOID'] = df.apply(DATA_CLEANUP_FUNCS[geo_str]['geoid'], axis=1)
    if 'parent-location' not in df.columns.values:
        df['parent-location'] = df.apply(DATA_CLEANUP_FUNCS[geo_str]['parent-location'], axis=1)
    df_numeric = [c for c in NUMERIC_COLS if c in df.columns.values]
    df[df_numeric] = df[df_numeric].apply(pd.to_numeric)
    return df


def state_county_sub_data(census_obj, geo_str, census_vars, year):
    geo_df_list = []
    if geo_str != 'block-groups':
        fips_list = STATE_FIPS
    else:
        fips_list = STATE_COUNTY_FIPS
    if geo_str in ['tracts', 'block-groups']:
        lookup_str = geo_str.replace('-', ' ')[:-1]
    else:
        lookup_str = 'metropolitan statistical area/micropolitan statistical area'
    lookup_dict = {'for': '{}:*'.format(lookup_str)}
    for f in fips_list:
        if geo_str == 'tracts':
            lookup_dict['in'] = 'county:{} state:{}'.format(
                f.get('county', '*'), f['state']
            )
        elif geo_str == 'msa':
            lookup_dict['in'] = 'state:{}'.format(f['state'])
        elif geo_str == 'block-groups':
            lookup_dict['in'] = 'county:{} state:{}'.format(f['county'], f['state'])
        geo_df_list.append(pd.DataFrame(census_obj.get(
            census_vars, lookup_dict, year=year
        )))
    return pd.concat(geo_df_list)


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
    elif geo_str == 'counties':
        census_sf1_df = pd.DataFrame(c.sf1.get(
            CENSUS_00_SF1_VARS, {'for': 'county:*', 'in': 'state:*'}, year=2000
        ))
        census_sf3_df = pd.DataFrame(c.sf3.get(
            CENSUS_00_SF3_VARS, {'for': 'county:*', 'in': 'state:*'}, year=2000
        ))
        acs_df = pd.DataFrame(c.acs5.get(
            ACS_VARS, {'for': 'county:*', 'in': 'state:*'}, year=2009
        ))
    elif geo_str == 'cities':
        census_sf1_df = pd.DataFrame(c.sf1.get(
            CENSUS_00_SF1_VARS, {'for': 'place:*', 'in': 'state:*'}, year=2000
        ))
        census_sf3_df = pd.DataFrame(c.sf3.get(
            CENSUS_00_SF3_VARS, {'for': 'place:*', 'in': 'state:*'}, year=2000
        ))
        acs_df = pd.DataFrame(c.acs5.get(
            ACS_VARS, {'for': 'place:*', 'in': 'state:*'}, year=2009
        ))
        # Handle ACS var difference
        acs_df['NAME'] = acs_df['NAME'].apply(lambda x: ','.join(x.split(',')[:-1]).strip())
    else:
        census_sf1_df = state_county_sub_data(c.sf1, geo_str, CENSUS_00_SF1_VARS, 2000)
        census_sf3_df = state_county_sub_data(c.sf3, geo_str, CENSUS_00_SF3_VARS, 2000)
        acs_df = state_county_sub_data(c.acs5, geo_str, ACS_VARS, 2009)

    census_sf1_df.rename(columns=CENSUS_00_SF1_VAR_MAP, inplace=True)
    census_sf3_df.rename(columns=CENSUS_00_SF3_VAR_MAP, inplace=True)
    if 'name' in census_sf3_df.columns.values:
        census_sf3_df.drop('name', axis=1, inplace=True)
    
    census_sf1_df = crosswalk_county(census_sf1_df)
    census_sf3_df = crosswalk_county(census_sf3_df)
    acs_df = crosswalk_county(acs_df)

    census_df = pd.merge(census_sf1_df, census_sf3_df, how='left', on=CENSUS_JOIN_KEYS.get(geo_str))
    census_df = census_df.loc[census_df['state'] != '72'].copy()
    acs_df = acs_df.loc[acs_df['state'] != '72'].copy()
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
        # Handle ACS var difference
        acs_df['NAME'] = acs_df['NAME'].apply(lambda x: ','.join(x.split(',')[:-1]).strip())
    else:
        census_df = state_county_sub_data(c.sf1, geo_str, CENSUS_10_VARS, 2010)
        acs_12_df = state_county_sub_data(c.acs5, geo_str, ACS_12_VARS, 2012)
        acs_df = state_county_sub_data(c.acs5, geo_str, ACS_VARS, 2015)

    census_df.rename(columns=CENSUS_10_VAR_MAP, inplace=True)
    acs_12_df.rename(columns=ACS_12_VAR_MAP, inplace=True)
    if 'name' in acs_12_df.columns.values:
        acs_12_df.drop('name', axis=1, inplace=True)

    # Merge vars that are only in ACS to 2010 census
    if geo_str == 'states':
        acs_merge_keys = ['state']
    elif geo_str == 'counties':
        acs_merge_keys = ['state', 'county']
    elif geo_str == 'cities':
        acs_merge_keys = ['state', 'place']
    elif geo_str == 'tracts':
        acs_merge_keys  = ['state', 'county', 'tract']
    elif geo_str == 'msa':
        acs_merge_keys = ['state', 'metropolitan statistical area/micropolitan statistical area']
    census_df = census_df.merge(acs_12_df, on=acs_merge_keys, how='left')
    census_df = census_df.loc[census_df['state'] != '72'].copy()
    acs_df = acs_df.loc[acs_df['state'] != '72'].copy()
    acs_df.rename(columns=ACS_VAR_MAP, inplace=True)

    census_df['year'] = 2010
    acs_df_list = []
    for year in range(2011, END_YEAR):
        acs_copy = acs_df.copy()
        acs_copy['year'] = year
        acs_df_list.append(acs_copy)

    return pd.concat([census_df] + acs_df_list)


def get_block_groups_data(year_str):
    df_list = []
    df_iter = pd.read_csv(
        os.path.join(CENSUS_DIR, year_str, 'block-groups.csv'),
        dtype={'GEOID': 'object', 'state': 'object', 'county': 'object', 'tract': 'object', 'block group': 'object'},
        encoding='utf-8',
        iterator=True,
        chunksize=50000
    )
    for df in df_iter:
        df['name'] = df['tract'].apply(create_tract_name) + '.' + df['block group']
        df['parent-location'] = df.apply(DATA_CLEANUP_FUNCS[geo_str]['parent-location'], axis=1)
        df = clean_data_df(df, 'block-groups')
        df_list.append(df)
    return pd.concat(df_list)


if __name__ == '__main__':
    data_str = sys.argv[1]
    geo_str = '-'.join(data_str.split('-')[:-1])
    year_str = data_str.split('-')[-1]

    if year_str == '00':
        if geo_str == 'block-groups':
            df = get_block_groups_data(year_str)
        else:
            df = get_00_data(geo_str)
    elif year_str == '10':
        if geo_str == 'block-groups':
            df = get_block_groups_data(year_str)
        else:
            df = get_10_data(geo_str)
    else:
        raise ValueError('An invalid year suffix was supplied')

    if geo_str != 'block-groups':
        df = clean_data_df(df, geo_str)
    df.to_csv(sys.stdout, index=False, quoting=csv.QUOTE_NONNUMERIC)
