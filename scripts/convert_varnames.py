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
    'eviction-filing-rate'
]

VARNAME_CROSSWALK = {
    'st_fips': 'GEOID',
    'co_fips': 'GEOID',
    'placefips': 'GEOID',
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
        'trt_fips': 'object',
        'bkg_fips': 'object'
    })
    df.rename(VARNAME_CROSSWALK, inplace=True)
    df[EVICTION_COLS].to_csv(sys.stdout, index=False)
