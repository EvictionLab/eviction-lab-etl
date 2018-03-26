import sys
import json
import pandas as pd

if __name__ == '__main__':
    df = pd.read_csv(sys.stdin, dtype={'year': 'object'})
    avg_records = df.to_dict(orient='records')
    us_avg = {}
    for r in avg_records:
        year_suffix = r['year'][2:]
        us_avg['er-{}'.format(year_suffix)] = r['eviction-rate']
        us_avg['efr-{}'.format(year_suffix)] = r['eviction-filing-rate']

    json.dump(us_avg, sys.stdout)
