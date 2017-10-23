import re
import csv
import sys
import pandas as pd


if __name__ == '__main__':
    input_df = pd.read_csv(sys.stdin, dtype={'GEOID': 'object', 'n': 'object'})
    output_cols = sys.argv[1].split(',')
    input_df[output_cols].to_csv(
        sys.stdout, index=False, quoting=csv.QUOTE_NONNUMERIC
    )
