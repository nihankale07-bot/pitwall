import json
import pandas as pd
from pathlib import Path 

raw_file = Path("data/raw/position_9558.json")

with open(raw_file, "r") as file:
    positions = json.load(file)

df = pd.DataFrame(positions)

print(df.head())
print(df.dtypes)
print("\nShape:", df.shape)


df["date"] = pd.to_datetime(df["date"], format="mixed", utc = True)

df["session_key"] = df["session_key"].astype("int64")
df["meeting_key"] = df["meeting_key"].astype("int64")
df["driver_number"] = df["driver_number"].astype("int64")
df["position"] = df["position"].astype("int64")

df = df.sort_values(
    ["date", "driver_number"]
).reset_index(drop=True)

print("\nNormalized dtypes:")
print(df.dtypes)

print("Unique positions:")
print(sorted(df["position"].unique()))

print("\nPosition range:")
print(df["position"].min(), "to", df["position"].max())

print("\nDuplicate driver/timestamp combinations:")
print(
    df.duplicated(
        subset=["date", "driver_number"]
    ).sum()
)

print("\nDrivers represented:")
print(df["driver_number"].nunique())

output_dir = Path("data/processed/9558")
output_dir.mkdir(parents=True, exist_ok=True)

output_file = output_dir / "position.parquet"

df.to_parquet(
    output_file,
    index=False
)

print(f"\nSaved normalized data to: {output_file}")