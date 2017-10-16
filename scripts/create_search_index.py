import os
import sys
import pandas as pd

DATA_COLS = ['GEOID', 'name', 'parent-location', 'layer', 'longitude', 'latitude']

if __name__ == '__main__':
    us_data_df = pd.read_csv(sys.argv[1], dtype={'GEOID': 'object'})
    us_center_df = pd.read_csv(sys.argv[2], dtype={'GEOID': 'object'})
    us_df = us_data_df.merge(us_center_df, on=['GEOID', 'layer'])

    pop_col = sorted([c for c in us_df.columns.values.tolist() if c.startswith('population-')])[-1]
    DATA_COLS.append(pop_col)

    us_df = us_df.loc[
        us_df['layer'].isin(['states', 'counties', 'zip-codes', 'cities']),
        ['GEOID', 'name', 'parent-location', pop_col, 'layer', 'longitude', 'latitude']
    ].copy()
    us_df['name'] = us_df['name'].str.replace('Zip Code ', '')
    us_df['lower_name'] = us_df['name'].str.lower()

    # Write full JSON file
    us_df.to_json(sys.argv[3], orient='records')

    first_chars = set([n[0] for n in us_df['lower_name'].tolist()])
    first_two_chars = set([n[:2] for n in us_df['lower_name'].tolist()])

    # Take first 10 of each first single character, in descending order of population
    for c in first_chars:
        c_path = os.path.join(sys.argv[4], '{}.json'.format(c))
        first_char_df = us_df.loc[us_df['lower_name'].str.startswith(c), DATA_COLS]
        first_char_df = first_char_df.sort_values(by=pop_col, ascending=False)[:10]
        first_char_df[DATA_COLS].to_json(c_path, orient='records')

    # Iterate through lower-cased first two characters, create file based off of each
    for c in first_two_chars:
        c_path = os.path.join(sys.argv[4], '{}.json'.format(c))
        us_df.loc[us_df['lower_name'].str.startswith(c), DATA_COLS].to_json(c_path, orient='records')
