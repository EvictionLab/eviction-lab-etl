CENSUS_API_BASE = 'https://api.census.gov/data/'

END_YEAR = 2017
RANKINGS_MAX_YEAR = 2016

ACS_VAR_MAP = {
    'NAME': 'name',
    'B01003_001E': 'population',
    'B17010_001E': 'total-poverty-pop',
    'B17010_002E': 'poverty-pop',
    'B25064_001E': 'median-gross-rent',
    'B25003_001E': 'occupied-housing-units',
    'B25003_003E': 'renter-occupied-households',
    'B19013_001E': 'median-household-income',
    'B25077_001E': 'median-property-value',
    'B25071_001E': 'rent-burden',
    'B03002_012E': 'hispanic-pop',
    'B03002_003E': 'white-pop',
    'B03002_004E': 'af-am-pop',
    'B03002_005E': 'am-ind-pop',
    'B03002_006E': 'asian-pop',
    'B03002_007E': 'nh-pi-pop',
    'B03002_008E': 'other-pop',
    'B03002_009E': 'multiple-pop'
}

ACS_12_VAR_MAP = {
    'B17010_001E': 'total-poverty-pop',
    'B17010_002E': 'poverty-pop',
    'B25064_001E': 'median-gross-rent',
    'B19013_001E': 'median-household-income',
    'B25077_001E': 'median-property-value',
    'B25071_001E': 'rent-burden'
}

CENSUS_00_SF1_VAR_MAP = {
    'NAME': 'name',
    'P001001': 'population',
    'H003002': 'occupied-housing-units',
    'H004003': 'renter-occupied-households',
    'P008010': 'hispanic-pop',
    'P008003': 'white-pop',
    'P008004': 'af-am-pop',
    'P008005': 'am-ind-pop',
    'P008006': 'asian-pop',
    'P008007': 'nh-pi-pop',
    'P008008': 'other-pop',
    'P008009': 'multiple-pop'
}

CENSUS_00_SF3_VAR_MAP = {
    'NAME': 'name',
    'P087001': 'total-poverty-pop',
    'P087002': 'poverty-pop',
    'H063001': 'median-gross-rent',
    'P053001': 'median-household-income',
    'H076001': 'median-property-value',
    'H070001': 'rent-burden'
}

CENSUS_10_VAR_MAP = {
    'NAME': 'name',
    'P003001': 'population',
    'H004001': 'occupied-housing-units',
    'H004004': 'renter-occupied-households',
    'P004003': 'hispanic-pop',
    'P005003': 'white-pop',
    'P005004': 'af-am-pop',
    'P005005': 'am-ind-pop',
    'P005006': 'asian-pop',
    'P005007': 'nh-pi-pop',
    'P005008': 'other-pop',
    'P005009': 'multiple-pop'
}

COUNT_COLS = [
    'population', 
]

RATE_COLS = [

]

NUMERIC_COLS = COUNT_COLS + RATE_COLS

OUTPUT_COLS = [
    'GEOID', 'name', 'parent-location', 'year', 'population'
]

NUMERIC_OUTPUT_COLS = [
    'population'
]

COLUMN_ORDER = [
    'GEOID',
    'year',
    'name',
    'parent-location',
    'population',

]

INT_COLS = ['imputed', 'subbed', 'low-flag']

COUNTY_CROSSWALK = {
    # 2000
    '02201': {
        'GEOID': '02198',
        'name': 'Prince of Wales-Hyder Census Area',
        'parent-location': 'Alaska'
    },
    '02232': {
        'GEOID': '02105',
        'name': 'Hoonah-Angoon Census Area',
        'parent-location': 'Alaska'
    },
    '02280': {
        'GEOID': '02275',
        'name': 'Wrangell City and Borough',
        'parent-location': 'Alaska'
    },
    # 2010
    '46102': {
        'GEOID': '46113',
        'name': 'Shannon County',
        'parent-location': 'South Dakota'
    },
    '02158': {
        'GEOID': '02270',
        'name': 'Wade Hampton Census Area',
        'parent-location': 'Alaska'
    }
}

ACS_VARS = tuple(ACS_VAR_MAP.keys())
ACS_12_VARS = tuple(ACS_12_VAR_MAP.keys())
CENSUS_00_SF1_VARS = tuple(CENSUS_00_SF1_VAR_MAP.keys())
CENSUS_00_SF3_VARS = tuple(CENSUS_00_SF3_VAR_MAP.keys())
CENSUS_10_VARS = tuple(CENSUS_10_VAR_MAP.keys())
