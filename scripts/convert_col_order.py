import sys
import pandas as pd
from data_constants import COLUMN_ORDER

if __name__ == '__main__':
    df = pd.read_csv(
        sys.stdin,
        dtype={
            'GEOID': 'object',
            'name': 'object',
            'parent-location': 'object'
        })

    # Ensure all columns are in CSV, output in order
    assert all([c in df.columns.values for c in COLUMN_ORDER])
    df[COLUMN_ORDER].to_csv(sys.stdout, index=False)
