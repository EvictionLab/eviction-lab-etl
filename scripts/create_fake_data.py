import sys
import random
import numpy as np
import pandas as pd

YEARS = list(range(2000, 2018))

DATA_COLS = {
    'evictions-per-day': (0, 1000),
    'eviction-rate': (0, 80),
    'eviction-filings': (0, 1000),
    'eviction-filing-rate': (0.0, 20.0)
}

if __name__ == '__main__':
    data_df = pd.read_csv(sys.argv[1], dtype={'GEOID': 'object', 'name': 'object', 'parent-location': 'object'})
    sample_df = pd.read_csv(sys.argv[2])

    sample_dict = {c: sample_df[c].tolist() for c in sample_df.columns.values}

    for col, value in sample_dict.items():
        data_df[col] = data_df['GEOID'].apply(lambda x: random.choice(value))
    for col, value in DATA_COLS.items():
        if isinstance(value[0], int):
            data_df[col] = data_df['GEOID'].apply(lambda x: random.randrange(*value))
        elif isinstance(value[0], float):
            data_df[col] =  data_df['GEOID'].apply(lambda x: random.uniform(*value)).round(2)
    data_df = data_df.round(2)
    data_df = data_df[['GEOID', 'year', 'evictions', 'eviction-rate', 'evictions-per-day', 'eviction-filings', 'eviction-filing-rate']].copy()
    data_df.replace(np.inf, 0, inplace=True)
    data_df.to_csv(sys.stdout, index=False)
