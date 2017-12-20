import sys
import random
import numpy as np
import pandas as pd

YEARS = list(range(2000, 2018))


if __name__ == '__main__':
    data_df = pd.read_csv(sys.argv[1], dtype={'GEOID': 'object', 'name': 'object', 'parent-location': 'object'})
    sample_df = pd.read_csv(sys.argv[2])

    sample_dict = {c: sample_df[c].tolist() for c in sample_df.columns.values}

    data_df['evictions'] = data_df['GEOID'].apply(lambda x: random.choice(sample_dict['evictions']))
    data_df['eviction-filings'] = data_df['GEOID'].apply(lambda x: random.choice(sample_dict['evictions']))

    data_df = data_df.round(2)
    data_df = data_df[['GEOID', 'year', 'evictions', 'eviction-filings']].copy()
    data_df.replace(np.inf, 0, inplace=True)
    data_df.to_csv(sys.stdout, index=False)
