import os
import pandas as pd
from census import Census


CENSUS_VARS = ('B01003_001E', 'B17001_002E', 'B25010_001E')
CENSUS_VARNAMES = {
    'B01003_001E': 'population',
    'B17001_002E': 'poverty-pop',
    'B25010_001E': 'average-household-size'
}

c = Census(os.getenv('CENSUS_KEY'))

def get_census_attr():
    


def state_county_fips():
    return c.acs5.get(('NAME',), {'for': 'county:*', 'in': 'state:*'})


def state_acs5_data():
    return pd.DataFrame(

    )


def state_county_sub_data(geo_str):
    state_counties = state_county_fips()
    geo_df_list = []
    for sc in state_counties:
        geo_df_list.append(pd.DataFrame(c.acs5.get(
            CENSUS_VARS,
            {'for': '{}:*'.format(geo_str),
             'in': 'county:{} state:{}'.format(sc['county'], sc['state'])}
        )))        


if __name__ == '__main__':
    pass
