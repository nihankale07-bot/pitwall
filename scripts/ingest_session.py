import json
from pathlib import Path

from scripts.openf1_client import get


ENDPOINTS = [
    "laps",
    "position",
    "stints",
    "weather",
    "race_control"
]


def save_raw_data(data, filename):
    path = Path("data/raw") / filename
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as file:
        json.dump(data, file, indent=2)


def ingest_data(endpoint, session_key):
    data = get(endpoint, {"session_key": session_key})

    filename = f"{endpoint}_{session_key}.json"
    save_raw_data(data, filename)

    return data

def ingest_car_data(session_key, driver_numbers):
    for driver_number in driver_numbers:
        print(f"Ingesting car_data for driver {driver_number}...")

        data = get(
            "car_data",
            {
                "session_key": session_key,
                "driver_number": driver_number
            }
        )

        filename = f"car_data_{session_key}_{driver_number}.json"
        save_raw_data(data, filename)

        print(f"  Retrieved {len(data)} records")


def ingest_session(session_key):
    for endpoint in ENDPOINTS:
        print(f"Ingesting {endpoint}...")

        data = ingest_data(endpoint, session_key)

        print(f"  Retrieved {len(data)} records")

    drivers = get(
        "drivers",
        {"session_key": session_key}
    )

    driver_numbers = [
        driver["driver_number"] for driver in drivers
    ]

    ingest_car_data(session_key, driver_numbers)


if __name__ == "__main__":
    ingest_session(9558)