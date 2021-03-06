"""
Maps 2000 data to 2010 geography

Input
------
Takes the stdout of `fetch_raw_census_data.py` as stdin

Arguments
----------
argv[1] : str
    The geography level to create weights for (block-groups or tracts)
argv[2] : str
    The file path to the file that contains the crosswalk and weights for
    converting 2000 data to 2010 geography

Outputs
-------
str
    a string of CSV data containing all of the 2000 census data
    crosswalked so it fits in 2010 geography

"""

import sys
import csv
import pandas as pd
from utils_validation import (merge_with_stats, logger)
from utils_census import (create_tract_name, get_block_group_crosswalk_df,
                        get_tract_crosswalk_09_10_df)
from data_constants import (COUNT_COLS, RATE_COLS)

def changeACS09toCensus10(df, map_df, fromField, toField):
    # get a map of columns `fromField` : `toField`
    bg_dict = pd.Series(map_df[toField].values, index=map_df[fromField]).to_dict()

    # loop through the map and update the data frame if needed
    for fromBg, toBg in bg_dict.items():
        df.loc[(df['GEOID'] == fromBg), 'GEOID'] = toBg
    return df

if __name__ == '__main__':
    # read output from `fetch_raw_census_data.py` into data frame
    data_df = pd.read_csv(
        sys.stdin,
        dtype={
            'GEOID': 'object',
            'name': 'object',
            'parent-location': 'object'
        })
    # read in weights output from `create_00_weights.py`
    weight_df = pd.read_csv(
        sys.argv[2], dtype={
            'GEOID00': 'object',
            'GEOID10': 'object'
        })

    # add ACS 09 -> 10 rows to weights dataframe with weight of 1
    if sys.argv[1] == 'block-groups':
        acs_09_10_cw_df = get_block_group_crosswalk_df('changes_09acs_to_10cen.csv')
        acs_09_10_cw_df.drop(['county', 'cofips'], axis=1, inplace=True)
        acs_09_10_cw_df.rename(columns={
            'bkg09': 'GEOID09',
            'bkg10': 'GEOID10'
        }, inplace=True)
    if sys.argv[1] == 'tracts':
        acs_09_10_cw_df = get_tract_crosswalk_09_10_df()
        acs_09_10_cw_df.rename(columns={
            'trt09': 'GEOID09',
            'trt10': 'GEOID10'
        }, inplace=True)

    # remove the rows from ACS 2009 that are already in 2010 geography
    # because they are not part of the crosswalk
    entries = acs_09_10_cw_df['GEOID09'].tolist()
    acs_10_entries_df = data_df[
        data_df['GEOID'].isin(entries) & data_df['year'].isin([2005,2006,2007,2008,2009])].copy()
    acs_10_entries_df.drop(['name', 'parent-location'], axis=1, inplace=True)
    cw_df = data_df.drop(data_df[
        data_df['GEOID'].isin(entries) & data_df['year'].isin([2005,2006,2007,2008,2009])].index)
    del data_df


    # merge the census data with the weights for each GEOID
    log_label = sys.argv[1]+' weights <- data'
    output_df = merge_with_stats(
        log_label, weight_df, cw_df, left_on='GEOID00', right_on='GEOID', how='left')
    del weight_df

    # create data frame with unique GEOID10 and associated name and parent-location
    context_df = output_df[['GEOID00', 'GEOID10', 'name', 'parent-location']].copy()
    # drop rows where GEOID00 county != GEOID10 county
    context_df.drop(
        context_df[context_df['GEOID00'].str[:5] != context_df['GEOID10'].str[:5]].index, inplace=True)
    context_df.drop(['GEOID00'], axis=1, inplace=True)
    context_df.drop_duplicates(subset=['GEOID10'], inplace=True)

    # multiply all count columns by the count weight
    output_df[COUNT_COLS] = output_df[COUNT_COLS].multiply(
        output_df['count_weight'], axis=0)

    # multiply all rate columns by rate weight
    output_df[RATE_COLS] = output_df[RATE_COLS].multiply(
        output_df['rate_weight'], axis=0)

    # sum all values together based on the 2010 geography identifier
    output_df = pd.DataFrame(
        output_df.groupby(['GEOID10',
                           'year'])[COUNT_COLS + RATE_COLS].sum()).reset_index()

    # overwrite the 2000 GEOID to the 2010 GEOID
    output_df.rename(columns={'GEOID10': 'GEOID'}, inplace=True)

    # apply ACS 2009 -> Census 2010 changes, then concat result to the data
    acs_10_entries_df = changeACS09toCensus10(acs_10_entries_df, acs_09_10_cw_df, 'GEOID09', 'GEOID10')
    output_df = pd.concat([acs_10_entries_df, output_df])

    # merge in the name and parent-location for all GEOIDs
    output_df = merge_with_stats(
        'context', output_df, context_df, left_on='GEOID', right_on='GEOID10', how='left')
    output_df['year'] = output_df['year'].astype('int')

    # create the name attribute for tracts and block groups
    if sys.argv[1] == 'tracts':
        output_df['name'] = output_df['GEOID'].str.slice(5).apply(
            create_tract_name)
    elif sys.argv[1] == 'block-groups':
        output_df['name'] = output_df['GEOID'].str.slice(5, -1).apply(
            create_tract_name) + '.' + output_df['GEOID'].str.slice(-1)
    else:
        raise ValueError('Invalid geography string supplied')

    # output to stdout
    output_df.to_csv(sys.stdout, index=False, quoting=csv.QUOTE_NONNUMERIC)
