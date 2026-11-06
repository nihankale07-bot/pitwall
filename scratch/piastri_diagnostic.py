import sys
import importlib
import pandas as pd

def print_header(msg):
    print(f"=== {msg} ===")

# 1. Python version and executable
print_header('Python version')
print(sys.version)
print_header('Executable')
print(sys.executable)

# 2. Dependency check
print_header('Dependency versions')
try:
    pandas_mod = importlib.import_module('pandas')
    print('pandas:', pandas_mod.__version__)
except Exception as e:
    print('pandas import error:', e)
try:
    pyarrow_mod = importlib.import_module('pyarrow')
    print('pyarrow:', pyarrow_mod.__version__)
except Exception as e:
    print('pyarrow import error:', e)

# 3. Load core laps data
laps_path = r'C:\\Users\\Nihan\\.vscode\\pitwall\\data\\processed\\9558\\laps.parquet'
print_header('Loading laps.parquet')
try:
    df = pd.read_parquet(laps_path)
    print('Laps columns:', list(df.columns))
    print('Laps dtypes:')
    print(df.dtypes)
except Exception as e:
    print('Error loading laps.parquet:', e)
    sys.exit(1)

# 4. Load tyre features (compound & tyre_age) if present
tyre_path = r'C:\\Users\\Nihan\\.vscode\\pitwall\\data\\processed\\9558\\tyre_features.parquet'
print_header('Loading tyre_features.parquet')
try:
    tyre_df = pd.read_parquet(tyre_path)
    print('Tyre columns:', list(tyre_df.columns))
except Exception as e:
    print('Error loading tyre_features.parquet:', e)
    tyre_df = None

# 5. Load weather data if present
weather_path = r'C:\\Users\\Nihan\\.vscode\\pitwall\\data\\processed\\9558\\weather.parquet'
print_header('Loading weather.parquet')
try:
    weather_df = pd.read_parquet(weather_path)
    print('Weather columns:', list(weather_df.columns))
except Exception as e:
    print('Error loading weather.parquet:', e)
    weather_df = None

# 6. Merge tyre info into laps (if available)
if tyre_df is not None:
    # Expected keys: driver_number, lap_number, compound, tyre_age
    merge_keys = [k for k in ['driver_number', 'lap_number'] if k in df.columns and k in tyre_df.columns]
    if {'compound', 'tyre_age'}.issubset(tyre_df.columns):
        df = df.merge(tyre_df[['driver_number', 'lap_number', 'compound', 'tyre_age']],
                      on=merge_keys, how='left')
        print('After tyre merge, sample rows:')
        print(df[['driver_number', 'lap_number', 'compound', 'tyre_age']].head())
    else:
        print('Tyre file missing compound/tyre_age columns – skipping merge.')
else:
    print('Tyre information not available – will omit compound/tyre_age columns.')

# 7. Merge weather info (if available)
if weather_df is not None:
    # Typical weather file contains lap_number plus weather features
    weather_cols = [c for c in ['lap_number', 'rainfall', 'track_temperature', 'air_temperature'] if c in weather_df.columns]
    if 'lap_number' in weather_cols:
        df = df.merge(weather_df[weather_cols], on='lap_number', how='left')
        print('After weather merge, sample rows:')
        print(df[['lap_number', 'rainfall', 'track_temperature', 'air_temperature']].head())
    else:
        print('Weather file has no lap_number – cannot merge.')
else:
    print('Weather information not available – will omit weather columns.')

# 8. Helper to display rows for a driver and lap range
def show_driver(driver, start, end):
    sub = df[(df['driver_number'] == driver) &
             (df['lap_number'] >= start) &
             (df['lap_number'] <= end)].sort_values('lap_number')
    if sub.empty:
        print(f'No data for driver {driver} laps {start}-{end}')
        return
    # Base columns that are always present
    cols = ['lap_number', 'lap_duration', 'duration_sector_1', 'duration_sector_2', 'duration_sector_3', 'is_pit_out_lap']
    # Optional columns if they exist after merges
    for opt in ['compound', 'tyre_age', 'rainfall', 'track_temperature', 'air_temperature']:
        if opt in sub.columns:
            cols.append(opt)
    print(f'Driver {driver} rows {start}-{end}:')
    print(sub[cols].to_string(index=False))
    # Report missing-value counts for the selected rows
    miss = sub[cols].isna().sum()
    if miss.any():
        print('Missing values per column:')
        print(miss[miss > 0])
    else:
        print('No missing values in displayed columns.')
    # Verify ordering
    if not sub['lap_number'].is_monotonic_increasing:
        print('⚠️ Lap numbers are not strictly increasing!')

print_header('Piastri (driver 81)')
show_driver(81, 20, 35)
print_header('Hamilton (driver 44)')
show_driver(44, 20, 35)
