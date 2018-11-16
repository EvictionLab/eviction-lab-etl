"""
Creates weights (allocation factors) for the provided geography level
for mapping 2000 demographics data to 2010 geographies based on the
geographic correspondence file

Arguments
----------
argv[1] : str
    The geography level to create weights for (block-groups or tracts)
argv[2] : str
    The file path to the geography correspondence file 
    generated from http://mcdc.missouri.edu/applications/geocorr2000.html
argv[3] : str
    The file path to the 2000 blocks to 2010 blocks crosswalk, retrieved from 
    https://www.nhgis.org/user-resources/geographic-crosswalks

Outputs
-------
str
    a string of CSV data containing the weights

Example output (tracts):

GEOID00,        GEOID10,        weight
01001020100,    01001020100,    0.9994897601882233
01001020100,    01001020600,    0.0
01001020100,    01001020802,    0.0005102398117768544
01001020200,    01001020200,    1.0

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
    crosswalk_df = pd.read_csv(
        sys.argv[3], dtype={
            'GEOID00': 'object',
            'GEOID10': 'object'
        })
    crosswalk_df.drop(['PAREA'], axis=1, inplace=True)

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

    # join crosswalk dataframe with geo correspondence file using the year 2000 full block GEOID
  
    geocorr_join = geocorr_df[['GEOID00', 'pop2k']].copy()
    del geocorr_df
    crosswalk_join = crosswalk_df.merge(geocorr_join, on='GEOID00', how='left')
    del geocorr_join
    crosswalk_join.fillna(0, inplace=True)

    # calculate 2010 block populations by multiplying 2000 population by weight
    crosswalk_join['pop10'] = crosswalk_join['pop2k'] * crosswalk_join['WEIGHT']

    # create an int column for block drop the GEOID object columns for memory purposes
    # crosswalk_join['block_00'] = crosswalk_join['GEOID00'].str.slice(-4).astype(int)
    # crosswalk_join['block_10'] = crosswalk_join['GEOID10'].str.slice(-4).astype(int)

    # trim block level GEOIDs to get provided geography level GEOID (block group or tract)
    crosswalk_join['GEOID00'] = crosswalk_join['GEOID00'].str[:geoid_slice]
    crosswalk_join['GEOID10'] = crosswalk_join['GEOID10'].str[:geoid_slice]

    # sum the populations for the provided geography level
    total_pop_2010 = pd.DataFrame(crosswalk_join.groupby('GEOID10')['pop10'].sum()).reset_index()
    total_pop_2010.rename(columns={'pop10': 'total_pop_10'}, inplace=True)
    
    # merge to add the total population (year 2000) for the provided geographys
    geo_crosswalk = crosswalk_join.merge(total_pop_2010, on=['GEOID10'], how='left')
    del crosswalk_join
    del total_pop_2010

    # calculate weights for the provided geography
    geo_crosswalk['weight_2010'] = geo_crosswalk['pop10'] / geo_crosswalk['total_pop_10']
    # geo_crosswalk.fillna(0, inplace=True)

    # output to stdout
    geo_crosswalk.to_csv(sys.stdout, index=False)