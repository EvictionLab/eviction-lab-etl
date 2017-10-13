import sys
import pandas as pd

CONTEXT_COLS = ['GEOID', 'name', 'parent-location', 'layer']
DATA_COLS = [
    'evictions', 'population', 'area', 'average-household-size',
    'renting-occupied-households', 'poverty-rate', 'eviction-rate'
]

if __name__ == '__main__':
    input_df = pd.read_csv(sys.stdin, dtype={'GEOID': 'object'})
    year_data_cols = []
    # Append -YEAR to each data column name
    for year in input_df['year'].unique():
        year_cols = ['{}-{}'.format(col, year) for col in DATA_COLS]
        year_data_cols.extend(['{}-{}'.format(col, year) for col in DATA_COLS])
        input_df[year_cols] = input_df.loc[input_df['year'] == year, DATA_COLS]

    # Group the dataframe by GEOID, and take the max (not-null in this case) value
    # for each newly-created data column
    output_df = input_df.groupby('GEOID')[CONTEXT_COLS[1:] + year_data_cols].max()
    output_df = pd.DataFrame(output_df).reset_index()
    output_df.to_csv(sys.stdout, index=False)