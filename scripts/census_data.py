CENSUS_API_BASE = 'https://api.census.gov/data/'

ACS_VAR_MAP = {
    'NAME': 'name',
    'B01003_001E': 'population',
    'B17001_002E': 'poverty-pop',
    'B25010_001E': 'average-household-size',
    'B25111_001E': 'median-gross-rent',
    'B25001_001E': 'housing-units',
    'B25002_003E': 'vacant-housing-units',
    'B25003_001E': 'occupied-housing-units',
    'B25003_003E': 'renter-occupied-households',
    'B19013_001E': 'median-household-income',
    'B25077_001E': 'median-property-value',
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
    'B17001_002E': 'poverty-pop',
    'B25111_001E': 'median-gross-rent',
    'B19013_001E': 'median-household-income',
    'B25077_001E': 'median-property-value'
}

CENSUS_90_BG_VAR_MAP = {
    'p0010001': 'population',
    'h0010001': 'housing-units',
    'h0040002': 'vacant-housing-units',
    'h0040001': 'occupied-housing-units',
    'h0080002': 'renter-occupied-households',
    'h061a001': 'median-property-value',
    # Average household size?
    'p0080001': 'hispanic-pop',
    'p0110001': 'white-pop',
    'p0110002': 'af-am-pop',
    'p0110003': 'am-ind-pop',
    # Combines Asian and Native Hawaiian, treating as nh-pi-pop
    'p0110004': 'nh-pi-pop',
    'p0110005': 'other-pop'
}

CENSUS_90_SF1_VAR_MAP = {
    'ANPSADPI': 'name',
    'P0010001': 'population',
    # Can't find one single summary stat for overall poverty
    # 'H043A001': 'median-gross-rent',
    'H0010001': 'housing-units',
    'H0020002': 'vacant-housing-units',
    'H0020001': 'occupied-housing-units',
    'H0030002': 'renter-occupied-households',
    # 'P080A001': 'median-household-income',
    # 'H061A001': 'median-property-value',
    # Average household size?
    'P0080001': 'hispanic-pop',
    'P0100001': 'white-pop',
    'P0100002': 'af-am-pop',
    'P0100003': 'am-ind-pop',
    # Cobines Asian and Native Hawaiian, treating as nh-pi-pop
    'P0100004': 'asian-pop',
    'P0100005': 'other-pop'
}

CENSUS_90_SF3_VAR_MAP = {
    'ANPSADPI': 'name',
    # 'P0010001': 'population',
    # Can't find one single summary stat for overall poverty
    'H043A001': 'median-gross-rent',
    # 'H0010001': 'housing-units',
    # 'H0040002': 'vacant-housing-units',
    # 'H0040001': 'occupied-housing-units',
    # 'H0080002': 'renter-occupied-households',
    'P080A001': 'median-household-income',
    'H061A001': 'median-property-value',
    # Average household size?
    # 'P0100001': 'hispanic-pop',
    # 'P0120001': 'white-pop',
    # 'P0120002': 'af-am-pop',
    # 'P0120003': 'am-ind-pop',
    # # Combines Asian and Native Hawaiian, treating as nh-pi-pop
    # 'P0120004': 'asian-pop',
    # 'P0120005': 'other-pop'
}

CENSUS_00_SF1_VAR_MAP = {
    'NAME': 'name',
    'P001001': 'population',
    # total-poverty-pop is "Population for whom poverty status is determined"
    # 'P087001': 'total-poverty-pop',
    # 'P087002': 'poverty-pop',
    'P017001': 'average-household-size',
    # 'H063001': 'median-gross-rent',
    'H003001': 'housing-units',
    'H003003': 'vacant-housing-units',
    'H003002': 'occupied-housing-units',
    'H004003': 'renter-occupied-households',
    # 'P053001': 'median-household-income',
    # 'H076001': 'median-property-value',
    'P008010': 'hispanic-pop',
    'P008003': 'white-pop',
    'P008004': 'af-am-pop',
    'P008005': 'am-ind-pop',
    'P008006': 'asian-pop',
    'P008007': 'nh-pi-pop',
    'P008008': 'other-pop',
    'P008009': 'multiple-pop',
    # 'P007010': 'hispanic-pop',
    # 'P007011': 'white-pop',
    # 'P007012': 'af-am-pop',
    # 'P007013': 'am-ind-pop',
    # 'P007014': 'asian-pop',
    # 'P007015': 'nh-pi-pop',
    # 'P007016': 'other-pop',
    # 'P007017': 'multiple-pop'
}

CENSUS_00_SF3_VAR_MAP = {
    'NAME': 'name',
    # 'P001001': 'population',
    # total-poverty-pop is "Population for whom poverty status is determined"
    'P087001': 'total-poverty-pop',
    'P087002': 'poverty-pop',
    # 'P017001': 'average-household-size',
    'H063001': 'median-gross-rent',
    # 'H001001': 'housing-units',
    # 'H002003': 'vacant-housing-units',
    # 'H002002': 'occupied-housing-units',
    # 'H007003': 'renter-occupied-households',
    'P053001': 'median-household-income',
    'H076001': 'median-property-value',
    # 'P007010': 'hispanic-pop',
    # 'P007011': 'white-pop',
    # 'P007012': 'af-am-pop',
    # 'P007013': 'am-ind-pop',
    # 'P007014': 'asian-pop',
    # 'P007015': 'nh-pi-pop',
    # 'P007016': 'other-pop',
    # 'P007017': 'multiple-pop'
}

CENSUS_10_VAR_MAP = {
    'NAME': 'name',
    'P0030001': 'population',
    'H00010001': 'housing-units',
    'H0030003': 'vacant-housing-units',
    'H0040001': 'occupied-housing-units',
    'H0040004': 'renter-occupied-households',
    'H0120001': 'average-household-size',
    'P0040003': 'hispanic-pop',
    'P0050003': 'white-pop',
    'P0050004': 'af-am-pop',
    'P0050005': 'am-ind-pop',
    'P0050006': 'asian-pop',
    'P0050007': 'nh-pi-pop',
    'P0050008': 'other-pop',
    'P0050009': 'multiple-pop'
}

# TODO: Add int cols to compress size
NUMERIC_COLS = [
    'population',
    'poverty-pop',
    'average-household-size',
    'median-gross-rent',
    'housing-units',
    'vacant-housing-units',
    'occupied-housing-units',
    'renter-occupied-households',
    'median-household-income',
    'median-property-value',
    'hispanic-pop',
    'white-pop',
    'af-am-pop',
    'am-ind-pop',
    'asian-pop',
    'nh-pi-pop',
    'other-pop',
    'multiple-pop'
]

OUTPUT_COLS = [
    'GEOID',
    'name',
    'parent-location',
    'year',
    'population',
    'poverty-rate',
    'average-household-size',
    'renter-occupied-households',
    'pct-renter-occupied',
    'median-gross-rent',
    'median-household-income',
    'median-property-value',
    'pct-white',
    'pct-af-am',
    'pct-hispanic',
    'pct-am-ind',
    'pct-asian',
    'pct-nh-pi',
    'pct-multiple',
    'pct-other'
]

ACS_VARS = tuple(ACS_VAR_MAP.keys())
ACS_12_VARS = tuple(ACS_12_VAR_MAP.keys())
CENSUS_90_SF1_VARS = tuple(CENSUS_90_SF1_VAR_MAP.keys())
CENSUS_90_SF3_VARS = tuple(CENSUS_90_SF3_VAR_MAP.keys())
CENSUS_00_SF1_VARS = tuple(CENSUS_00_SF1_VAR_MAP.keys())
CENSUS_00_SF3_VARS = tuple(CENSUS_00_SF3_VAR_MAP.keys())
CENSUS_10_VARS = tuple(CENSUS_10_VAR_MAP.keys())