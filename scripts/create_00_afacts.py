"""
Recalculates the allocation factor in the geo correspondence file

Arguments
----------
argv[1] : str
    The geography level to create weights for (block-groups or tracts)
argv[2] : str
    The file path to the geography correspondence file 
    generated from http://mcdc.missouri.edu/applications/geocorr2000.html

Outputs
-------
str
    a string of CSV data containing the weights

Example output (tracts):

county, tract,      bg, block,  pop2k,  afact
01001,  0201.00,    1,  1000,   16,     0.013 
01001,  0201.00,    1,  1001,   40,     0.034 
01001,  0201.00,    1,  1002,   284,    0.239 
01001,  0201.00,    1,  1003,   47,     0.04 

"""

import sys
import pandas as pd

if __name__ == '__main__':
    # load provided csv files into dataframes
    geocorr_df = pd.read_csv(
        sys.argv[2],
        dtype={
            'county': 'object',
            'tract': 'object',
            'bg': 'object',
            'block': 'object',
            'pop2k': 'float64'
        })

    # combine geography levels in the geo correspondence file to create
    # block level GEOIDs for all entries
    geocorr_df['GEOID00'] = (
        geocorr_df['county'] + geocorr_df['tract'].str.replace(
            '.', '') + geocorr_df['block'])

    # Create GEOID for the provided geography level (tracts or block groups)
    if sys.argv[1] == 'tracts':
        geocorr_df['GEOID'] = (
            geocorr_df['county'] + geocorr_df['tract'].str.replace(
                '.', ''))
        # Slice the last 4 characters off of block GEOID to get tract GEOID
        geoid_slice = -4
    elif sys.argv[1] == 'block-groups':
        geocorr_df['GEOID'] = (
            geocorr_df['county'] + geocorr_df['tract'].str.replace(
                '.', '') + geocorr_df['bg'])
        # Slice the last 3 characters off of block GEOID to get block group GEOID
        geoid_slice = -3
    else:
        raise ValueError('Invalid geography string supplied')

    # create dataframe containing total population for the provided geography level
    total_pop_df = pd.DataFrame(geocorr_df.groupby('GEOID')['pop2k'].sum()).reset_index()
    total_pop_df.rename(columns={ 'pop2k': 'total_pop' }, inplace=True)

    # merge to add the total population (year 2000) for the provided geographys
    geocorr_df = geocorr_df.merge(total_pop_df, on='GEOID', how='left')
    geocorr_df.fillna(0, inplace=True)

    # calculate weights for the provided geography
    geocorr_df['allocation'] = geocorr_df['pop2k'] / geocorr_df['total_pop']
    geocorr_df.fillna(0, inplace=True)

    # output to stdout
    output_df = geocorr_df[['GEOID', 'GEOID00', 'county', 'tract', 'bg', 'block', 'pop2k', 'allocation']].copy()
    output_df.to_csv(sys.stdout, index=False)
