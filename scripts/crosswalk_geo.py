import csv
import sys
import pandas as pd
from census_data import COUNTY_CROSSWALK


if __name__ == '__main__':
    geo = sys.argv[1]
    df = pd.read_csv(sys.stdin, dtype={'GEOID': 'object', 'name': 'object', 'parent-location': 'object'})

    if geo == 'counties':
        for k, v in COUNTY_CROSSWALK.items():
            df.loc[df['GEOID'] == k, ['GEOID', 'name', 'parent-location']] = [v['GEOID'], v['name'], v['parent-location']]
    elif geo in ['tracts', 'block-groups']:
        for k, v in COUNTY_CROSSWALK.items():
            df.loc[df['GEOID'].str.startswith(k), ['GEOID', 'parent-location']] = [
                v['GEOID'] + df.loc[df['GEOID'].str.startswith(k), 'GEOID'].str.slice(5),
                v['name'] + ', ' + v['parent-location']
            ]

    df.to_csv(sys.stdout, index=False, quoting=csv.QUOTE_NONNUMERIC)
