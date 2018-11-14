"""
Links the census data files with the allocation factors file and the
2000 to 2010 blocks crosswalk.

Arguments
----------
argv[1] : str
    The geography level to create weights for (block-groups or tracts)
argv[2] : str
    The file path to the file with allocations
argv[3] : str
    The file path to the 2000 blocks to 2010 blocks crosswalk, retrieved from 
    https://www.nhgis.org/user-resources/geographic-crosswalks

Outputs
-------
str
    a string of CSV data containing the block GEOIDs for 2000, 2010, 
    allocation factors, and weights

Example output:
GEOID00,afact_2000,GEOID10,weight_2010
010010201001000,0.01346801346801347,010010201002000,0.0004900677979520337
010010201001000,0.01346801346801347,010010201002001,0.003458433632908435
010010201001000,0.01346801346801347,010010201002002,0.0
010010201001000,0.01346801346801347,010010201002003,0.0010415987884761476
010010201001000,0.01346801346801347,010010201002004,0.00044288226602458134
010010201001000,0.01346801346801347,010010201002005,0.005616460572850339
010010201001000,0.01346801346801347,010010201002006,0.00027179928356164094
010010201001000,0.01346801346801347,010010201002007,0.0013548291912375667

"""

import sys
import numpy as np
import pandas as pd
from utils_validation import (merge_with_stats)

if __name__ == '__main__':

    # set the target geography level (tracts or block-groups)
    geo_level = sys.argv[1]
    # load provided csv files into dataframes
    allocation_df = pd.read_csv(
        sys.argv[2],
        dtype={
            'GEOID': 'object',
            'GEOID00': 'object',
            'county': 'object',
            'tract': 'object',
            'bg': 'object',
            'block': 'object',
            'pop2k': 'float64',
            'allocation': 'float64'
        })
    crosswalk_df = pd.read_csv(
        sys.argv[3], dtype={
            'GEOID00': 'object',
            'GEOID10': 'object'
        })


    # STEP 1:
    # Merge the allocations into the crosswalk to get 2010 GEOID (GEOID10) 
    log_label = 'mcdc_geocorr_pop2k <- nhgis_crosswalk'
    output_df = merge_with_stats(allocation_df, crosswalk_df, 'GEOID00', 'left', log_label)
    output_df.fillna(0, inplace=True)

    # add 2010 block and block group from crosswalk GEOID
    output_df['block_2010'] = output_df['GEOID10'].str.slice(11)
    output_df['bg_2010'] = output_df['GEOID10'].str.slice(11, 12)

    # rename 2000 columns for clarity
    output_df.rename(
        columns={
            'tract': 'tract_2000',
            'bg': 'bg_2000',
            'block': 'block_2000',
            'allocation': 'afact_2000'
        }, inplace=True)


    # STEP 2:
    # Create 2010 population for the given geo level
    output_df['pop_2010'] = output_df['pop2k'] * output_df['WEIGHT']

    # Create GEOID for the provided geography level (tracts or block groups)
    if geo_level == 'tracts':
        output_df['SUMID'] = output_df['GEOID10'].str.slice(0, 11)
    elif geo_level == 'block-groups':
        output_df['SUMID'] = output_df['GEOID10'].str.slice(0, 12)
    else:
        raise ValueError('Invalid geography string supplied')


    # STEP 3:
    # Calculate 2010 block weight by dividing 2010 block population
    # by the total population for the current geography

    # create dataframe containing total population for the provided geography level
    total_pop_df = pd.DataFrame(output_df.groupby('SUMID')['pop_2010'].sum()).reset_index()
    total_pop_df.rename(columns={ 'pop_2010': 'total_pop_2010' }, inplace=True)

    # merge to add the total population (year 2000) for the provided geographys
    output_df = output_df.merge(total_pop_df, on='SUMID', how='left')
    output_df.fillna(0, inplace=True)

    # calculate weights for the provided geography
    output_df['weight_2010'] = output_df['pop_2010'] / output_df['total_pop_2010']
    output_df.fillna(0, inplace=True)

    # output to stdout
    output_df[['GEOID00', 'afact_2000', 'GEOID10', 'weight_2010']].to_csv(sys.stdout, index=False)
