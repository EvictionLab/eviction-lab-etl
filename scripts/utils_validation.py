import sys
import time
import numpy as np
import pandas as pd
from utils_logging import create_logger

log_name = 'merge_' + str(time.time()).split('.')[0]
logger = create_logger(log_name, console_lvl='INFO', file_lvl='DEBUG')

# Checks if all items in the right data frame will merge into the left
def is_clean_left_merge(df_left, df_right, col):
    set1 = set(df_left[col])
    set2 = set(df_right[col])
    if set1.issubset(set2):
        return True
    return False

# Gets stats on left merge
def get_left_merge_stats(df_left, df_right, **kwargs):

    if 'on' in kwargs:
        cols = kwargs.get('on')
        if isinstance(cols, str):
            # if single column is provided to merge on, set it as the key
            left_key = cols
            right_key = cols
        elif isinstance(cols,(list,)):
            # if multiple columns create a merge key by joining all provided columns
            left_key = right_key = 'merge_key'
            df_left = df_left[cols].copy()
            df_right = df_right[cols].copy()
            df_left[left_key] = df_left[cols].apply(lambda row: ''.join(row.values.astype(str)), axis=1)
            df_right[right_key] = df_right[cols].apply(lambda row: ''.join(row.values.astype(str)), axis=1)
        else:
            raise ValueError('column name(s) for merge stats must be a string or list of strings')
    
    if 'left_on' in kwargs and 'right_on' in kwargs:
        left_key = kwargs.get('left_on')
        right_key = kwargs.get('right_on')

    set1 = set(df_left[left_key])
    set2 = set(df_right[right_key])

    matchedEntries = set2.intersection(set1)
    unmatchedEntries = set2.difference(set1)

    results = {
        'df1_entries': len(set1),
        'df2_entries': len(set2),
        'matched': len(matchedEntries),
        'unmatched': len(unmatchedEntries),
        'unmatchedEntries': list(unmatchedEntries)
    }

    return results

# Writes provided merge stats to the logger
def log_merge_stats(name, stats):
    matched = stats['matched']
    unmatched = stats['unmatchedEntries']
    total = stats['df2_entries']
    percent = (matched/total)*100
    
    if len(unmatched) > 0:
        logger.warn(name + ': merged ' + str(matched) + ' of ' + str(total) + ' rows ('+ str(percent) + '%)')
        if len(unmatched) > 1000:
            unmatched = unmatched[:1000]
        logger.warn(name + ': ' + str(stats['unmatched']) + ' unmatched rows: ' + ','.join(str(e) for e in unmatched))
    else:
        logger.info(name + ': merge successful')

# Performs a data frame merge with the given data frames, keys, and join method.
# Logs the statistics of the merge to console and file
def merge_with_stats(name, df_left, df_right, **kwargs):
    merge_stats = get_left_merge_stats(df_left, df_right, **kwargs)
    log_merge_stats(name, merge_stats)
    return df_left.merge(df_right, **kwargs)

