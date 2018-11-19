"""
Converts census variable counts to rates:
"""

import sys
import csv
import numpy as np
import pandas as pd
from data_constants import OUTPUT_COLS


def generated_cols(df):
    # create percent renter occupied stat
    if 'occupied-housing-units' in df.columns.values:
        df['pct-renter-occupied'] = np.where(
            df['occupied-housing-units'] > 0,
            (df['renter-occupied-households'] / df['occupied-housing-units']) *
            100, 0)
    else:
        df['pct-renter-occupied'] = np.nan

    # create poverty rate from poverty population
    if 'poverty-pop' in df.columns.values:
        df[['population',
            'poverty-pop']] = df[['population',
                                  'poverty-pop']].apply(pd.to_numeric)
        pop_col = 'population'
        if 'total-poverty-pop' in df.columns.values:
            pop_col = 'total-poverty-pop'
            df[[pop_col]] = df[[pop_col]].apply(pd.to_numeric)
        df['poverty-rate'] = np.where(
            df[pop_col] > 0, (df['poverty-pop'] / df[pop_col]) * 100, 0)
    else:
        df['poverty-rate'] = np.nan

    # create race percentages based on counts
    for dem in [
            'hispanic', 'white', 'af-am', 'am-ind', 'asian', 'nh-pi', 'other',
            'multiple'
    ]:
        if dem + '-pop' in df.columns.values:
            df[[dem + '-pop']] = df[[dem + '-pop']].apply(pd.to_numeric)
            df['pct-{}'.format(dem)] = np.where(
                df['population'] > 0,
                (df['{}-pop'.format(dem)] / df['population']) * 100, 0)
    
    # set values not present as "NaN"
    for col in OUTPUT_COLS:
        if col not in df.columns.values:
            df[col] = np.nan
    return df[OUTPUT_COLS].copy()


if __name__ == '__main__':
    df = pd.read_csv(
        sys.stdin,
        dtype={
            'GEOID': 'object',
            'name': 'object',
            'parent-location': 'object'
        })
    df = generated_cols(df).round(2)
    df.to_csv(sys.stdout, index=False, quoting=csv.QUOTE_NONNUMERIC)
