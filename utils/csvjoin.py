import sys
import pandas as pd
from functools import reduce

INT_COLS = ['imputed', 'subbed', 'low-flag']

if __name__ == '__main__':
    join_keys = sys.argv[1].split(',')
    dtypes = {k: 'object' for k in join_keys}
    dtypes['name'] = 'object'
    dtypes['parent-location'] = 'object'
    df_list = []
    for filename in sys.argv[2:]:
        df = pd.read_csv(filename, dtype=dtypes)
        df.set_index(join_keys, inplace=True)
        df_list.append(df)
    output_df = reduce(lambda x, y: x.join(y, how='left'), df_list)
    # Handle int cols
    for col in INT_COLS:
        if col in output_df.columns:
            output_df[col] = output_df[col].fillna(0).astype(int)
    output_df.to_csv(sys.stdout)
