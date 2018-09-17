import sys
import pandas as pd
from functools import reduce

INT_COLS = ['imputed', 'subbed', 'low-flag']

if __name__ == '__main__':
    join_keys = sys.argv[1].split(',')
    dtypes = {k: 'object' for k in join_keys}
    dtypes['name'] = 'object'
    dtypes['parent-location'] = 'object'
    dtypes['GEOID'] = 'object'
    df_list = []
    for filename in sys.argv[2:]:
        df = pd.read_csv(filename, dtype=dtypes)
        df.set_index(join_keys, inplace=True)
        df_list.append(df)
    output_df = reduce(lambda x, y: x.join(y, how='outer'), df_list)

    # Handle int cols
    for col in INT_COLS:
        if col in output_df.columns:
            output_df[col] = output_df[col].fillna(0).astype(int)

    # Fill in missing `name` and `parent-location` after join
    if sys.argv[1] == 'GEOID,year':
        # get dataframe with name,parent-location for each GEOID
        not_null = output_df[output_df['name'].notnull()].reset_index(level=['year'])
        names_df = not_null[['name', 'parent-location']].drop_duplicates()
        # merge names,parent-location with dataset
        output_df = output_df.reset_index(level=['year'])
        output_df = pd.merge(output_df, names_df, how='left', left_index=True, right_index=True)
        # rename merged columns
        output_df.rename(columns={'name_y': 'name', 'parent-location_y': 'parent-location'}, inplace=True)
        # drop old columns that are missing data
        output_df = output_df.drop(['name_x', 'parent-location_x'], axis=1)
        # remove any remaining records with no names
        output_df = output_df[output_df['name'].notnull()]
        # reorder cols
        cols = list(output_df.columns.values)
        plcol = cols.pop()
        namecol = cols.pop()
        cols.insert(1,namecol)
        cols.insert(2,plcol)
        output_df = output_df[cols]

    output_df.to_csv(sys.stdout)
