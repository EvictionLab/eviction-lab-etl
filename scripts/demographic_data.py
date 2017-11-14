import os
import sys
import csv
import pandas as pd
from census import Census


ACS_VAR_MAP = {
    'NAME': 'name',
    'B01003_001E': 'population',
    'B17001_002E': 'poverty-pop',
    'B25010_001E': 'average-household-size',
    'B25111_001E': 'median-gross-rent',
    'B25001_001E': 'housing-units',
    'B25002_003E': 'vacant-housing-units',
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

CENSUS_90_VAR_MAP = {
    'ANPSADPI': 'name',
    'P0010001': 'population',
    'H0010001': 'housing-units',
    'H0030002': 'renter-occupied-housing',
    # Average household size?
    'P0080001': 'hispanic-pop',
    'P0100001': 'white-pop',
    'P0100002': 'af-am-pop',
    'P0100003': 'am-ind-pop',
    # Combines Asian and Native Hawaiian, treating as nh-pi-pop
    'P0100004': 'nh-pi-pop',
    'P0100005': 'other-pop'
}

CENSUS_00_VAR_MAP = {
    'NAME': 'name',
    'P001001': 'population',
    'H001001': 'housing-units',
    'H004003': 'renter-occupied-housing',
    'P017001': 'average-household-size',
    'P004002': 'hispanic-pop',
    'P004005': 'white-pop',
    'P004006': 'af-am-pop',
    'P004007': 'am-ind-pop',
    'P004008': 'asian-pop',
    'P004009': 'nh-pi-pop',
    'P004010': 'other-pop',
    'P004011': 'multiple-pop'
}

CENSUS_10_VAR_MAP = {
    'NAME': 'name',
    'P0030001': 'population',
    'H00010001': 'housing-units',
    'H0040004': 'renter-occupied-housing',
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

ACS_VARS = tuple(ACS_VAR_MAP.keys())
CENSUS_90_VARS = tuple(CENSUS_90_VAR_MAP.keys())
CENSUS_00_VARS = tuple(CENSUS_00_VAR_MAP.keys())
CENSUS_10_VARS = tuple(CENSUS_10_VAR_MAP.keys())

c = Census(os.getenv('CENSUS_KEY'))


STATE_FIPS = c.acs5.get(('NAME'), {'for': 'state:*'})
STATE_FIPS_MAP = {s['state']: s['NAME'] for s in STATE_FIPS}

STATE_COUNTY_FIPS = c.acs5.get(('NAME'), {'for': 'county:*', 'in': 'state:*'})
COUNTY_FIPS_MAP = {str(c['state']).zfill(2) + str(c['county']).zfill(3): c['NAME'] for c in STATE_COUNTY_FIPS}


def state_county_sub_data(census_obj, geo_str, census_vars, year):
    geo_df_list = []
    for sc in STATE_COUNTY_FIPS:
        geo_df_list.append(pd.DataFrame(census_obj.get(
            census_vars,
            {'for': '{}:*'.format(geo_str),
             'in': 'county:{} state:{}'.format(sc['county'], sc['state'])},
            year=year
        )))
    return pd.concat(geo_df_list)


def state_geoid(row):
    return str(row['state']).zfill(2)


def county_geoid(row):
    return (
        str(row['state']).zfill(2) +
        str(row['county']).zfill(3)
    )


def city_geoid(row):
    return (
        str(row['state']).zfill(2) +
        str(row['place']).zfill(5)
    )


def tract_geoid(row):
    return (
        str(row['state']).zfill(2) +
        str(row['county']).zfill(3) +
        str(row['tract']).zfill(6)
    )


def block_group_geoid(row):
    return (
        str(row['state']).zfill(2) +
        str(row['county']).zfill(3) +
        str(row['tract']).zfill(6) +
        str(row['block group'])
    )


def create_pct_cols(df):
    pass


def clean_state_df(df):
    df['GEOID'] = df.apply(state_geoid, axis=1)
    df['parent-location'] = 'USA'
    df_cols = ['GEOID'] + [c for c in df.columns.values() if c not in ['GEOID', 'state']]
    df = df[df_cols].copy()
    return df


def clean_county_df(df):
    df['GEOID'] = df.apply(county_geoid, axis=1)
    df['parent-location'] = df['state'].apply(lambda x: STATE_FIPS_MAP[x])
    df_cols = ['GEOID'] + [c for c in df.columns.values() if c not in ['GEOID', 'state', 'county']]
    df = df[df_cols].copy()
    return df


def clean_city_df(df):
    df['GEOID'] = df.apply(city_geoid, axis=1)
    df_cols = ['GEOID'] + [c for c in df.columns.values() if c not in ['GEOID', 'state', 'place']]
    df['parent-location'] = df['state'].apply(lambda x: STATE_FIPS_MAP[x])
    df = df[df_cols].copy()
    return df


def clean_tract_df(df):
    df['GEOID'] = df.apply(tract_geoid, axis=1)
    df_cols = ['GEOID'] + [c for c in df.columns.values() if c not in ['GEOID', 'state', 'county', 'tract']]
    df['parent-location'] = df.apply(lambda x: COUNTY_FIPS_MAP[str(x).zfill(2) + str(x).zfill(3)], axis=1)
    df = df[df_cols].copy()
    return df


def clean_block_group_df(df):
    df['GEOID'] = df.apply(block_group_geoid, axis=1)
    df_cols = ['GEOID'] + [c for c in df.columns.values() if c not in ['GEOID', 'state', 'county', 'tract', 'block group']]
    df['parent-location'] = df['tract'].apply(lambda x: x.zfill(6))
    df = df[df_cols].copy()
    return df


def get_90_data(geo_str):
    if geo_str == 'states':
        census_df = pd.DataFrame(c.sf1.get(
            CENSUS_90_VARS, {'for': 'state:*'}, year=1990
        ))
    elif geo_str == 'counties':
        census_df = pd.DataFrame(c.sf1.get(
            CENSUS_90_VARS, {'for': 'county:*', 'in': 'state:*'}, year=1990
        ))
    else:
        census_df = state_county_sub_data(c.sf1, geo_str, CENSUS_90_VARS, 1990)

    census_df.rename(columns=CENSUS_90_VAR_MAP, inplace=True)
    census_df_list = []
    for year in range(1990, 2000):
        census_copy = census_df.copy()
        census_copy['year'] = year
        census_df_list.append(census_copy)
    return pd.concat(census_df_list)


def get_00_data(geo_str):
    if geo_str == 'states':
        census_df = pd.DataFrame(c.sf1.get(
            CENSUS_00_VARS, {'for': 'state:*'}, year=2000
        ))
        acs_df = pd.DataFrame(c.acs5.get(
            ACS_VARS, {'for': 'state:*'}, year=2009
        ))
    elif geo_str == 'counties':
        census_df = pd.DataFrame(c.sf1.get(
            CENSUS_00_VARS, {'for': 'county:*', 'in': 'state:*'}, year=2000
        ))
        acs_df = pd.DataFrame(c.acs5.get(
            ACS_VARS, {'for': 'county:*', 'in': 'state:*'}, year=2009
        ))
    else:
        census_df = state_county_sub_data(c.sf1, geo_str, CENSUS_00_VARS, 2000)
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
        acs_df = pd.DataFrame(c.acs5.get(
            ACS_VARS, {'for': 'state:*'}, year=2015
        ))
    elif geo_str == 'counties':
        census_df = pd.DataFrame(c.sf1.get(
            CENSUS_10_VARS, {'for': 'county:*', 'in': 'state:*'}, year=2010
        ))
        acs_df = pd.DataFrame(c.acs5.get(
            ACS_VARS, {'for': 'county:*', 'in': 'state:*'}, year=2015
        ))
    else:
        census_df = state_county_sub_data(c.sf1, geo_str, CENSUS_10_VARS, 2010)
        acs_df = state_county_sub_data(c.acs5, geo_str, ACS_VARS, 2015)

    census_df.rename(columns=CENSUS_10_VAR_MAP, inplace=True)
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
        data_df = get_90_data(geo_str)
    elif year_str == '00':
        data_df = get_00_data(geo_str)
    elif year_str == '10':
        data_df = get_10_data(geo_str)
    else:
        raise ValueError('An invalid argument was supplied')

    data_df.to_csv(sys.stdout, index=False, quoting=csv.QUOTE_NONE)
