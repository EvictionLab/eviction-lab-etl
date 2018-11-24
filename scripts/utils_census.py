import os
import sys
import csv
import time
import traceback
import pandas as pd
import sys
import json
from utils_validation import (merge_with_stats)
from utils_logging import logger
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


# splits a geoid into parts (state, county, tract, block group, block)
def split_geoid(geoid):
    parts = {}
    if len(geoid) > 1:
        parts['state'] = geoid[:2]
    if len(geoid) > 4:
        parts['county'] = geoid[0:5]
    if len(geoid) > 10:
        parts['tract'] = geoid[5:11]
    if len(geoid) > 11:
        parts['bg'] = geoid[11:12]
    if len(geoid) > 12:
        parts['block'] = geoid[12:]
    return parts

# Updates the tract and block group in the census dataframe passed.
# Tracts and block groups are mapped based on columns in the map_df.
#
# - df: dataframe containing results from the Census API
# - map_df: dataframe containing two columns with a mapping of
#       source block group to target block group
# - fromField: the column name that contains the source block group ids
# - toField: the column name that contains the target block group ids 
def changeBlockGroupsInCensusData(df, map_df, fromField, toField):
    # get a map of columns `fromField` : `toField`
    bg_dict = pd.Series(map_df[toField].values, index=map_df[fromField]).to_dict()
    # loop through the map and update the data frame if needed
    for fromBg, toBg in bg_dict.items():
        from_parts = split_geoid(fromBg) 
        to_parts = split_geoid(toBg)
        # update the data frame where conditions are met
        df.loc[
            (df['tract'] == from_parts['tract']) & (df['block group'] == from_parts['bg']), 
            ['county', 'tract', 'block group']] = [ to_parts['county'], to_parts['tract'], to_parts['bg'] ]

    return df

# Loads a block group crosswalk file from the `conf` directory and 
# removes any rows that should not be compared
def get_block_group_crosswalk_df(filename):
    conf_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'conf')
    cw_df = pd.read_csv(
        os.path.join(conf_dir, filename),
        dtype={
                'cofips': 'object',
                'bkg09': 'object',
                'bkg10': 'object'
            }
    )
    # filter out entries where values should not be copied
    if 'nocompare' in cw_df.columns:
        cw_df = cw_df.loc[cw_df['nocompare'] == 0]
    return cw_df

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

    if not sf1_df.empty and not acs12_df.empty:
        # Merge vars that are only in ACS to 2010 census
        log_label = '2010 ' + geo_str + ' sf1_df <- acs12_df'
        sf1_df = merge_with_stats(log_label, sf1_df, acs12_df, on=CENSUS_JOIN_KEYS.get(geo_str), how='left')

    if not sf1_df.empty:
        sf1_df = sf1_df.loc[sf1_df['state'] != '72'].copy()
        sf1_df['year'] = 2010
    
    if not acs_df.empty:
        acs_df = acs_df.loc[acs_df['state'] != '72'].copy()

    acs_df.rename(columns=ACS_VAR_MAP, inplace=True)
    acs_df_list = addDataFrameYears(acs_df, 2011, END_YEAR)

    return pd.concat([sf1_df] + acs_df_list)

class CensusDataStore:
    def __init__(self):
        self.crosswalks = {
            'acs_09_00': get_block_group_crosswalk_df('changes_09acs_to_00cen.csv'),
            'acs_09_10': get_block_group_crosswalk_df('changes_09acs_to_10cen.csv')
        }

    # Get the crosswalk for a specific county
    def getCountyBlockGroupCrosswalk(self, cw_name, county):
        cw_df = self.crosswalks[cw_name]
        return cw_df.loc[cw_df['cofips'] == county]

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
                exctype, value = sys.exc_info()[:2]
                logger.info('received ' + str(exctype) + ' fetching ' + str(year) + ' ' + source + ' data ' + str(lookup_dict) + ', will retry shortly')
                logger.debug(value)
                time.sleep(180)
            else:
                break
        else: 
            # could not retrieve data after 10 attempts (20 min)
            logger.error("could not retrieve " + str(year) + " " + source + " data for: " + json.dumps(lookup_dict))
            return None

    # Returns a dataframe with the results or empty dataframe if error
    def fetchData(self, source, items, lookup_dict, year):
        results_df = pd.DataFrame(self.fetchResults(source, items, lookup_dict, year=year))
        if results_df.empty:
            logger.info('received empty result for query: ' + str(year) + ' ' + source + ' data ' + str(lookup_dict))
        return results_df

    # Fetch data for all states in the US
    def fetchStates(self, source, items, year):
        lookup_dict = { 'for': 'state:*' }
        return self.fetchData(source, items, lookup_dict, year)

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

    # Fetch data for all counties in the US
    def fetchCounties(self, source, items, year):
        lookup_dict = { 'for': 'county:*', 'in': 'state:*' }
        return self.fetchData(source, items, lookup_dict, year)

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

    # Fetch data for all cities in the US
    def fetchCities(self, source, items, year):
        lookup_dict = { 'for': 'place:*', 'in': 'state:*' }
        return self.fetchData(source, items, lookup_dict , year)

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

    # Fetch data for tracts within a given county
    def fetchTractsByCounty(self, source, items, county, year):
        parent  = 'county:{} state:{}'.format(county[2:], county[0:2])
        lookup_dict = { 'for': 'tract:*', 'in': parent }
        return self.fetchData(source, items, lookup_dict, year)

    # Fetch data for all tracts in the US by looping through counties and fetching
    # tracts for each
    def fetchTracts(self, source, items, year):
        geo_df_list = []
        fips_list = STATE_COUNTY_FIPS
        for f in fips_list:
            county = f['state'] + f['county']
            geo_df_list.append(self.fetchTractsByCounty(source, items, county, year))
        return pd.concat(geo_df_list)

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

    # Fetch data for block groups within a given tract
    def fetchBlockGroupsByTract(self, source, items, tract, year):
        parent  = 'county:{} state:{} tract:{}'.format(tract[2:5], tract[0:2], tract[5:])
        lookup_dict = { 'for': 'block group:*', 'in': parent }
        return self.fetchData(source, items, lookup_dict, year)

    def getTractsList(self, county):
        lookup_dict =  {
            'for': 'tract:*', 
            'in': 'county:' + county[2:] + ' state:' + county[0:2] 
        }
        tract_fips = [ (r['state'] + r['county'] + r['tract']) for r in self.fetchResults('acs5', ('NAME'), lookup_dict) ]


    # Fetch data for all 2010 block groups in a county by fetching all of
    # the tracts within a county, and then looping through those tracts.
    def fetchBlockGroupsByCounty(self, source, items, county, year):
        geo_df_list = []
        lookup_dict =  {
            'for': 'tract:*', 
            'in': 'county:' + county[2:] + ' state:' + county[0:2] 
        }
        # NOTE: need to double check this is an appropriate way to get all of the tracts in
        #   a county.  It is querying ACS5, but does that have all of the tracts in
        #   SF1, SF3, and ACS?
        tract_fips = [ r for r in self.fetchResults(source, ('NAME'), lookup_dict, year=year) ]
        for f in tract_fips:
            tract = f['state'] + f['county'] + f['tract']
            geo_df_list.append(self.fetchBlockGroupsByTract(source, items, tract, year))

        if len(geo_df_list) > 0:
            return pd.concat(geo_df_list)
        return pd.DataFrame()

    def fetchAllBlockGroupData2000(self, county):
        logger.debug('starting fetch block group level data for 2000-2009')
        census_sf1_df = self.fetchBlockGroupsByCounty('sf1', CENSUS_00_SF1_VARS, county, 2000)
        census_sf3_df = self.fetchBlockGroupsByCounty('sf3', CENSUS_00_SF3_VARS, county, 2000)
        acs_df = self.fetchBlockGroupsByCounty('acs5', ACS_VARS, county, 2009)
        # translate ACS 2009 -> 2000 block groups if needed
        # NOTE: Some entries are also translate from ACS 2009 -> 2010, this happens when
        # `convert_00_geo.py` is run using the a weight of 1
        acs_09_00_cw_df = self.getCountyBlockGroupCrosswalk('acs_09_00', county)
        if not acs_09_00_cw_df.empty:
            acs_df = changeBlockGroupsInCensusData(acs_df, acs_09_00_cw_df, 'bg09', 'bg00')
        return postProcessData2000(census_sf1_df, census_sf3_df, acs_df, 'block-groups')
    
    def fetchAllBlockGroupData2010(self, county):
        logger.debug('starting fetch block group level data for 2010-current')
        census_df = self.fetchBlockGroupsByCounty('sf1', CENSUS_10_VARS, county, 2010)
        acs_12_df = self.fetchBlockGroupsByCounty('acs5', ACS_12_VARS, county, 2012)
        acs_df = self.fetchBlockGroupsByCounty('acs5', ACS_VARS, county, 2015)
        return postProcessData2010(census_df, acs_12_df, acs_df, 'block-groups')
