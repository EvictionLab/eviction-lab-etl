import os
import sys
import csv
import json
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CONTEXT_COLS = ['GEOID', 'n', 'pl']

YEAR_MAP = {'00': 2000, '10': 2010}

if __name__ == '__main__':
    with open(
            os.path.join(os.path.dirname(BASE_DIR), 'conf', 'col_map.json'),
            'r') as col_f:
        col_map = json.load(col_f)

    if len(sys.argv) > 1:
        min_year = YEAR_MAP[sys.argv[1]]
        max_year = min_year + 9
    else:
        min_year = 2000
        max_year = 2019

    input_df_list = []

    input_df_iter = pd.read_csv(
        sys.stdin,
        dtype={
            'GEOID': 'object',
            'name': 'object',
            'parent-location': 'object'
        },
        iterator=True,
        chunksize=10000)
    for df in input_df_iter:
        input_df_list.append(
            df.loc[(df['year'] >= min_year) & (df['year'] <= max_year)])

    input_df = pd.concat(input_df_list)
    input_df.rename(columns=col_map, inplace=True)

    # Get non-context or year columns
    data_cols = [
        c for c in input_df.columns.values if c not in CONTEXT_COLS + ['year']
    ]

    # Create context dataframe to join later
    max_year = input_df['year'].max()
    context_df = input_df.loc[input_df['year'] == max_year, CONTEXT_COLS]
    context_df.drop_duplicates(subset=['GEOID'], inplace=True)
    context_df.set_index('GEOID', inplace=True)

    # Create list of dataframes by year with -YEAR appended to data columns
    year_df_list = []
    for year in input_df['year'].unique():
        year_df = input_df.loc[input_df['year'] == year, ['GEOID'] + data_cols]
        year_df.drop_duplicates(subset=['GEOID'], inplace=True)
        year_df.set_index('GEOID', inplace=True)
        year_str = str(year)[2:]
        year_df.columns = [
            '{}-{}'.format(col, year_str) for col in year_df.columns.values
        ]
        year_df_list.append(year_df)

    # Join all year dataframes together with context on GEOID index
    output_df = pd.concat([context_df] + year_df_list, axis=1)
    output_df.index.name = 'GEOID'

    # Replace leftover inf and nan data with -1 null placeholder
    output_df.replace([np.inf, -np.inf, np.nan], -1.0, inplace=True)

    output_df = output_df[output_df['n'] != -1.0]
    output_df[~output_df.index.duplicated()].to_csv(
        sys.stdout, quoting=csv.QUOTE_NONNUMERIC)
