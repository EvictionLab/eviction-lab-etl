"""
Maps 2000 data to 2010 geography

Input
------
Takes the stdout of `fetch_raw_census_data.py` as stdin

Arguments
----------
argv[1] : str
    The geography level to create weights for (block-groups or tracts)
argv[2] : str
    The file path to the file that contains the crosswalk and weights for
    converting 2000 data to 2010 geography

Outputs
-------
str
    a string of CSV data containing all of the 2000 census data
    crosswalked so it fits in 2010 geography

"""
import numpy as np # added 9/23/19
import sys
import csv
import pandas as pd
import os
from utils_validation import (merge_with_stats, logger)
from utils_census import (create_tract_name, get_block_group_crosswalk_df,
                        get_tract_crosswalk_09_10_df)
# from data_constants import (COUNT_COLS, RATE_COLS) # not needed when piping in own columns as arguement 

def changeACS09toCensus10(df, map_df, fromField, toField):
    # get a map of columns `fromField` : `toField`
    bg_dict = pd.Series(map_df[toField].values, index=map_df[fromField]).to_dict()

    # loop through the map and update the data frame if needed
    for fromBg, toBg in bg_dict.items():
        df.loc[(df['GEOID'] == fromBg), 'GEOID'] = toBg
    return df

if __name__ == '__main__':
    # read output from `fetch_raw_census_data.py` into data frame
    data_df = pd.read_csv(
        sys.stdin,
        dtype={
            'GEOID': 'object',
            'name': 'object',
            'parent-location': 'object'
        })
    # read in weights output from `create_00_weights.py`
    weight_df = pd.read_csv(
        sys.argv[2], dtype={
            'GEOID00': 'object',
            'GEOID10': 'object'
        })

    # add ACS 09 -> 10 rows to weights dataframe with weight of 1
    if sys.argv[1] == 'block-groups':
        acs_09_10_cw_df = get_block_group_crosswalk_df('changes_09acs_to_10cen.csv')
        acs_09_10_cw_df.drop(['county', 'cofips'], axis=1, inplace=True)
        acs_09_10_cw_df.rename(columns={
            'bkg09': 'GEOID09',
            'bkg10': 'GEOID10'
        }, inplace=True)
    if sys.argv[1] == 'tracts':
        acs_09_10_cw_df = get_tract_crosswalk_09_10_df()
        acs_09_10_cw_df.rename(columns={
            'trt09': 'GEOID09',
            'trt10': 'GEOID10'
        }, inplace=True)
    # create count, rate, and other cols from csv argument 
    COUNT_COLS = []
    RATE_COLS = []
    other_cols = []
    col_list = list(data_df.columns)
    # read column list csv as dictionary
    with open(sys.argv[3], mode = 'r') as infile:
        reader = csv.reader(infile)
        mydict = {rows[0]:rows[1] for rows in reader}
    for col in col_list:
        if col in mydict.keys():
            if mydict[col] == 'count':
                COUNT_COLS.append(col)
            elif mydict[col] == 'rate':
                RATE_COLS.append(col)
            else:
                other_cols.append(col)
    # filter count and rate col list based on if they are in the list of columns

    RATE_COLS_filtered = [col for col in RATE_COLS if col in col_list]
    COUNT_COLS_filtered = [col for col in COUNT_COLS if col in col_list]

    # create base,hh,unit, and other cols from csv argument
    BASE_COLS = []
    HH_COLS = []
    UNIT_COLS = []
    # read column list csv as dictionary
    with open(sys.argv[4], mode = 'r') as infile:
        reader = csv.reader(infile)
        mydict = {rows[0]:rows[1] for rows in reader}
    for col in col_list:
        if col in mydict.keys():
            if mydict[col] == 'base':
                BASE_COLS.append(col)
            elif mydict[col] == 'hh':
                HH_COLS.append(col)
            elif mydict[col] == 'unit':
                UNIT_COLS.append(col)
            else:
                other_cols.append(col)
    # filter count and rate col list based on if they are in the list of columns
    BASE_COLS_filtered = [col for col in BASE_COLS if col in col_list]
    HH_COLS_filtered = [col for col in HH_COLS if col in col_list]
    UNIT_COLS_filtered = [col for col in UNIT_COLS if col in col_list]
    # remove the rows from ACS 2009 that are already in 2010 geography
    # because they are not part of the crosswalk
    entries = acs_09_10_cw_df['GEOID09'].tolist()
    acs_10_entries_df = data_df[
        data_df['GEOID'].isin(entries) & data_df['year'].isin([2005,2006,2007,2008,2009])].copy()
    acs_10_entries_df.drop(['name', 'parent-location'], axis=1, inplace=True)
    cw_df = data_df.drop(data_df[
        data_df['GEOID'].isin(entries) & data_df['year'].isin([2005,2006,2007,2008,2009])].index)

    del data_df

    conf_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'conf')

    # rename tracts that changed from 00 -> 09

    with open(str(os.path.join(conf_dir, 'changes_09acs_to_00cen_tract.csv'))) as rename_file:
        reader = csv.reader(rename_file)
        rename_dict = {rows[1]:rows[2] for rows in reader}
    # map values using rename dict. fill non mapped values w/ original value
    cw_df['GEOID'] = np.where(cw_df['year'].isin([2005,2006,2007,2008,2009]), cw_df['GEOID'].map(rename_dict).fillna(cw_df['GEOID']), cw_df['GEOID'])

    # split tracks in Bloomfield, CO
    cw_df['dup'] = np.where(cw_df.groupby(['GEOID','year'])['GEOID'].transform('count')==1, 0, cw_df.groupby(['GEOID','year']).cumcount()+1)
    cw_df['htot_old'] = cw_df['htot']
    def count_cols_dupes(column_, dataframe):
        dataframe[column_] = np.where(dataframe['dup']>0, dataframe.groupby(['GEOID','year'])[column_].transform('sum'), dataframe[column_])
    def rate_cols_dupes(column_, dataframe):
        w_col = 'w_' + column_
        dataframe['flag'] = np.where((dataframe[column_].isna()),1,0)
        dataframe['t_flag'] = np.where(dataframe['dup']>0, dataframe.groupby(['GEOID','year'])['flag'].transform('sum'), 0)
        dataframe['cweight'] = np.where(dataframe['t_flag']==0, dataframe['test_weight'], np.nan)
        dataframe['cweight'] = np.where((dataframe['t_flag']==1) & (dataframe['flag']==0),1 ,dataframe['cweight'])
        dataframe['cweight'] = np.where((dataframe['t_flag']==1) & (dataframe['flag']==1),0 ,dataframe['cweight'])
        dataframe[w_col] = dataframe['cweight']*dataframe[column_]
        dataframe[column_] = np.where(dataframe['dup']>0, dataframe.groupby(['GEOID','year'])[w_col].transform('sum'), dataframe[column_])
        dataframe.drop(['flag', w_col, 't_flag', 'cweight'], axis=1, inplace=True)

    for column in COUNT_COLS_filtered:
        count_cols_dupes(column, cw_df)
    cw_df['test_weight'] = cw_df['htot_old']/cw_df['htot']
    for column in RATE_COLS_filtered:
        rate_cols_dupes(column, cw_df)
    cw_df = cw_df[cw_df['dup']!=2]

    # merge the census data with the weights for each GEOID
    log_label = sys.argv[1]+' weights <- data'
    output_df = merge_with_stats(
        log_label, weight_df, cw_df, left_on='GEOID00', right_on='GEOID', how='left', indicator=True)
    del weight_df
    output_df = output_df[output_df['_merge'] != 'left_only']  # drop merges added 10/04/19
    # create data frame with unique GEOID10 and associated name and parent-location
    context_df = output_df[['GEOID00', 'GEOID10', 'name', 'parent-location', 'state','year']].copy()  # added state and NAME columns to context_df 7/25/19
    # drop rows where GEOID00 county != GEOID10 county
    context_df.drop(
        context_df[context_df['GEOID00'].str[:5] != context_df['GEOID10'].str[:5]].index, inplace=True)
    context_df.drop(['GEOID00'], axis=1, inplace=True)
    context_df.drop_duplicates(subset=['GEOID10','year'], inplace=True)

    output_df['count_'] = output_df.groupby(['year','GEOID00'])['GEOID00'].transform('count')
    # create new weight variables to be in accordance w/ ashley's script
    output_df['wtot_pop'] = output_df.groupby(['GEOID00', 'year'])['count_weight'].transform('sum')
    output_df['wtot_hh'] = output_df.groupby(['GEOID00', 'year'])['rate_weight'].transform('sum')
    output_df['wtot_units'] = output_df.groupby(['GEOID00', 'year'])['unit_weight'].transform('sum')

    def base_multiply(column_):
        newCol = 'wt_' + column_
        output_df[newCol] = np.where(output_df['wtot_pop']!=0, output_df['count_weight']*output_df[column_], np.nan)
        output_df[newCol] = np.where(output_df[column_]==0, 0, output_df[newCol])
        output_df[newCol] = np.where((output_df['wtot_pop']==0) & (output_df['count_'] ==1), output_df[column_], output_df[newCol])
        output_df[newCol] = np.where((output_df['wtot_pop']==0) & (output_df['count_'] >1),output_df[column_]*(1/output_df['count_']), output_df[newCol])
        output_df.drop(columns=[column_], inplace=True)
        output_df.rename(columns={newCol:column_}, inplace=True)

    def hh_multiple(column_):
        newCol = 'wt_' + column_
        output_df[newCol] = np.where(output_df['wtot_hh']!=0, output_df['rate_weight']*output_df[column_], np.nan)
        output_df[newCol] = np.where(output_df[column_]==0, 0, output_df[newCol])
        output_df[newCol] = np.where((output_df['wtot_hh']==0) & (output_df['count_'] ==1), output_df[column_], output_df[newCol])
        output_df[newCol] = np.where((output_df['wtot_hh']==0) & (output_df['count_'] >1),output_df[column_]*(1/output_df['count_']), output_df[newCol])
        output_df.drop(columns=[column_], inplace=True)
        output_df.rename(columns={newCol:column_}, inplace=True)

    def unit_multiply(column_):
        newCol = 'wt_' + column_
        output_df[newCol] = np.where(output_df['wtot_units']!=0, output_df['unit_weight']*output_df[column_], np.nan)
        output_df[newCol] = np.where(output_df[column_]==0, 0, output_df[newCol])
        output_df[newCol] = np.where((output_df['wtot_units']==0) & (output_df['count_'] ==1), output_df[column_], output_df[newCol])
        output_df[newCol] = np.where((output_df['wtot_units']==0) & (output_df['count_'] >1),output_df[column_]*(1/output_df['count_']), output_df[newCol])
        output_df.drop(columns=[column_], inplace=True)
        output_df.rename(columns={newCol:column_}, inplace=True)

    def rate_multiply(column_):
        output_df['htot_'] = np.where(output_df[column_].notnull(), output_df['htot'],0)
        output_df['htot2'] = output_df.groupby(['year', 'GEOID10'])['htot_'].transform('sum')
        output_df['hweight'] = output_df['htot']/output_df['htot2']
        output_df['hweight'] = np.where((output_df['htot']==0) & (output_df['htot2']==0), 0, output_df['hweight'])
        newCol = 'wt_' + column_
        output_df[newCol] = output_df[column_]*output_df['hweight']
        output_df.drop(columns=[column_,'hweight','htot2','htot_'], inplace=True)
        output_df.rename(columns={newCol:column_}, inplace=True)
    
    # added loop to apply new multiply functiuons 9/23/19
    for column in BASE_COLS_filtered:
        base_multiply(column)

    for column in HH_COLS_filtered:
        hh_multiple(column)

    for column in UNIT_COLS_filtered:
        unit_multiply(column)

    for column_ in RATE_COLS_filtered:
        rate_multiply(column_)

    # sum all values together based on the 2010 geography identifier
    output_df = pd.DataFrame(
        output_df.groupby(['GEOID10',
                           'year'])[COUNT_COLS_filtered + RATE_COLS_filtered].sum()).reset_index()

    # overwrite the 2000 GEOID to the 2010 GEOID
    output_df.rename(columns={'GEOID10': 'GEOID'}, inplace=True)
    # apply ACS 2009 -> Census 2010 changes, then concat result to the data
    acs_10_entries_df = changeACS09toCensus10(acs_10_entries_df, acs_09_10_cw_df, 'GEOID09', 'GEOID10')
    output_df = pd.concat([acs_10_entries_df, output_df])

    # clean up duplicates generated from the concatenation
    output_df['old_htot'] = output_df['htot']
    output_df['dup'] = np.where(output_df.groupby(['GEOID','year'])['GEOID'].transform('count')==1, 0, output_df.groupby(['GEOID','year']).cumcount()+1)
    for col in COUNT_COLS_filtered:
        count_cols_dupes(col, output_df)
    output_df['test_weight'] = output_df['old_htot']/output_df['htot']
    for col in RATE_COLS_filtered:
        rate_cols_dupes(col, output_df)
    output_df = output_df[output_df['dup']!=2]
    # merge in the name and parent-locationt-location for all GEOIDs
    # somewhere here there was an issue where output df had a blank state and NAME column. Unclear why
    output_df = merge_with_stats(
        'context_now', output_df, context_df, left_on=['GEOID','year'], right_on=['GEOID10','year'], how='left')
    # create the name attribute for tracts and block groups
    if sys.argv[1] == 'tracts':
        output_df['name'] = output_df['GEOID'].str.slice(5).apply(
            create_tract_name)
    elif sys.argv[1] == 'block-groups':
        output_df['name'] = output_df['GEOID'].str.slice(5, -1).apply(
            create_tract_name) + '.' + output_df['GEOID'].str.slice(-1)
    else:
        raise ValueError('Invalid geography string supplied')

    # output to stdout
    # clean up output before exporting
    output_df['state'] = output_df['state_x'].map(str) + output_df['state_y'].map(str)  # merge the two state columns into one 7/27/19
    output_df['state'] = output_df['state'].str.extract(r'([A-Z]{2})')  # extract only the two letter abbreviation from concatenated column 7/27/19
    # drop not needed columns
    output_df.drop(columns = ['state_x', 'state_y', 'dup','test_weight',
         'old_htot'
        ], inplace=True) 
    # appennd empty tract
    if 2009 in output_df['year'].unique():
        empty_tract = pd.DataFrame(dict(zip(list(output_df.columns),int(output_df.shape[1])*[[0]])))
        empty_tract['GEOID'] = "24009990100"
        empty_tract = pd.concat([empty_tract]*5)
        empty_tract['year'] = range(2005,2010)
        output_df = pd.concat([output_df, empty_tract])
    output_df = output_df.sort_index(axis = 1)
    # output to stdout
    output_df.to_csv(sys.stdout, index=False, quoting=csv.QUOTE_NONNUMERIC)
