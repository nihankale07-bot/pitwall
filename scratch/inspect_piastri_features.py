import pandas as pd
from pathlib import Path

p = Path("data/processed/9558")

for filename in [
    "stints.parquet",
    "fuel_features.parquet",
    "rolling_temporal_predictions.parquet",
    "race_state.parquet"
]:
    print("\n" + "=" * 70)
    print(filename)

    df = pd.read_parquet(p / filename)

    print("\nCOLUMNS:")
    print(df.columns.tolist())

    if "driver_number" in df.columns:
        df = df[df["driver_number"].isin([81, 44])]

    if "lap_number" in df.columns:
        df = df[df["lap_number"].between(20, 35)]

    print("\nRELEVANT ROWS:")
    print(df.to_string(index=False))
