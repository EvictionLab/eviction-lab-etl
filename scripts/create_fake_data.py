import sys
import pandas as pd
import random

RANGE_EXTREME = 0.25

# Offsets a value by a random amount
def offset_value (value, low=False):
  offset = random.random() * RANGE_EXTREME
  amount = offset * value
  if low:
    return amount - offset
  return amount + offset

# Add random high / low values for confidence interval
def create_high_low (df, col_name):
  df[col_name + '-low'] = df.apply (lambda row: offset_value(row[col_name], True), axis=1)
  df[col_name + '-high'] = df.apply (lambda row: offset_value(row[col_name]), axis=1)
  return df

if __name__ == '__main__':
  df = pd.read_csv(sys.stdin, dtype={'GEOID': 'object'})
  df = create_high_low(df, 'eviction-filings')
  df = create_high_low(df, 'eviction-filing-rate')
  df = create_high_low(df, 'evictions')
  df = create_high_low(df, 'eviction-rate')
  df.to_csv(sys.stdout, index=False)
