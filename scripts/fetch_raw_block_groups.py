import os
import sys
import csv
import time
import pandas as pd
import sys
from utils_census import CensusDataStore

if __name__ == '__main__':

    c = CensusDataStore()
    
    if sys.argv[2] == '00':
        df = c.fetchAllBlockGroupData2000(sys.argv[1])
    elif sys.argv[2] == '10':
        df = c.fetchAllBlockGroupData2010(sys.argv[1])
    else:
        raise ValueError('Invalid year suffix supplied')

    if df is not None and 'state' in df.columns.values:
        df['GEOID'] = df['state'].str.zfill(2) + df['county'].str.zfill(
            3) + df['tract'].str.zfill(6) + df['block group']
        df.to_csv(sys.stdout, index=False, quoting=csv.QUOTE_NONNUMERIC)
