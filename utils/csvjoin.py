import sys
import pandas as pd
from functools import reduce


if __name__ == '__main__':
    join_keys = sys.argv[1].split(',')
    dtypes = {k: 'object' for k in join_keys}
    dtypes['name'] = 'object'
    dtypes['parent-location'] = 'object'
    df_list = []
    for filename in sys.argv[2:]:
        df = pd.read_csv(filename, dtype=dtypes)
        df.set_index(join_keys, inplace=True)
        for c in ['name', 'parent-location']:
            if c in df.columns.values:
                df[c] = df[c].apply(lambda x: str(x).encode('ascii', 'ignore').decode('ascii'))
        df_list.append(df)
    output_df = reduce(lambda x, y: x.join(y, how='left'), df_list)
    output_df.to_csv(sys.stdout)
