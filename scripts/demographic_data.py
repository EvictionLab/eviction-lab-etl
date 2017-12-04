import os
import re
import sys
import csv
import json
import numpy as np
import pandas as pd
from census import Census
from census_data import *

c = Census(os.getenv('CENSUS_KEY'))

END_YEAR = 2017

CENSUS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'census')

STATE_FIPS = c.acs5.get(('NAME'), {'for': 'state:*'})
STATE_FIPS_MAP = {s['state']: s['NAME'] for s in STATE_FIPS}

STATE_COUNTY_FIPS = c.acs5.get(('NAME'), {'for': 'county:*', 'in': 'state:*'})
COUNTY_FIPS_MAP = {str(c['state']).zfill(2) + str(c['county']).zfill(3): c['NAME'] for c in STATE_COUNTY_FIPS}

REMOVE_CITY_SUFFIXES = ['town', 'city', 'CDP', 'municipality', 'borough', '(balance)', 'village']

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


def generated_cols(df):
    if 'occupied-housing-units' in df.columns.values:
        df['pct-renter-occupied'] = np.where(df['occupied-housing-units'] > 0, (df['renter-occupied-households'] / df['occupied-housing-units']) * 100, 0)
    else:
        df['pct-renter-occupied'] = np.nan
    if 'poverty-pop' in df.columns.values:
        df[['population', 'poverty-pop']] = df[['population', 'poverty-pop']].apply(pd.to_numeric)
        pop_col = 'population'
        if 'total-poverty-pop' in df.columns.values:
            pop_col = 'total-poverty-pop'
            df[[pop_col]] = df[[pop_col]].apply(pd.to_numeric)
        df['poverty-rate'] = np.where(df[pop_col] > 0, (df['poverty-pop'] / df[pop_col]) * 100, 0)
    else:
        # Should nulls be handled this way here?
        df['poverty-rate'] = np.nan
    for dem in ['hispanic', 'white', 'af-am', 'am-ind', 'asian', 'nh-pi', 'other', 'multiple']:
        if dem + '-pop' in df.columns.values:
            df[[dem + '-pop']] = df[[dem + '-pop']].apply(pd.to_numeric)
            df['pct-{}'.format(dem)] = np.where(df['population'] > 0, (df['{}-pop'.format(dem)] / df['population']) * 100, 0)
    return df


def clean_data_df(df, geo_str):
    if geo_str == 'cities':
        for s in REMOVE_CITY_SUFFIXES:
            df['name'] = df['name'].str.rstrip(s)
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
    df = generated_cols(df)
    for col in OUTPUT_COLS:
        if col not in df.columns.values:
            df[col] = np.nan
    return df[OUTPUT_COLS].copy()


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
        df['parent-location'] = df['tract'].apply(create_tract_name)
        df_numeric = [c for c in NUMERIC_COLS if c in df.columns.values]
        df[df_numeric] = df[df_numeric].apply(pd.to_numeric)
        df = generated_cols(df)
        for col in OUTPUT_COLS:
            if col not in df.columns.values:
                df[col] = np.nan
        df_list.append(df[OUTPUT_COLS])
    return pd.concat(df_list)


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

    acs_df.rename(columns=ACS_VAR_MAP, inplace=True)

    census_df['year'] = 2010
    acs_df_list = []
    for year in range(2011, END_YEAR):
        acs_copy = acs_df.copy()
        acs_copy['year'] = year
        acs_df_list.append(acs_copy)

    return pd.concat([census_df] + acs_df_list)


if __name__ == '__main__':
    data_str = sys.argv[1]
    geo_str = '-'.join(data_str.split('-')[:-1])
    year_str = data_str.split('-')[-1]

    if year_str == '00':
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

    if not (geo_str == 'block-groups' and year_str in ['00', '10']):
        data_df = clean_data_df(data_df, geo_str).round(2)
    data_df.to_csv(sys.stdout, index=False, quoting=csv.QUOTE_NONNUMERIC)
