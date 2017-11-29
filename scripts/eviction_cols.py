import csv
import sys
import numpy as np
import pandas as pd


if __name__ == '__main__':
    df = pd.read_csv(sys.stdin, dtype={'GEOID': 'object', 'name': 'object', 'parent-location': 'object'})

    # Generate eviction columns
    df['eviction-rate'] = df['evictions'] / (df['renter-occupied-households'] / 100)
    df['eviction-filing-rate'] = df['eviction-filings'] / (df['renter-occupied-households'] / 100)
    # Check leap year for per day calculation
    df['evictions-per-day'] = np.where(
        df['year'] % 4 == 0, df['evictions'] / 366, df['evictions'] / 365
    )

    df.round(2).to_csv(sys.stdout, index=False, quoting=csv.QUOTE_NONNUMERIC)
