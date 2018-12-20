"""
Creates demographics data pulled from the Census API for the
provided geography level and year.

Arguments
----------
argv[1] : str
    The geography level with the two-digit year code to create data for (e.g. tracts-00)

Outputs
-------
str
    a string of CSV data containing the demographics data

Example output ():


"""

import os
import sys
import csv
import time
import pandas as pd
from census_patch import CensusPatch as Census
from data_constants import NUMERIC_COLS
from utils_census import (CensusDataStore, postProcessData2000, 
                            postProcessData2010, STATE_FIPS_MAP,
                            COUNTY_FIPS_MAP, create_tract_name)


CENSUS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'census')

# List of suffixes to remove from place names
REMOVE_CITY_SUFFIXES = [
    ' town', ' city', ' CDP',
    ' municipality', ' borough', ' village',
    ' consolidated government', ' metro government', ' metropolitan government',
    ' unified governm',
]

# Cleanup functions for each geography level to ensure proper
# geoid values and parent locations.
DATA_CLEANUP_FUNCS = {
    'states': {
        'geoid': lambda x: str(x['state']).zfill(2),
        'parent-location': lambda x: 'USA'
    },
    'counties': {
        'geoid': (
            lambda x: str(x['state']).zfill(2) + str(x['county']).zfill(3)
        ),
        'parent-location': lambda x: STATE_FIPS_MAP[x['state']]
    },
    'cities': {
        'geoid': lambda x: str(x['state']).zfill(2) + str(x['place']).zfill(5),
        'parent-location': lambda x: STATE_FIPS_MAP[x['state']]
    },
    'tracts': {
        'geoid': lambda x: (
            str(x['state']).zfill(2) + str(x['county']).zfill(3) +
            str(x['tract']).zfill(6)
        ),
        'parent-location': lambda x: (
            COUNTY_FIPS_MAP.get(
                str(x['state']).zfill(2) + str(x['county']).zfill(3),
                STATE_FIPS_MAP[str(x['state']).zfill(2)]
            )
        )
    },
    'block-groups': {
        'geoid': lambda x: (
            str(x['state']).zfill(2) + str(x['county']).zfill(3) +
            str(x['tract']).zfill(6) + str(x['block group'])
        ),
        'parent-location': lambda x: (
            COUNTY_FIPS_MAP.get(
                str(x['state']).zfill(2) + str(x['county']).zfill(3),
                STATE_FIPS_MAP[str(x['state']).zfill(2)]
            )
        )
    }
}

def remove_suffix(v):
    for s in REMOVE_CITY_SUFFIXES:
        try:
            cdpPos = v.index(s)
            v = v[0:cdpPos]
        except ValueError:
            continue
    return v

# Perform some cleaning tasks on the data frame based on geography level
def clean_data_df(df, geo_str):
    if geo_str == 'cities':
        df['name'] = df['name'].apply(remove_suffix)
        df['name'] = df['name'].str.strip()
    elif geo_str == 'tracts':
        # generate proper tract name
        df['name'] = df['tract'].apply(create_tract_name)
    elif geo_str == 'block-groups':
        # generate proper block group name
        df['name'] = df['GEOID'].apply(
            lambda x: create_tract_name(x[5:11]) + '.' + x[11]
        )
    else:
        # take the first chunk before a comma, strip any leading zeros for other geography levels
        df['name'] = df['name'].apply(
            lambda x: (str(x).split(',')[0]).lstrip('0')
        )
    
    # add GEOID column if it's not already present
    if 'GEOID' not in df.columns.values:
        df['GEOID'] = df.apply(DATA_CLEANUP_FUNCS[geo_str]['geoid'], axis=1)

    # add parent-location column if it's not already present
    if 'parent-location' not in df.columns.values:
        df['parent-location'] = (
            df.apply(DATA_CLEANUP_FUNCS[geo_str]['parent-location'], axis=1)
        )
    
    # get all numeric columns in the data frame
    df_numeric = [col for col in NUMERIC_COLS if col in df.columns.values]

    # convert all numeric columns to numeric values
    df[df_numeric] = df[df_numeric].apply(pd.to_numeric)
    return df

# Fetch 2000 data from Census API
def get_00_data(c, geo_str):
    if geo_str == 'states':
        return c.fetchAllStateData2000()
    elif geo_str == 'counties':
        return c.fetchAllCountyData2000()
    elif geo_str == 'cities':
        return c.fetchAllCityData2000()
    elif geo_str == 'tracts':
        return c.fetchAllTractData2000()
    else:
        raise ValueError('Invalid geography type for 2000 data fetch.')
      
# Fetch 2010 data from Census API
def get_10_data(c, geo_str):
    if geo_str == 'states':
        return c.fetchAllStateData2010()
    elif geo_str == 'counties':
        return c.fetchAllCountyData2010()
    elif geo_str == 'cities':
        return c.fetchAllCityData2010()
    elif geo_str == 'tracts':
        return c.fetchAllTractData2010()
    else:
        raise ValueError('Invalid geography type for 2010 data fetch.')

def create_parent_name(row):
    try:
        return DATA_CLEANUP_FUNCS[geo_str]['parent-location'](row)
    except KeyError:
        print(row, file=sys.stderr)
        raise


# Load block groups data and perform cleanup
def get_block_groups_data(year_str):
    df_list = []
    df_iter = pd.read_csv(
        os.path.join(CENSUS_DIR, year_str, 'block-groups.csv'),
        dtype={
            'GEOID': 'object',
            'state': 'object',
            'county': 'object',
            'tract': 'object',
            'block group': 'object',
        },
        encoding='utf-8',
        iterator=True,
        chunksize=50000
    )
    for df in df_iter:
        df['name'] = df['tract'].apply(
            create_tract_name) + '.' + df['block group']
        df['parent-location'] = df.apply(create_parent_name, axis=1)
        df = clean_data_df(df, 'block-groups')
        df_list.append(df)
    return pd.concat(df_list)


if __name__ == '__main__':
    # first argument is {{GEO_LEVEL}}-{{2_DIGIT_YEAR}}
    data_str = sys.argv[1]
    # pull geography level from first argument
    geo_str = '-'.join(data_str.split('-')[:-1])
    # pull year from first argument
    year_str = data_str.split('-')[-1]

    c = CensusDataStore()
    
    if year_str == '00':
        if geo_str == 'block-groups':
            df = get_block_groups_data(year_str)
        else:
            df = get_00_data(c, geo_str)
    elif year_str == '10':
        if geo_str == 'block-groups':
            df = get_block_groups_data(year_str)
        else:
            df = get_10_data(c, geo_str)
    else:
        raise ValueError('An invalid year suffix was supplied')

    if geo_str != 'block-groups':
        df = clean_data_df(df, geo_str)
    df.to_csv(sys.stdout, index=False, quoting=csv.QUOTE_NONNUMERIC)
