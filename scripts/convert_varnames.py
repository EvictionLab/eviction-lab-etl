import sys
import pandas as pd
from data_constants import INT_COLS

EVICTION_COLS = [
    'GEOID',
    'year',
    'renter-occupied-households',
    'eviction-filings',
    'eviction-filings-imp',
    'eviction-filings-non-imp',
    'evictions',
    'evictions-imp',
    'evictions-non-imp',
    'eviction-rate',
    'eviction-filing-rate',
    'imputed',
    'subbed',
    'low-flag',
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
    'cases_imp': 'eviction-filings-imp',
    'cases_non_imp': 'eviction-filings-non-imp',
    'caserate': 'eviction-filing-rate',
    'evictions_imp': 'evictions-imp',
    'evictions_non_imp': 'evictions-non-imp',
    'evictrate': 'eviction-rate',
    'low_county_ind': 'low-flag',
    'low_state_ind': 'low-flag'
}

ID_KEYS = [
    'GEOID', 'st_fips', 'co_fips', 'placefips', 'pl_fips', 'trt_fips',
    'bkg_fips'
]

if __name__ == '__main__':
    df = pd.read_csv(sys.stdin, dtype={key: 'object' for key in ID_KEYS})
    # Assert at least one of the ID keys is in the input file
    assert any([key in df.columns.values for key in ID_KEYS])
    df.rename(columns=VARNAME_CROSSWALK, inplace=True)
    output_cols = [c for c in EVICTION_COLS if c in df.columns.values]
    # Add imputed and subbed if not included and not non-imputed data
    if not any(['-imp' in c for c in output_cols]):
        add_cols = [c for c in ['imputed', 'subbed'] if c not in output_cols]
        for c in add_cols:
            output_cols.append(c)
            df[c] = 0
    for col in INT_COLS:
        if col in df.columns:
            df[col] = df[col].fillna(0).astype(int)
    # Fail if GEOID len not one of allowed values, which would prevent join
    assert df['GEOID'].str.len().mean() in [2, 5, 7, 11, 12]
    df[output_cols].to_csv(sys.stdout, index=False)
