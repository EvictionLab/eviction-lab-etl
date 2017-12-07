import os
import re
import sys
import csv
import json
import numpy as np
import pandas as pd
from census import Census
from census_data import *


if os.getenv('CENSUS_KEY'):
    c = Census(os.getenv('CENSUS_KEY'))
else:
    raise Exception('Environment variable CENSUS_KEY not specified')


def block_groups_00(state, county):
    census_sf1_df = pd.DataFrame(c.sf1.get(
        CENSUS_00_SF1_VARS, {'for': 'block group:*', 'in': 'county:{} state:{}'.format(county, state)}, year=2000
    ))
    census_sf3_df = pd.DataFrame(c.sf3.get(
        CENSUS_00_SF3_VARS, {'for': 'block group:*', 'in': 'county:{} state:{}'.format(county, state)}, year=2000
    ))
    acs_df = pd.DataFrame(c.acs5.get(
        ACS_VARS,
        {'for': 'block group:*', 'in': 'county:{} state:{}'.format(county, state)},
        year=2009
    ))

    census_sf1_df.rename(columns=CENSUS_00_SF1_VAR_MAP, inplace=True)
    census_sf3_df.rename(columns=CENSUS_00_SF3_VAR_MAP, inplace=True)

    if not len(census_sf1_df.columns.values) or not len(census_sf3_df.columns.values):
        return
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
    census_df = pd.DataFrame(c.sf1.get(
        CENSUS_10_VARS,
        {'for': 'block group:*', 'in': 'county:{} state:{}'.format(county, state)},
        year=2010
    ))
    acs_12_df = pd.DataFrame(c.acs5.get(
        ACS_12_VARS,
        {'for': 'block group:*', 'in': 'county:{} state:{}'.format(county, state)},
        year=2012
    ))
    acs_df = pd.DataFrame(c.acs5.get(
        ACS_VARS,
        {'for': 'block group:*', 'in': 'county:{} state:{}'.format(county, state)},
        year=2015
    ))

    census_df.rename(columns=CENSUS_10_VAR_MAP, inplace=True)
    acs_12_df.rename(columns=ACS_12_VAR_MAP, inplace=True)

    if len(acs_12_df.columns.values):
        # Merge vars that are only in ACS to 2010 census
        census_df = census_df.merge(acs_12_df, on=['state', 'county', 'tract', 'block group'], how='left')
    census_df['year'] = 2010

    acs_df.rename(columns=ACS_VAR_MAP, inplace=True)
    acs_df_list = []
    for year in range(2011, 2017):
        acs_copy = acs_df.copy()
        acs_copy['year'] = year
        acs_df_list.append(acs_copy)
    return pd.concat([census_df] + acs_df_list)


if __name__ == '__main__':
    state, county = sys.argv[1][:2], sys.argv[1][2:]

    if sys.argv[2] == '00':
        bg_df = block_groups_00(state, county)
    elif sys.argv[2] == '10':
        bg_df = block_groups_10(state, county)
    else:
        raise ValueError('Invalid year suffix supplied')
    if bg_df is not None:
        bg_df['GEOID'] = bg_df.apply(lambda x: str(x['state']).zfill(2) + str(x['county']).zfill(3) + str(x['tract']).zfill(6) + str(x['block group']), axis=1)
        bg_df.to_csv(sys.stdout, index=False, quoting=csv.QUOTE_NONNUMERIC)

    