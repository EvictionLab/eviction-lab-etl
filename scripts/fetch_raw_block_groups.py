import os
import sys
import csv
import time
import pandas as pd
import sys
from utils_census import CensusDataStore
from utils_logging import logger

CENSUS_COLS = 'af-am-pop,am-ind-pop,asian-pop,block group,county,hispanic-pop,median-gross-rent,median-household-income,median-property-value,multiple-pop,name,nh-pi-pop,occupied-housing-units,other-pop,population,poverty-pop,rent-burden,renter-occupied-households,state,total-poverty-pop,tract,white-pop,year,GEOID'

if __name__ == '__main__':

    c = CensusDataStore()
    
    if sys.argv[2] == '00':
        df = c.fetchAllBlockGroupData2000(sys.argv[1])
    elif sys.argv[2] == '10':
        df = c.fetchAllBlockGroupData2010(sys.argv[1])
    else:
        raise ValueError('Invalid year suffix supplied')

    if df is None or df.empty:
        logger.warn('Received no census data for block groups in county: ' + sys.argv[1])
        # output header row, but no data
        print(CENSUS_COLS)
        exit()

    if df is not None and 'state' in df.columns.values:
        df['GEOID'] = df['state'].str.zfill(2) + df['county'].str.zfill(
            3) + df['tract'].str.zfill(6) + df['block group']
        df.to_csv(sys.stdout, index=False, quoting=csv.QUOTE_NONNUMERIC)
