import numpy as np # added 9/23/19
import sys
import csv
import pandas as pd
import os
from utils_validation import (merge_with_stats, logger)
from utils_census import (create_tract_name, get_block_group_crosswalk_df,
                        get_tract_crosswalk_09_10_df)

if __name__ == '__main__':
    # read output from `fetch_raw_census_data.py` into data frame
    data_df = pd.read_csv(
        sys.stdin,
        dtype={
            'GEOID': 'object',
            'name': 'object',
            'parent-location': 'object'
        })
    conf_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'conf')

# rename tracts that changed from 10 -> 15
    with open(str(os.path.join(conf_dir, 'changes_15acs_10cen_tract.csv'))) as rename_file:
        reader = csv.reader(rename_file)
        rename_dict_15_10 = {rows[2]:rows[1] for rows in reader}
    # rename tracts that changed from 10 -> 12

    with open(str(os.path.join(conf_dir, 'changes_12acs_10cen_tract.csv'))) as rename_file:
        reader = csv.reader(rename_file)
        rename_dict_12_10 = {rows[2]:rows[1] for rows in reader}

    data_df['GEOID'] = np.where(data_df['year'].isin([2012]), data_df['GEOID'].map(rename_dict_12_10).fillna(data_df['GEOID']), data_df['GEOID'])
    data_df['GEOID'] = np.where(data_df['year'].isin([2011, 2013, 2014, 2015, 2016]), data_df['GEOID'].map(rename_dict_15_10).fillna(data_df['GEOID']), data_df['GEOID'])
    data_df['GEOID10'] = data_df['GEOID']
    data_df = data_df.sort_index(axis=1)
    if 2011 in data_df['year'].unique():
        empty_tract = pd.DataFrame(dict(zip(list(data_df.columns),int(data_df.shape[1])*[[0]])))
        empty_tract['GEOID'] = "36085008900"
        empty_tract = pd.concat([empty_tract]*6)
        empty_tract['year'] = range(2011,2017)
        data_df = pd.concat([data_df, empty_tract])
    # data_df.drop(["Unnamed: 0"], inplace=True)
    data_df.to_csv(sys.stdout, index=False, quoting=csv.QUOTE_NONNUMERIC)