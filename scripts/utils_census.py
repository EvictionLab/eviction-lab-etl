import os
import sys
import csv
import time
import traceback
import pandas as pd
import sys
import json
from utils_validation import (merge_with_stats)
from utils_logging import create_logger
from census_patch import CensusPatch as Census
from data_constants import (COUNTY_CROSSWALK,
                            CENSUS_00_SF1_VARS, CENSUS_00_SF1_VAR_MAP,
                            CENSUS_00_SF3_VARS, CENSUS_00_SF3_VAR_MAP,
                            CENSUS_10_VARS, CENSUS_10_VAR_MAP, ACS_VARS,
                            ACS_VAR_MAP, ACS_12_VARS, ACS_12_VAR_MAP, END_YEAR)

if os.getenv('CENSUS_KEY'):
    c = Census(os.getenv('CENSUS_KEY'))
else:
    raise Exception('Environment variable CENSUS_KEY not specified')

# create a logger to log fetches to the console
logger = create_logger('census_fetch')

# all state names (except Puerto Rico)
STATE_FIPS = [
    r for r in c.acs5.get(('NAME'), {'for': 'state:*'}) if r['state'] != '72'
]
# map from state FIPS code to state name
STATE_FIPS_MAP = {s['state']: s['NAME'] for s in STATE_FIPS}

# all county names in the US (except Puerto Rico)
STATE_COUNTY_FIPS = [
    r for r in c.acs5.get(('NAME'), {'for': 'county:*', 'in': 'state:*'})
    if r['state'] != '72'
]
# map from county fips code to county name
COUNTY_FIPS_MAP = {
    str(r['state']).zfill(2) + str(r['county']).zfill(3): r['NAME']
    for r in STATE_COUNTY_FIPS
}

# Map of geography level to column names to user for join
CENSUS_JOIN_KEYS = {
    'states': ['state'],
    'counties': ['state', 'county'],
    'cities': ['state', 'place'],
    'tracts': ['state', 'county', 'tract'],
    'block-groups': ['state', 'county', 'tract', 'block group'],
}

# Census tract names follow rules described here:
# https://www.census.gov/geo/reference/gtc/gtc_ct.html
def create_tract_name(tract):
    tract_name = str(tract).lstrip('0')
    if tract_name[-2:] == '00':
        return tract_name[:-2]
    else:
        return tract_name[:-2] + '.' + tract_name[-2:]

# Checks the data frame for any GEOIDs in the COUNTY_CROSSWALK data constant
# If there are matches, update the GEOID, name, parent-location with the
# mapped values.
def crosswalk_county(df):
    for k, v in COUNTY_CROSSWALK.items():
        if (
            'name' in df.columns.values and
            'parent-location' in df.columns.values
        ):
            df.loc[df['GEOID'] == k, ['GEOID', 'name', 'parent-location']] = (
                [v['GEOID'], v['name'], v['parent-location']]
            )
        elif 'GEOID' in df.columns.values:
            df.loc[df['GEOID'] == k, 'GEOID'] = v['GEOID']
    return df

# Add years column to data frame
def addDataFrameYears(df, start, end):
    df_list = []
    for year in range(start, end):
        df_copy = df.copy()
        df_copy['year'] = year
        df_list.append(df_copy)
    return df_list

# Handles merging and processing data fetched from the census API
# for the years 2000-2010
def postProcessData2000(sf1_df, sf3_df, acs_df, geo_str):
    sf1_df.rename(columns=CENSUS_00_SF1_VAR_MAP, inplace=True)
    sf3_df.rename(columns=CENSUS_00_SF3_VAR_MAP, inplace=True)
    if 'name' in sf3_df.columns.values:
        sf3_df.drop('name', axis=1, inplace=True)

    # exit function if there are is no data
    early_exit = False
    if not len(sf1_df.columns.values):
        logger.warn('no data from sf1 query')
        early_exit = True
    if not len(sf3_df.columns.values):
        logger.warn('no data from sf3 query')
        early_exit = True
    if early_exit:
        return

    # update with county crosswalk data if needed
    sf1_df = crosswalk_county(sf1_df)
    sf3_df = crosswalk_county(sf3_df)
    acs_df = crosswalk_county(acs_df)

    # merge sf3 results into sf1 results
    log_label = '2000 ' + geo_str + ' sf1 <- sf3'
    census_df = merge_with_stats(log_label, sf1_df, sf3_df, on=CENSUS_JOIN_KEYS.get(geo_str), how='left')
    # drop Puerto Rico
    if geo_str != 'block-groups': 
        census_df = census_df.loc[census_df['state'] != '72'].copy()
        acs_df = acs_df.loc[acs_df['state'] != '72'].copy()
    acs_df.rename(columns=ACS_VAR_MAP, inplace=True)

    census_df_list = addDataFrameYears(census_df, 2000, 2005)
    acs_df_list = addDataFrameYears(acs_df, 2005, 2010)
    return pd.concat(census_df_list + acs_df_list)

# Handles merging and processing data fetched from the census API
# for the years 2010-current
def postProcessData2010(sf1_df, acs12_df, acs_df, geo_str):
    sf1_df.rename(columns=CENSUS_10_VAR_MAP, inplace=True)
    acs12_df.rename(columns=ACS_12_VAR_MAP, inplace=True)
    if 'name' in acs12_df.columns.values:
        acs12_df.drop('name', axis=1, inplace=True)

    # Merge vars that are only in ACS to 2010 census
    log_label = '2010 ' + geo_str + ' sf1_df <- acs12_df'
    sf1_df = merge_with_stats(log_label, sf1_df, acs12_df, on=CENSUS_JOIN_KEYS.get(geo_str), how='left')

    sf1_df = sf1_df.loc[sf1_df['state'] != '72'].copy()
    acs_df = acs_df.loc[acs_df['state'] != '72'].copy()
    acs_df.rename(columns=ACS_VAR_MAP, inplace=True)

    sf1_df['year'] = 2010
    acs_df_list = addDataFrameYears(acs_df, 2011, END_YEAR)

    return pd.concat([sf1_df] + acs_df_list)

class CensusDataStore:
    def __init__(self):
        self.key = os.getenv('CENSUS_KEY')

    # Fetches results from the provided Census API source
    def fetchResults(self, source, items, lookup_dict, year=None):
        for attempt in range(10):
            try:
                logger.debug('fetching ' + (str(year) if year else '') + ' ' + source + ' data ' + str(lookup_dict))
                if year:
                    return getattr(c, source).get(items, lookup_dict, year=year)
                else:
                    return getattr(c, source).get(items, lookup_dict)
            except:
                logger.warn(traceback.format_exc())
                logger.warn('received error fetching ' + str(year) + ' ' + source + ' data ' + str(lookup_dict) + ', will retry in two minutes')
                time.sleep(120)
            else:
                break
        else: 
            # could not retrieve data after 10 attempts (20 min)
            logger.error("could not retrieve " + year + " " + source + " data for: " + json.dumps(lookup_dict))
            return None

    # Returns a dataframe with the results or empty dataframe if error
    def fetchData(self, source, items, lookup_dict, year):
        return pd.DataFrame(self.fetchResults(source, items, lookup_dict, year=year))

    # Fetch data for block groups within a given tract
    def fetchBlockGroupsByTract(self, source, items, tract, year):
        parent  = 'county:{} state:{} tract:{}'.format(tract[2:5], tract[0:2], tract[5:])
        lookup_dict = { 'for': 'block group:*', 'in': parent }
        return self.fetchData(source, items, lookup_dict, year)

    # Fetch data for tracts within a given county
    def fetchTractsByCounty(self, source, items, county, year):
        parent  = 'county:{} state:{}'.format(county[2:], county[0:2])
        lookup_dict = { 'for': 'tract:*', 'in': parent }
        return self.fetchData(source, items, lookup_dict, year)

    # Fetch data for all states in the US
    def fetchStates(self, source, items, year):
        lookup_dict = { 'for': 'state:*' }
        return self.fetchData(source, items, lookup_dict, year)

    # Fetch data for all counties in the US
    def fetchCounties(self, source, items, year):
        lookup_dict = { 'for': 'county:*', 'in': 'state:*' }
        return self.fetchData(source, items, lookup_dict, year)

    # Fetch data for all cities in the US
    def fetchCities(self, source, items, year):
        lookup_dict = { 'for': 'place:*', 'in': 'state:*' }
        return self.fetchData(source, items, lookup_dict , year)

    # Fetch data for all tracts in the US
    def fetchTracts(self, source, items, year):
        geo_df_list = []
        fips_list = STATE_COUNTY_FIPS
        for f in fips_list:
            county = f['state'] + f['county']
            geo_df_list.append(self.fetchTractsByCounty(source, items, county, year))
        return pd.concat(geo_df_list)

    # Fetch data for block groups within a given county
    def fetchBlockGroupsByCounty(self, source, items, county, year):
        parent  = 'county:{} state:{}'.format(county[2:], county[0:2])
        lookup_dict = { 'for': 'block group:*', 'in': parent }
        return self.fetchData(source, items, lookup_dict, year)

    # Fetch data for all 2010 block groups in a county
    # The 2010 queries require tract to be specified, where 2000 queries do not
    def fetchBlockGroupsByCounty10(self, source, items, county, year):
        geo_df_list = []
        lookup_dict =  {
            'for': 'tract:*', 
            'in': 'county:' + county[2:] + ' state:' + county[0:2] 
        }
        tract_fips = [ r for r in self.fetchResults('acs5', ('NAME'), lookup_dict) ]
        for f in tract_fips:
            tract = f['state'] + f['county'] + f['tract']
            geo_df_list.append(self.fetchBlockGroupsByTract(source, items, tract, year))

        return pd.concat(geo_df_list)

    # Fetches data for all states for 2000-2009
    def fetchAllStateData2000(self):
        logger.debug('starting fetch for all state level data for 2000-2009')
        census_sf1_df = self.fetchStates('sf1', CENSUS_00_SF1_VARS, 2000)
        census_sf3_df = self.fetchStates('sf3', CENSUS_00_SF3_VARS, 2000)
        acs_df = self.fetchStates('acs5', ACS_VARS, 2009)
        return postProcessData2000(census_sf1_df, census_sf3_df, acs_df, 'states')

    # Fetches data for all states for 2010-current
    def fetchAllStateData2010(self):
        logger.debug('starting fetch for all state level data for 2010-current')
        census_df = self.fetchStates('sf1', CENSUS_10_VARS, 2010)
        acs_12_df = self.fetchStates('acs5', ACS_12_VARS, 2012)
        acs_df = self.fetchStates('acs5', ACS_VARS, 2015)
        return postProcessData2010(census_df, acs_12_df, acs_df, 'states')

    # Fetches data for all counties for 2000-2009
    def fetchAllCountyData2000(self):
        logger.debug('starting fetch for all county level data for 2000-2009')
        census_sf1_df = self.fetchCounties('sf1', CENSUS_00_SF1_VARS, 2000)
        census_sf3_df = self.fetchCounties('sf3', CENSUS_00_SF3_VARS, 2000)
        acs_df = self.fetchCounties('acs5', ACS_VARS, 2009)
        return postProcessData2000(census_sf1_df, census_sf3_df, acs_df, 'counties')

    # Fetches data for all counties for 2010-current
    def fetchAllCountyData2010(self):
        logger.debug('starting fetch for all county level data for 2010-current')
        census_df = self.fetchCounties('sf1', CENSUS_10_VARS, 2010)
        acs_12_df = self.fetchCounties('acs5', ACS_12_VARS, 2012)
        acs_df = self.fetchCounties('acs5', ACS_VARS, 2015)
        return postProcessData2010(census_df, acs_12_df, acs_df, 'counties')

    def fetchAllCityData2000(self):
        logger.debug('starting fetch for all city level data for 2000-2009')
        census_sf1_df = self.fetchCities('sf1', CENSUS_00_SF1_VARS, 2000)
        census_sf3_df = self.fetchCities('sf3', CENSUS_00_SF3_VARS, 2000)
        acs_df = self.fetchCities('acs5', ACS_VARS, 2009)
        # Handle ACS var difference
        acs_df['NAME'] = acs_df['NAME'].apply(
            lambda x: ','.join(x.split(',')[:-1]).strip()
        )
        return postProcessData2000(census_sf1_df, census_sf3_df, acs_df, 'cities')

    def fetchAllCityData2010(self):
        logger.debug('starting fetch for all city level data for 2010-current')
        census_df = self.fetchCities('sf1', CENSUS_10_VARS, 2010)
        acs_12_df = self.fetchCities('acs5', ACS_12_VARS, 2012)
        acs_df = self.fetchCities('acs5', ACS_VARS, 2015)
        # Handle ACS var difference
        acs_df['NAME'] = acs_df['NAME'].apply(
            lambda x: ','.join(x.split(',')[:-1]).strip()
        )
        return postProcessData2010(census_df, acs_12_df, acs_df, 'cities')

    def fetchAllTractData2000(self):
        logger.debug('starting fetch for all tract level data for 2000-2009')
        census_sf1_df = self.fetchTracts('sf1', CENSUS_00_SF1_VARS, 2000)
        census_sf3_df = self.fetchTracts('sf3', CENSUS_00_SF3_VARS, 2000)
        acs_df = self.fetchTracts('acs5', ACS_VARS, 2009)
        return postProcessData2000(census_sf1_df, census_sf3_df, acs_df, 'tracts')

    def fetchAllTractData2010(self):
        logger.debug('starting fetch for all tract level data for 2010-current')
        census_df = self.fetchTracts('sf1', CENSUS_10_VARS, 2010)
        acs_12_df = self.fetchTracts('acs5', ACS_12_VARS, 2012)
        acs_df = self.fetchTracts('acs5', ACS_VARS, 2015)
        return postProcessData2010(census_df, acs_12_df, acs_df, 'tracts')

    def fetchAllBlockGroupData2000(self, county):
        logger.debug('starting fetch block group level data for 2000-2009')
        # fetch the data
        census_sf1_df = self.fetchBlockGroupsByCounty('sf1', CENSUS_00_SF1_VARS, county, 2000)
        census_sf3_df = self.fetchBlockGroupsByCounty('sf3', CENSUS_00_SF3_VARS, county, 2000)
        acs_df = self.fetchBlockGroupsByCounty('acs5', ACS_VARS, county, 2009)
        return postProcessData2000(census_sf1_df, census_sf3_df, acs_df, 'block-groups')
    
    def fetchAllBlockGroupData2010(self, county):
        logger.debug('starting fetch block group level data for 2010-current')
        # fetch the data
        census_df = self.fetchBlockGroupsByCounty10('sf1', CENSUS_10_VARS, county, 2010)
        acs_12_df = self.fetchBlockGroupsByCounty10('acs5', ACS_12_VARS, county, 2012)
        acs_df = self.fetchBlockGroupsByCounty10('acs5', ACS_VARS, county, 2015)
        return postProcessData2010(census_df, acs_12_df, acs_df, 'block-groups')
