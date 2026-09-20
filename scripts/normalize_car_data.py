import json
import pandas as pd
from pathlib import Path

def normalize_car_data(raw_file):
    with open(raw_file, "r") as file:
        car_data = json.load(file)

    df = pd.DataFrame(car_data)

    df["date"] = pd.to_datetime(
        df["date"], format="mixed", utc = True
    )

    numeric_columns = [
        "session_key",
        "meeting_key",
        "driver_number",
        "n_gear",
        "drs",
        "brake",
        "rpm",
        "speed",
        "throttle"
    ]

    for column in numeric_columns:
        df[column] = df[column].astype("int64")

    df = df.sort_values(
        "date"
    ).reset_index(drop=True)

    return df

raw_dir = Path("data/raw")
output_dir = Path("data/processed/9558/car_data")

output_dir.mkdir(parents=True, exist_ok=True)

car_files = sorted(
    raw_dir.glob("car_data_9558_*.json")
)

print(f"Found {len(car_files)} car data files")

for raw_file in car_files:
    driver_number = raw_file.stem.split("_")[-1]

    df = normalize_car_data(raw_file)

    output_file = output_dir / f"{driver_number}.parquet"

    df.to_parquet(output_file, index=False)

    print(
        f"Driver {driver_number}: "
        f"{len(df)} records → {output_file}"
    )