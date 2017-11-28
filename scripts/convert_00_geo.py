import sys
import csv
import pandas as pd
from census_data import *


if __name__ == '__main__':
    data_df = pd.read_csv(sys.argv[2], dtype={'GEOID': 'object', 'name': 'object', 'parent-location': 'object'})
    weight_df = pd.read_csv(sys.argv[3], dtype={'GEOID00': 'object', 'GEOID10': 'object'})

    output_df = weight_df.merge(data_df, left_on='GEOID00', right_on='GEOID', how='left')
    output_df[NUMERIC_OUTPUT_COLS] = output_df[NUMERIC_OUTPUT_COLS].multiply(output_df['weight'], axis=0).round(2)
    output_df = pd.DataFrame(
        output_df.groupby(['GEOID10', 'name', 'parent-location', 'year'])[NUMERIC_OUTPUT_COLS].sum()
    ).reset_index()

    output_df.rename(columns={'GEOID10': 'GEOID'}, inplace=True)
    if sys.argv[1] == 'tracts':
        output_df['name'] = output_df['GEOID'].str.slice(5).str.lstrip('0')
    elif sys.argv[1] == 'block-groups':
        output_df['name'] = output_df['GEOID'].str.slice(5, -1).str.lstrip('0') + '.' + output_df['GEOID'].str.slice(-1)
    else:
        raise ValueError('Invalid geography string supplied')

    output_df.to_csv(sys.argv[2], index=False, quoting=csv.QUOTE_NONNUMERIC)
