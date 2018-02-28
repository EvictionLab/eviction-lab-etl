import os
import csv
import sys
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

if __name__ == '__main__':
    geo = sys.argv[1]
    df = pd.read_csv(sys.stdin, dtype={'GEOID': 'object', 'name': 'object', 'parent-location': 'object'})

    df.to_csv(sys.stdout, index=False, quoting=csv.QUOTE_NONNUMERIC)
