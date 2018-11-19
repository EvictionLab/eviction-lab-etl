"""
Recalculates allocation factors for a given geography level and geographic
correspondence file.

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

Output has header: GEOID00,pop2k,afact


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

    # combine geography levels in the 2000 geo correspondence file to create
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

    # recalculate allocation factors
    pop2k_totals = pd.DataFrame(geocorr_df.groupby('GEOID')['pop2k'].sum()).reset_index()
    pop2k_totals.rename(columns={'pop2k': 'total_pop_00'}, inplace=True)
    geocorr_df = geocorr_df.merge(pop2k_totals, on='GEOID', how='left')
    del pop2k_totals
    geocorr_df['afact'] = geocorr_df['pop2k'] / geocorr_df['total_pop_00']

    output_df = geocorr_df[['GEOID00', 'pop2k', 'afact']].copy()

    output_df.to_csv(sys.stdout, index=False)
