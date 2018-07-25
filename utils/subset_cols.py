import csv
import sys
import numpy as np
import pandas as pd

if __name__ == '__main__':
    input_df = pd.read_csv(
        sys.stdin, dtype={
            'GEOID': 'object',
            'n': 'object',
            'pl': 'object'
        })
    col_args = sys.argv[1].split(',')

    # Passing -i flag drops listed columns instead of retaining them
    inverse = False
    if len(sys.argv) > 2:
        inverse = sys.argv[2] == '-i'

    if not inverse:
        missing_cols = [
            c for c in col_args if c not in input_df.columns.values
        ]
        for c in missing_cols:
            input_df[c] = np.nan
        input_df = input_df[col_args]
    else:
        input_df.drop(col_args, axis=1, inplace=True)

    input_df.to_csv(sys.stdout, index=False, quoting=csv.QUOTE_NONNUMERIC)
