import sys
import pandas as pd
    

if __name__ == '__main__':
    geocorr_df = pd.read_csv(sys.argv[2], dtype={
        'county': 'object',
        '2000 Census Tract': 'object',
        'bg': 'object',
        '2000 Census Block': 'object',
    })
    crosswalk_df = pd.read_csv(sys.argv[3], dtype={
        'GEOID00': 'object',
        'GEOID10': 'object'
    })

    geocorr_df.rename(
        columns={'Pop 2009 estimate fr county level ests': 'pop09'},
        inplace=True
    )

    geocorr_df['GEOID00'] = (
        geocorr_df['county'] +
        geocorr_df['2000 Census Tract'].str.replace('.', '') +
        geocorr_df['2000 Census Block']
    )

    if sys.argv[1] == 'tracts':
        geocorr_df['GEOID'] = (
            geocorr_df['county'] +
            geocorr_df['2000 Census Tract'].str.replace('.', '')
        )
        geoid_slice = -4
    elif sys.argv[1] == 'block-groups':
        geocorr_df['GEOID'] = (
            geocorr_df['county'] +
            geocorr_df['2000 Census Tract'].str.replace('.', '') +
            geocorr_df['bg']
        )
        geoid_slice = -3
    else:
        raise ValueError('Invalid geography string supplied')
    total_pop_df = pd.DataFrame(geocorr_df.groupby('GEOID')['pop09'].sum()).reset_index()
    total_pop_df.rename(columns={'GEOID': 'GEOID00', 'pop09': 'total_pop'}, inplace=True)

    geocorr_join = geocorr_df[['GEOID00', 'pop09']].copy()
    crosswalk_join = crosswalk_df.merge(geocorr_join, on='GEOID00', how='left')
    crosswalk_join.fillna(0, inplace=True)
    crosswalk_join['pop10'] = crosswalk_join['pop09'] * crosswalk_join['WEIGHT']

    crosswalk_join['geo_GEOID00'] = crosswalk_join['GEOID00'].str.slice(0, geoid_slice)
    crosswalk_join['geo_GEOID10'] = crosswalk_join['GEOID10'].str.slice(0, geoid_slice)
    geo_crosswalk = pd.DataFrame(
        crosswalk_join.groupby(['geo_GEOID00', 'geo_GEOID10'])['pop09', 'pop10'].sum()
    ).reset_index()
    geo_crosswalk.rename(columns={'geo_GEOID00': 'GEOID00', 'geo_GEOID10': 'GEOID10'}, inplace=True)
    geo_crosswalk = geo_crosswalk.merge(total_pop_df, on='GEOID00', how='left')
    geo_crosswalk.fillna(0, inplace=True)
    geo_crosswalk['weight'] = geo_crosswalk['pop10'] / geo_crosswalk['total_pop']
    geo_crosswalk.fillna(0, inplace=True)
    
    output_df = geo_crosswalk[['GEOID00', 'GEOID10', 'weight']].copy()
    output_df.to_csv(sys.stdout, index=False)
