import sys
import pandas as pd
from functools import reduce

CONTEXT_COLS = ['GEOID', 'name', 'parent-location', 'layer']

if __name__ == '__main__':
    input_df = pd.read_csv(sys.stdin, dtype={'GEOID': 'object'})
    # Get non-context or year columns
    data_cols = [c for c in input_df.columns.values if c not in CONTEXT_COLS + ['year']]

    # Create context dataframe to join later
    max_year = input_df['year'].max()
    context_df = input_df.loc[input_df['year'] == max_year, CONTEXT_COLS]
    context_df.set_index('GEOID', inplace=True)

    # Create list of dataframes by year with -YEAR appended to data columns
    year_df_list = []
    for year in input_df['year'].unique():
        year_df = input_df.loc[input_df['year'] == year, ['GEOID'] + data_cols]
        year_df.set_index('GEOID', inplace=True)
        year_df.columns = ['{}-{}'.format(col, year) for col in year_df.columns.values]
        year_df_list.append(year_df)

    # Join all year dataframes together with context on GEOID index
    output_df = reduce(lambda x, y: x.join(y, how='left'), [context_df] + year_df_list)
    output_df.to_csv(sys.stdout, index=False)