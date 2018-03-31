import sys
import json
import pandas as pd

EVICTION_COLS = [
    'GEOID',
    'year',
    'renter-occupied-households',
    'eviction-filings',
    'evictions',
    'eviction-rate',
    'eviction-filing-rate',
    'imputed',
    'subbed'
]

VARNAME_CROSSWALK = {
    'st_fips': 'GEOID',
    'co_fips': 'GEOID',
    'placefips': 'GEOID',
    'pl_fips': 'GEOID',
    'trt_fips': 'GEOID',
    'bkg_fips': 'GEOID',
    'tenure': 'renter-occupied-households',
    'renter_households': 'renter-occupied-households',
    'cases': 'eviction-filings',
    'evictrate': 'eviction-rate',
    'caserate': 'eviction-filing-rate'
}

if __name__ == '__main__':
    df = pd.read_csv(sys.stdin, dtype={
        'st_fips': 'object',
        'co_fips': 'object',
        'placefips': 'object',
        'pl_fips': 'object',
        'trt_fips': 'object',
        'bkg_fips': 'object'
    })
    df.rename(columns=VARNAME_CROSSWALK, inplace=True)
    output_cols = [c for c in df.columns.values if c in EVICTION_COLS]
    # Add imputed and subbed if not included
    add_cols = [c for c in ['imputed', 'subbed'] if c not in output_cols]
    for c in add_cols:
        output_cols.append(c)
        df[c] = 0
    df[output_cols].to_csv(sys.stdout, index=False)
