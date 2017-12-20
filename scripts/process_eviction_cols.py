import csv
import sys
import numpy as np
import pandas as pd


if __name__ == '__main__':
    df = pd.read_csv(sys.stdin, dtype={'GEOID': 'object', 'name': 'object', 'parent-location': 'object'})

    # Generate eviction columns
    df['eviction-rate'] = df['evictions'] / (df['renter-occupied-households'] / 100)
    df['eviction-filing-rate'] = df['eviction-filings'] / (df['renter-occupied-households'] / 100)

    df.round(2).to_csv(sys.stdout, index=False, quoting=csv.QUOTE_NONNUMERIC)
