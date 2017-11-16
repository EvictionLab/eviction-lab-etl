import sys
import pandas as pd


if __name__ == '__main__':
    bg_df = None
    for filename in sys.argv[1:]:
        df = pd.read_csv(filename, dtype={
            'statefp': 'object', 'cnty': 'object', 'tractbna': 'object', 'blckgr': 'object'
        })
        df['GEOID'] = df.apply(lambda x: x['statefp'].zfill(2) + x['cnty'].zfill(3) + x['tractbna'].zfill(6) + x['blckgr'], axis=1)
        df.set_index('GEOID', inplace=True)
        df = df[[c for c in df.columns.values if c not in ['statefp', 'cnty', 'tractbna', 'blckgr']]].copy()
        if bg_df is None:
            bg_df = df
        else:
            bg_df = bg_df.join(df, how='left')
    bg_df.to_csv(sys.stdout)
