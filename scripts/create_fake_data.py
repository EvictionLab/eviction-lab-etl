import sys
import pandas as pd
import random

MARGIN_MIN = 5
MARGIN_MAX = 10

# randomly return 1 or -1
def random_pos_neg ():
  rand = random.random()
  if rand > 0.5:
    return 1
  return -1

# Offsets a value by a random amount
def offset_value (value, low=False, base_margin=0):
  direction = random_pos_neg()
  offset = (value * base_margin) * (random.randrange(5, 10) / 100) # create slight difference between high and low
  amount = (value * base_margin) + (direction * offset)
  if low:
    return value - amount
  return value + amount

# Add random high / low values for confidence interval
def create_high_low (df, col_name):
  base_margin = random.randrange(MARGIN_MIN, MARGIN_MAX) / 100 # get a base margin of error value
  df[col_name + '-low'] = df.apply (lambda row: offset_value(row[col_name], True, base_margin), axis=1)
  df[col_name + '-high'] = df.apply (lambda row: offset_value(row[col_name], False, base_margin), axis=1)
  return df

if __name__ == '__main__':
  df = pd.read_csv(sys.stdin, dtype={'GEOID': 'object'})
  df = create_high_low(df, 'eviction-filings')
  df = create_high_low(df, 'eviction-filing-rate')
  df = create_high_low(df, 'evictions')
  df = create_high_low(df, 'eviction-rate')
  df.to_csv(sys.stdout, index=False)
