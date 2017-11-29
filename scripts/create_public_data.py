import os
import sys
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
PUBLIC_DATA_DIR = os.path.join(BASE_DIR, 'data', 'public_data')

GEO_TYPE_LEN = {
    'states': 2,
    'counties': 5,
    'cities': 7,
    'tracts': 11,
    'block-groups': 12
}


if __name__ == '__main__':
    state_fips_df = pd.read_csv(os.path.join(BASE_DIR, 'conf', 'state_fips.csv'), dtype={'fips': 'object'})
    state_fips = {s[0]: s[1] for s in zip(state_fips_df.fips, state_fips_df.usps)}

    data_df = pd.read_csv(os.path.join(BASE_DIR, 'data', 'us.csv'), dtype={
        'GEOID': 'object', 'name': 'object', 'parent-location': 'object'
    })

    if not os.path.isdir(os.path.join(PUBLIC_DATA_DIR, 'us')):
        os.mkdir(os.path.join(PUBLIC_DATA_DIR, 'us'))
    data_df.to_csv(os.path.join(PUBLIC_DATA_DIR, 'us', 'all.csv'), index=False)
    for geo, geo_len in GEO_TYPE_LEN.items():
        data_df.loc[data_df['GEOID'].str.len() == geo_len].to_csv(
            os.path.join(PUBLIC_DATA_DIR, 'us', '{}.csv'.format(geo)), index=False
        )

    for fips, state in state_fips.items():
        state_str = state.lower()
        if not os.path.isdir(os.path.join(PUBLIC_DATA_DIR, state_str)):
            os.mkdir(os.path.join(PUBLIC_DATA_DIR, state_str))
        data_df.loc[data_df['GEOID'].str.startswith(fips)].to_csv(
            os.path.join(PUBLIC_DATA_DIR, state_str, 'all.csv'),
            index=False
        )

        for geo, geo_len in GEO_TYPE_LEN.items():
            data_df.loc[
                (data_df['GEOID'].str.len() == geo_len) &
                (data_df['GEOID'].str.startswith(fips))
            ].to_csv(
                os.path.join(PUBLIC_DATA_DIR, state_str, '{}.csv'.format(geo)),
                index=False
            )
