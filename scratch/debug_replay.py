import os, sys, pandas as pd
from pitwall.engine import replay

data_path = os.path.join('data','processed','9558','laps.parquet')
session_df = pd.read_parquet(data_path)
print('Loaded rows', len(session_df))
print('Drivers unique count', session_df['driver_number'].nunique())
# pick a driver present
target_driver = int(session_df['driver_number'].unique()[0])
print('Target driver', target_driver)
race_length = int(session_df['lap_number'].max())
print('Race length', race_length)
# run replay causal
result = replay(session_df, target_driver=target_driver, decision_lap=20, track_mode='causal', race_length=race_length)
print('Summary keys', result.summary.keys())
print('Final cumulative time', result.summary.get('final_cumulative_time'))
print('Projected classification sample')
# get projected classification from backend service? Not needed here
print(result.laps_table.tail())

