import os
import sys
import pandas as pd

if __name__ == '__main__':
    us_data_df = pd.read_csv(sys.argv[1], dtype={'GEOID': 'object'})
    us_center_df = pd.read_csv(sys.argv[2], dtype={'GEOID': 'object'})
    us_df = us_data_df.merge(us_center_df, on='GEOID')

    pop_col = sorted([c for c in us_df.columns.values.tolist() if c.startswith('population-')])[-1]
    us_df = us_df.loc[
        us_df['layer'].isin(['states', 'counties', 'zip-codes', 'cities']),
        ['GEOID', 'name', 'parent-location', pop_col, 'layer', 'longitude', 'latitude']
    ].copy()

    # Write full JSON file
    us_df.to_json(sys.argv[3], orient='records')

    first_chars = set([n[0] for n in us_df['name'].str.lower().tolist()])
    first_two_chars = set([n[:2] for n in us_df['name'].str.lower().tolist()])

    # Iterate through lower-cased first two characters, create file based off of each
    for c in first_chars.union(first_two_chars):
        c_path = os.path.join(sys.argv[4], '{}.json'.format(c))
        us_df['lower_name'] = us_df['name'].str.lower()
        us_df.loc[us_df['name'].str.startswith(c)].to_json(c_path, orient='records')
