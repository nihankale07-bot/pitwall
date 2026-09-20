import json 
from pathlib import Path
import pandas as pd

raw_file = Path("data/raw/weather_9558.json")

with open(raw_file, "r") as file:
    stints = json.load(file)

df = pd.DataFrame(stints)

print(df.head())
print(df.dtypes)
print("Shape:", df.shape)

print("Missing value: ")
print(df.isnull().sum())

df["date"] = pd.to_datetime(
    df["date"],
    format="mixed",
    utc=True
)

df["session_key"] = df["session_key"].astype("int64")
df["meeting_key"] = df["meeting_key"].astype("int64")

df["track_temperature"] = df["track_temperature"].astype("float64")
df["wind_speed"] = df["wind_speed"].astype("float64")
df["rainfall"] = df["rainfall"].astype("int64")
df["humidity"] = df["humidity"].astype("float64")
df["pressure"] = df["pressure"].astype("float64")
df["air_temperature"] = df["air_temperature"].astype("float64")
df["wind_direction"] = df["wind_direction"].astype("int64")

df = df.sort_values(
    "date"
).reset_index(drop=True)

print("\nNormalized dtypes:")
print(df.dtypes)

print("\nMissing values:")
print(df.isna().sum())

print("\nChronological order:")
print(df["date"].is_monotonic_increasing)

print("\nFirst 10 normalized records:")
print(df.head(10).to_string(index=False))

output_dir = Path("data/processed/9558")
output_dir.mkdir(parents=True, exist_ok=True)

output_file = output_dir / "weather.parquet"

df.to_parquet(
    output_file,
    index=False
)

print(f"\nSaved normalized data to: {output_file}")