import sys
import json
from census_data import COUNTY_CROSSWALK

CROSSWALK_GEO = ['counties', 'tracts', 'block-groups']

if __name__ == '__main__':
    if any([g in sys.argv[1] for g in CROSSWALK_GEO]):
        with open(sys.argv[1], 'r') as f:
            geo = json.load(f)
        
        for feat in geo['features']:
            if any([feat['properties']['GEOID'].startswith(g) for g in COUNTY_CROSSWALK]):
                geoid = COUNTY_CROSSWALK.get(
                    [g for g in COUNTY_CROSSWALK if feat['properties']['GEOID'].startswith(g)][0]
                )
                feat['properties']['GEOID'] = geoid['GEOID'] + feat['properties']['GEOID'][5:]
        
        with open(sys.argv[1], 'w') as f:
            json.dump(geo, f)