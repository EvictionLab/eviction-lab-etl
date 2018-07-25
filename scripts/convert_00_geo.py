import sys
import csv
import pandas as pd
from create_census_data import create_tract_name
from data_constants import NUMERIC_COLS

if __name__ == '__main__':
    data_df = pd.read_csv(
        sys.stdin,
        dtype={
            'GEOID': 'object',
            'name': 'object',
            'parent-location': 'object'
        })
    weight_df = pd.read_csv(
        sys.argv[2], dtype={
            'GEOID00': 'object',
            'GEOID10': 'object'
        })

    output_df = weight_df.merge(
        data_df, left_on='GEOID00', right_on='GEOID', how='left')
    context_df = output_df[['GEOID10', 'name', 'parent-location']].copy()
    context_df.drop_duplicates(subset=['GEOID10'], inplace=True)

    output_df[NUMERIC_COLS] = output_df[NUMERIC_COLS].multiply(
        output_df['weight'], axis=0)
    output_df = pd.DataFrame(
        output_df.groupby(['GEOID10',
                           'year'])[NUMERIC_COLS].sum()).reset_index()
    output_df = output_df.merge(context_df, on='GEOID10', how='left')
    output_df['year'] = output_df['year'].astype('int')

    output_df.rename(columns={'GEOID10': 'GEOID'}, inplace=True)
    if sys.argv[1] == 'tracts':
        output_df['name'] = output_df['GEOID'].str.slice(5).apply(
            create_tract_name)
    elif sys.argv[1] == 'block-groups':
        output_df['name'] = output_df['GEOID'].str.slice(5, -1).apply(
            create_tract_name) + '.' + output_df['GEOID'].str.slice(-1)
    else:
        raise ValueError('Invalid geography string supplied')

    output_df.to_csv(sys.stdout, index=False, quoting=csv.QUOTE_NONNUMERIC)
