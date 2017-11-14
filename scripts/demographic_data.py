import os
import sys
import csv
import pandas as pd
from census import Census


CENSUS_VARS = ('B01003_001E', 'B17001_002E', 'B25010_001E')
ACS_VARS = ('B01003_001E', 'B17001_002E', 'B25010_001E')
CENSUS_VARNAMES = {
    'B01003_001E': 'population',
    'B17001_002E': 'poverty-pop',
    'B25010_001E': 'average-household-size'
}

c = Census(os.getenv('CENSUS_KEY'))


def state_county_fips():
    return c.acs5.get(('NAME', ), {'for': 'county:*', 'in': 'state:*'})


def state_county_sub_data(census_obj, geo_str, year):
    state_counties = state_county_fips()
    geo_df_list = []
    for sc in state_counties:
        geo_df_list.append(
            pd.DataFrame(
                census_obj.get(
                    CENSUS_VARS, {
                        'for':
                        '{}:*'.format(geo_str),
                        'in':
                        'county:{} state:{}'.format(sc['county'], sc['state'])
                    },
                    year=year)))
    return pd.concat(geo_df_list)


def get_90_data(geo_str):
    if geo_str == 'states':
        census_df = pd.DataFrame(
            c.sf1.get(CENSUS_VARS, {'for': 'state:*'}, year=1990))
    elif geo_str == 'counties':
        census_df = pd.DataFrame(
            c.sf1.get(
                CENSUS_VARS, {'for': 'county:*',
                              'in': 'state:*'}, year=1990))
    else:
        census_df = state_county_sub_data(c.sf1, geo_str, 1990)

    census_df.rename(columns=CENSUS_VARNAMES, inplace=True)
    census_df_list = []
    for year in range(1990, 2000):
        census_copy = census_df.copy()
        census_copy['year'] = year
        census_df_list.append(census_copy)
    return pd.concat(census_df_list)


def get_00_data(geo_str):
    if geo_str == 'states':
        census_df = pd.DataFrame(
            c.sf1.get(CENSUS_VARS, {'for': 'state:*'}, year=2000))
        acs_df = pd.DataFrame(
            c.acs5.get(CENSUS_VARS, {'for': 'state:*'}, year=2009))
    elif geo_str == 'counties':
        census_df = pd.DataFrame(
            c.sf1.get(CENSUS_VARS, {'for': 'county:*', 'in': 'state:*'}, year=2000)
        )
        acs_df = pd.DataFrame(
            c.acs5.get(CENSUS_VARS, {'for': 'county:*', 'in': 'state:*'}, year=2009)
        )
    else:
        census_df = state_county_sub_data(c.sf1, geo_str, 2000)
        acs_df = state_county_sub_data(c.acs5, geo_str, 2009)

    census_df.rename(columns=CENSUS_VARNAMES, inplace=True)
    acs_df.rename(columns=CENSUS_VARNAMES, inplace=True)

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
        census_df = pd.DataFrame(c.sf1.get(CENSUS_VARS, {'for': 'state:*'}, year=2010))
        acs_df = pd.DataFrame(c.acs5.get(CENSUS_VARS, {'for': 'state:*'}, year=2015))
    elif geo_str == 'counties':
        census_df = pd.DataFrame(
            c.sf1.get(CENSUS_VARS, {'for': 'county:*', 'in': 'state:*'}, year=2010)
        )
        acs_df = pd.DataFrame(
            c.acs5.get(CENSUS_VARS, {'for': 'county:*', 'in': 'state:*'}, year=2015)
        )
    else:
        census_df = state_county_sub_data(c.sf1, geo_str, 2010)
        acs_df = state_county_sub_data(c.acs5, geo_str, 2015)

    census_df.rename(columns=CENSUS_VARNAMES, inplace=True)
    acs_df.rename(columns=CENSUS_VARNAMES, inplace=True)
    census_df['year'] = 2010
    acs_df_list = []
    for year in range(2011, 2017):
        acs_copy = acs_df.copy()
        acs_copy['year'] = year
        acs_df_list.append(acs_copy)

    return pd.concat([census_df] + acs_df_list)

## TODO: Add functions for each type that create the GEOID from args, drop unneeded columns


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

    data_df.to_csv(sys.stdout, index=False, quoting=csv.QUOTE_NONNUMERIC)
