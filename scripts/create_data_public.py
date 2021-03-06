import os
import boto3
import numpy as np
import pandas as pd
import geopandas as gpd
from data_constants import INT_COLS
from shapely import geometry

upcast_dispatch = {geometry.Point: geometry.MultiPoint, 
                   geometry.LineString: geometry.MultiLineString, 
                   geometry.Polygon: geometry.MultiPolygon}

def maybe_cast_to_multigeometry(geom):
    caster = upcast_dispatch.get(type(geom), lambda x: x[0])
    return caster([geom])

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
PUBLIC_DATA_DIR = os.path.join(BASE_DIR, 'data', 'public')
BUCKET = os.getenv('S3_DATA_DOWNLOADS_BUCKET')
s3 = boto3.resource('s3')
client = boto3.client('s3')

GEO_TYPE_LEN = {
    'states': 2,
    'counties': 5,
    'cities': 7,
    'tracts': 11,
    'block-groups': 12
}


def create_state_csvs(df, fips, state):
    if not os.path.isdir(os.path.join(PUBLIC_DATA_DIR, state)):
        os.mkdir(os.path.join(PUBLIC_DATA_DIR, state))

    print('Writing full CSV data for {}'.format(state))
    df.loc[df['GEOID'].str.startswith(fips)].to_csv(
        os.path.join(PUBLIC_DATA_DIR, state, 'all.csv'), index=False)

    for geo, geo_len in GEO_TYPE_LEN.items():
        print('Writing CSV data for {} {}'.format(state, geo))
        filename = os.path.join(PUBLIC_DATA_DIR, state, '{}.csv'.format(geo))
        df.loc[(df['GEOID'].str.len() == geo_len)
               & (df['GEOID'].str.startswith(fips))].to_csv(
                   filename, index=False)
        client.upload_file(filename, BUCKET, '{}/{}.csv'.format(state, geo))
        os.remove(filename)


def create_state_geojson(df, fips, state):
    for geo, geo_df in geo_df_map.items():
        print('Writing GeoJSON for {} {}'.format(state, geo))
        filename = os.path.join(PUBLIC_DATA_DIR, state,
                                '{}.geojson'.format(geo))
        geo_df.loc[geo_df['GEOID'].str.startswith(fips)].to_file(
            filename, driver='GeoJSON')
        client.upload_file(filename, BUCKET, '{}/{}.geojson'.format(
            state, geo))
        os.remove(filename)


if __name__ == '__main__':
    state_fips_df = pd.read_csv(
        os.path.join(BASE_DIR, 'conf', 'state_fips.csv'),
        dtype={'fips': 'object'})
    state_fips = {
        s[0]: s[1].upper()
        for s in zip(state_fips_df.fips, state_fips_df.usps)
    }

    print('Reading United States CSV data')
    data_df = pd.read_csv(
        os.path.join(PUBLIC_DATA_DIR, 'US', 'all.csv'),
        dtype={
            'GEOID': 'object',
            'name': 'object',
            'parent-location': 'object'
        })
    data_df.replace([np.inf, -np.inf, -1.0], np.nan, inplace=True)

    # Convert int cols to int
    data_df[INT_COLS] = data_df[INT_COLS].fillna(0).astype(int)

    geo_df_map = {}
    for k, v in GEO_TYPE_LEN.items():
        geo_df = gpd.read_file(
            os.path.join(BASE_DIR, 'census', '{}.geojson'.format(k)),
            driver='GeoJSON')
        attr_df = pd.read_csv(
            os.path.join(BASE_DIR, 'grouped_public', '{}.csv'.format(k)),
            dtype={
                'GEOID': 'object',
                'n': 'object',
                'pl': 'object'
            })
        geo_df = geo_df.merge(attr_df, on='GEOID', how='left')
        geo_df.replace([np.inf, -np.inf, -1.0], np.nan, inplace=True)
        print('Writing United States GeoJSON file for {}'.format(k))
        # Cast to multipolygon to avoid errors
        # https://github.com/geopandas/geopandas/issues/834
        geo_df['geometry'] = geo_df['geometry'].apply(maybe_cast_to_multigeometry)
        geo_df.to_file(
            os.path.join(PUBLIC_DATA_DIR, 'US', '{}.geojson'.format(k)),
            driver='GeoJSON')
        geo_df_map[k] = geo_df

    for fips, state in state_fips.items():
        create_state_csvs(data_df, fips, state)
        create_state_geojson(geo_df_map, fips, state)
