import sys
import random
import numpy as np
import pandas as pd

YEARS = list(range(1990, 2018))

DATA_COLS = {
    'evictions-per-day': (0, 1000),
    'eviction-rate': (0, 80),
    'eviction-filings': (0, 1000),
    'eviction-filing-rate': (0.0, 20.0),
    # 'pct-renter-occupied': (0.0, 1.0),
    # 'median-gross-rent': (500, 1800),
    # 'median-household-income': (10000, 100000),
    # 'median-property-value': (10000, 1000000),
    # 'placeholder': (0.0, 1.0),
    # 'pct-white': (0.0, 1.0),
    # 'pct-af-am': (0.0, 1.0),
    # 'pct-hispanic': (0.0, 1.0),
    # 'pct-am-ind': (0.0, 1.0),
    # 'pct-nh-pi': (0.0, 1.0),
    # 'pct-multiple': (0.0, 1.0),
    # 'pct-other': (0.0, 1.0),
    # 'poverty-rate': (0.0, 0.6)
}

if __name__ == '__main__':
    context_df = pd.read_csv(sys.argv[1], dtype={'GEOID': 'object', 'name': 'object'})
    sample_df = pd.read_csv(sys.argv[2])

    sample_dict = {c: sample_df[c].tolist() for c in sample_df.columns.values}
    year_df_list = []

    for year in YEARS:
        year_df = context_df.copy()
        year_df['year'] = year
        # Add columns from random data and sample of semi-real data
        for col, value in sample_dict.items():
            year_df[col] = year_df['GEOID'].apply(lambda x: random.choice(value))
        for col, value in DATA_COLS.items():
            if isinstance(value[0], int):
                year_df[col] = year_df['GEOID'].apply(lambda x: random.randrange(*value))
            elif isinstance(value[0], float):
                year_df[col] =  year_df['GEOID'].apply(lambda x: random.uniform(*value)).round(2)
        year_df_list.append(year_df)

    output_df = pd.concat(year_df_list).round(2)
    output_df.replace(np.inf, 0, inplace=True)
    output_df.to_csv(sys.stdout, index=False)
