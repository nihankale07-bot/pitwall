import json
import pandas as pd
from pathlib import Path

raw_file = Path("data/raw/stints_9558.json")

with open(raw_file, "r") as file:
    stints = json.load(file)

df = pd.DataFrame(stints)

print(df.head())
print(df.dtypes)
print("Shape:", df.shape)


df["meeting_key"] = df["meeting_key"].astype("int64")
df["session_key"] = df["session_key"].astype("int64")
df["stint_number"] = df["stint_number"].astype("int64")
df["driver_number"] = df["driver_number"].astype("int64")

df["lap_start"] = pd.to_numeric(df["lap_start"], errors="coerce")
df["lap_end"] = pd.to_numeric(df["lap_end"], errors="coerce")

df["compound"] = df["compound"].str.upper().str.strip()

df["tyre_age_at_start"] = df["tyre_age_at_start"].astype("int64")

df = df.sort_values(
    ["driver_number", "stint_number"]
).reset_index(drop=True)

print("\nNormalized dtypes:")
print(df.dtypes)

print("\nMissing values:")
print(df.isna().sum())

print("\nFirst 10 normalized stints:")
print(df.head())

print("Stint counts per driver:")
print(df.groupby("driver_number")["stint_number"].max().sort_index())

print("Stint data:")
print(df[["driver_number",
            "stint_number",
            "lap_start",
            "lap_end",
            "compound",
            "tyre_age_at_start"
        ]].to_string(index=False))

output_dir = Path("data/processed/9558")
output_dir.mkdir(parents=True, exist_ok=True)

output_file = output_dir / "stints.parquet"

df.to_parquet(output_file, index=False)

print(f"Saved normalized data to : {output_file}")