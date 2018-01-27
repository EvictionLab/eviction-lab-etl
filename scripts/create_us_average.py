import sys
import json
import pandas as pd

if __name__ == '__main__':
    df = pd.read_csv(
        sys.argv[1],
        engine='python',
        dtype={'GEOID': 'object', 'n': 'object', 'pl': 'object'}
    )

    # data_cols = [c for c in df.columns.values if '-' in c]
    eviction_cols = [c for c in df.columns.values if 'er-' in c or 'efr-' in c]
    us_avg = df[eviction_cols].mean().round(2).to_dict()
    json.dump(us_avg, sys.stdout)
