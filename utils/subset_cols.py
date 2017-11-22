import re
import csv
import sys
import numpy as np
import pandas as pd


if __name__ == '__main__':
    input_df = pd.read_csv(sys.stdin, dtype={'GEOID': 'object', 'n': 'object', 'pl': 'object'})
    output_cols = sys.argv[1].split(',')
    missing_cols = [c for c in output_cols if c not in input_df.columns.values]
    for c in missing_cols:
        input_df[c] = np.nan
    input_df[output_cols].to_csv(
        sys.stdout, index=False, quoting=csv.QUOTE_NONNUMERIC
    )
