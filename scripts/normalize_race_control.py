import json
from pathlib import Path
import pandas as pd

raw_file = Path("data/raw/race_control_9558.json")

with open(raw_file, "r") as file:
    positions = json.load(file)

df = pd.DataFrame(positions)

df["date"] = pd.to_datetime(
    df["date"],
    format="mixed",
    utc=True
)

df["driver_number"] = df["driver_number"].astype("Int64")
df["sector"] = df["sector"].astype("Int64")

for column in [
    "category",
    "flag",
    "scope",
    "qualifying_phase"
]:
    df[column] = df[column].str.upper().str.strip()

df = df.sort_values(
    ["date", "lap_number"]
).reset_index(drop=True)

print("\nEvent categories:")
print(df["category"].value_counts())

print("\nFlags:")
print(df["flag"].value_counts(dropna=False))

print("\nDrivers referenced:")
print(df["driver_number"].value_counts(dropna=False).head(15))

print("\nChronological order:")
print(df["date"].is_monotonic_increasing)

output_dir = Path("data/processed/9558")
output_dir.mkdir(parents=True, exist_ok=True)

output_file = output_dir / "race_control.parquet"

df.to_parquet(
    output_file,
    index=False
)

print(f"\nSaved normalized data to: {output_file}")