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
from utils_census import create_tract_name
from data_constants import (COUNT_COLS, RATE_COLS)

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

    # merge the census data with the weights for each GEOID
    log_label = sys.argv[1]+' weights <- data'
    output_df = merge_with_stats(
        log_label, weight_df, data_df, left_on='GEOID00', right_on='GEOID', how='left')

    # create data frame with unique GEOID10 and associated name and parent-location
    context_df = output_df[['GEOID10', 'name', 'parent-location']].copy()
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
    
    # merge in the name and parent-location for all GEOIDs
    output_df = output_df.merge(context_df, on='GEOID10', how='left')
    output_df['year'] = output_df['year'].astype('int')

    # overwrite the 2000 GEOID to the 2010 GEOID
    output_df.rename(columns={'GEOID10': 'GEOID'}, inplace=True)

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
