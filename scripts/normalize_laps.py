import json
from pathlib import Path
import pandas as pd

raw_file = Path("data/raw/laps_9558.json")

with open(raw_file, "r") as file:
    laps = json.load(file)

df = pd.DataFrame(laps)

df["date_start"] = pd.to_datetime(df["date_start"], format="mixed", utc = True)

print(df[["segments_sector_1","segments_sector_2","segments_sector_3"]].head())
print(df[["segments_sector_1","segments_sector_2","segments_sector_3"]].dtypes)

print("Missing values:")
print(df.isna().sum())

df = df.sort_values(["driver_number", "lap_number"]).reset_index(drop=True)

print("Normalised DataFrame:")
print(df.head())
print("Shape:", df.shape)

output_dir = Path("data/processed/9558")
output_dir.mkdir(parents=True, exist_ok=True)

output_file = output_dir / "laps.parquet"

df.to_parquet(
    output_file,
    index=False
)
print(f"Saved normalised data to:{output_file}")

check_df = pd.read_parquet(output_file)

print("\nParquet verification:")
print(check_df.dtypes)
print("\nShape:", check_df.shape)
print(check_df.head())