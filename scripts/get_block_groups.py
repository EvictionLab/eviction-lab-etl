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


if os.getenv('CENSUS_KEY'):
    c = Census(os.getenv('CENSUS_KEY'))
else:
    raise Exception('Environment variable CENSUS_KEY not specified')


def block_groups_00(state, county):
    res_sf1 = requests.get('{}2000/sf1?get={}&for=block group:*&in=county:{} state:{}&key={}'.format(
        CENSUS_API_BASE, ','.join(CENSUS_00_SF1_VARS), county, state, os.getenv('CENSUS_KEY')
    ))
    if res_sf1.status_code != 200:
        return
    census_sf1_json = json.loads(re.sub(r'(?<=[\w\s])"(?=[\w\s])', "'", res_sf1.text))
    census_sf1_df = pd.DataFrame([
        dict(zip(list(CENSUS_00_SF1_VARS) + ['state', 'county', 'tract', 'block group'], r)) for r in census_sf1_json[1:]
    ])
    res_sf3 = requests.get('{}2000/sf3?get={}&for=block group:*&in=county:{} state:{}&key={}'.format(
        CENSUS_API_BASE, ','.join(CENSUS_00_SF3_VARS), county, state, os.getenv('CENSUS_KEY')
    ))
    if res_sf3.status_code != 200:
        return

    census_sf3_json = json.loads(re.sub(r'(?<=[\w\s])"(?=[\w\s])', "'", res_sf3.text))
    census_sf3_df = pd.DataFrame([
        dict(zip(list(CENSUS_00_SF3_VARS) + ['state', 'county', 'tract', 'block group'], r)) for r in census_sf3_json[1:]
    ])
    acs_df = pd.DataFrame(c.acs5.get(
        ACS_VARS,
        {'for': 'block group:*', 'in': 'county: {} state:{}'.format(county, state)},
        year=2009
    ))

    census_sf1_df.rename(columns=CENSUS_00_SF1_VAR_MAP, inplace=True)
    census_sf3_df.rename(columns=CENSUS_00_SF3_VAR_MAP, inplace=True)
    census_df = pd.merge(census_sf1_df, census_sf3_df, how='left', on=['name', 'state', 'county', 'tract', 'block group'])
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

def block_groups_10(state, county):
    pass


if __name__ == '__main__':
    state, county = sys.argv[1][:2], sys.argv[1][2:]

    if sys.argv[2] == '00':
        bg_df = block_groups_00(state, county)
    elif sys.argv[2] == '10':
        bg_df = block_groups_10(state, county)
    else:
        raise ValueError('Invalid year suffix supplied')
    if bg_df is not None:
        bg_df.to_csv(sys.stdout, index=False, quoting=csv.QUOTE_NONNUMERIC)

    