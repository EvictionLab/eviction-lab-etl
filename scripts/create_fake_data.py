import sys
import random
import pandas as pd

YEARS = list(range(1980, 2010))

DATA_COLS = {
    'evictions-per-day': (0, 1000),
    'pct-renter-occupied': (0, 100),
    'median-gross-rent': (500, 1800),
    'median-household-income': (10000, 100000),
    'median-property-value': (10000, 1000000),
    'placeholder': (0, 100),
    'pct-white': (0, 100),
    'pct-af-am': (0, 100),
    'pct-hispanic': (0, 100),
    'pct-am-ind': (0, 100),
    'pct-nh-pi': (0, 100),
    'pct-multiple': (0, 100),
    'pct-other': (0, 100),
}

if __name__ == '__main__':
    context_df = pd.read_csv(sys.argv[1], dtype={'GEOID': 'object', 'name': 'object'})
    sample_df = pd.read_csv(sys.argv[2])

    sample_dict = {c: sample_df[c].tolist() for c in sample_df.columns.values}

    # Add columns from random data and sample of semi-real data
    for col, value in DATA_COLS.items():
        context_df[col] = context_df['GEOID'].apply(lambda x: random.randrange(*value))
    for col, value in sample_dict.items():
        context_df[col] = context_df['GEOID'].apply(lambda x: random.choice(value))
    context_df['eviction-rate'] = context_df['evictions'] / context_df['renting-occupied-households']
    context_df['eviction-rate'] = context_df['eviction-rate'].round(2)

    year_df_list = [context_df]

    # Just copies year data across rather than generating each time
    # More to test volume of data than variation
    for year in YEARS:
        year_df = context_df.copy()
        year_df['year'] = year
        year_df_list.append(year_df)

    output_df = pd.concat(year_df_list)
    output_df.to_csv(sys.stdout, index=False)
