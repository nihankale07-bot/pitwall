import json
from pathlib import Path
from datetime import datetime


def load_data(file_path):
    with open(file_path, "r") as file:
        return json.load(file)


def check_req_fields(data, required_fields):
    missing_fields = []

    for record in data:
        for field in required_fields:
            if field not in record:
                missing_fields.append(field)

    return missing_fields


def check_missing_values(data, fields):
    missing_values = {}

    for field in fields:
        count = 0

        for record in data:
            if record.get(field) is None:
                count += 1

        missing_values[field] = count

    return missing_values


def check_duplicates(data, key_fields):
    seen = set()
    duplicates = []

    for record in data:
        key = tuple(record[field] for field in key_fields)

        if key in seen:
            duplicates.append(key)
        else:
            seen.add(key)

    return duplicates


def check_data_types(data, expected_types):
    invalid_types = []

    for record in data:
        for field, expected_type in expected_types.items():
            value = record.get(field)

            if value is not None and not isinstance(value, expected_type):
                invalid_types.append((field, value))

    return invalid_types


def check_timestamps(
    data,
    timestamp_field,
    order_field=None,
    group_field=None
):
    invalid_timestamps = []
    timestamps = {}

    for record in data:
        timestamp = record.get(timestamp_field)

        if timestamp is None:
            continue

        try:
            parsed_time = datetime.fromisoformat(timestamp)

        except (ValueError, TypeError):
            invalid_timestamps.append(record)
            continue

        if group_field and order_field:
            group = record.get(group_field)
            order = record.get(order_field)

            if group not in timestamps:
                timestamps[group] = []

            timestamps[group].append(
                (order, parsed_time)
            )

    out_of_order = []

    for group, records in timestamps.items():

        records.sort(key=lambda x: x[0])

        for i in range(1, len(records)):

            if records[i][1] < records[i - 1][1]:

                out_of_order.append({
                    "group": group,
                    "previous": records[i - 1],
                    "current": records[i]
                })

    return invalid_timestamps, out_of_order


LAPS_CONFIG = {
    "required_fields": [
        "session_key",
        "driver_number",
        "lap_number",
        "date_start",
        "lap_duration"
    ],

    "expected_types": {
        "driver_number": int,
        "lap_number": int,
        "lap_duration": (int, float)
    },

    "timestamp": {
        "field": "date_start",
        "order_field": "lap_number",
        "group_field": "driver_number"
    },

    "duplicate_fields": [
        "driver_number",
        "lap_number"
    ]
}


POSITION_CONFIG = {
    "required_fields": [
        "date",
        "session_key",
        "driver_number",
        "position",
        "meeting_key"
    ],

    "expected_types": {
        "session_key": int,
        "driver_number": int,
        "position": int
    },

    "timestamp": {
        "field": "date",
        "order_field": "date",
        "group_field": "driver_number"
    },

    "duplicate_fields": [
        "date",
        "driver_number"
    ]
}


STINTS_CONFIG = {
    "required_fields": [
        "meeting_key",
        "session_key",
        "stint_number",
        "driver_number",
        "lap_start",
        "lap_end",
        "compound",
        "tyre_age_at_start"
    ],

    "expected_types": {
        "meeting_key": int,
        "session_key": int,
        "stint_number": int,
        "driver_number": int,
        "lap_start": int,
        "lap_end": int,
        "compound": str,
        "tyre_age_at_start": int
    },

    "timestamp": None,

    "duplicate_fields": [
        "driver_number",
        "stint_number"
    ]
}

WEATHER_CONFIG = {
    "required_fields": [
        "date",
        "session_key",
        "meeting_key",
        "track_temperature",
        "wind_speed",
        "rainfall",
        "humidity",
        "pressure",
        "air_temperature",
        "wind_direction"
    ],

    "expected_types": {
        "session_key": int,
        "meeting_key": int,
        "track_temperature": (int, float),
        "wind_speed": (int, float),
        "rainfall": (int, float),
        "humidity": (int, float),
        "pressure": (int, float),
        "air_temperature": (int, float),
        "wind_direction": int
    },

    "timestamp": {
        "field": "date",
        "order_field": "date",
        "group_field": None
    },

    "duplicate_fields": [
        "date"
    ]
}

RACE_CONTROL_CONFIG = {
    "required_fields": [
        "meeting_key",
        "session_key",
        "date",
        "driver_number",
        "lap_number",
        "category",
        "flag",
        "scope",
        "sector",
        "qualifying_phase",
        "message"
    ],

    "expected_types": {
        "meeting_key": int,
        "session_key": int,
        "driver_number": int,
        "lap_number": int,
        "category": str,
        "flag": str,
        "scope": str,
        "sector": int,
        "qualifying_phase": str,
        "message": str
    },

    "timestamp": {
        "field": "date",
        "order_field": "date",
        "group_field": None
    },

    "duplicate_fields": [
        "date",
        "message"
    ]
}

CAR_DATA_CONFIG = {
    "required_fields": [
        "date",
        "session_key",
        "meeting_key",
        "driver_number",
        "n_gear",
        "drs",
        "brake",
        "rpm",
        "speed",
        "throttle"
    ],

    "expected_types": {
        "session_key": int,
        "meeting_key": int,
        "driver_number": int,
        "n_gear": int,
        "drs": int,
        "brake": int,
        "rpm": int,
        "speed": int,
        "throttle": int
    },

    "timestamp": {
        "field": "date",
        "order_field": "date",
        "group_field": None
    },

    "duplicate_fields": [
        "date",
        "driver_number"
    ]
}

DATASETS = {
    "laps": {
        "file": Path("data/raw/laps_9558.json"),
        "config": LAPS_CONFIG
    },

    "position": {
        "file": Path("data/raw/position_9558.json"),
        "config": POSITION_CONFIG
    },

    "stints": {
        "file": Path("data/raw/stints_9558.json"),
        "config": STINTS_CONFIG
    },
    "weather": {
        "file": Path("data/raw/weather_9558.json"),
        "config": WEATHER_CONFIG
    },
    "race_control": {
        "file": Path("data/raw/race_control_9558.json"),
        "config": RACE_CONTROL_CONFIG
    }
}
for file in Path("data/raw").glob("car_data_9558_*.json"):
    driver_number = file.stem.split("_")[-1]

    DATASETS[f"car_data_{driver_number}"] = {
            "file": file,
            "config": CAR_DATA_CONFIG
    }

def validate_data(data, config):

    required_fields = config["required_fields"]
    expected_types = config["expected_types"]
    duplicate_fields = config["duplicate_fields"]
    timestamp_config = config["timestamp"]

    print("Number of records:", len(data))

    if not isinstance(data, list):
        print("Data is not a list")
        return

    invalid_records = [
        record
        for record in data
        if not isinstance(record, dict)
    ]

    print("Invalid record structures:", len(invalid_records))

    missing_fields = check_req_fields(
        data,
        required_fields
    )

    print("Missing required fields:", len(missing_fields))

    missing_values = check_missing_values(
        data,
        required_fields
    )

    for field, count in missing_values.items():
        print(f"{field} missing values:", count)

    duplicates = check_duplicates(
        data,
        duplicate_fields
    )

    print("Duplicate records:", len(duplicates))

    if duplicates:
        print("Duplicates:", duplicates)

    invalid_types = check_data_types(
        data,
        expected_types
    )

    print("Invalid data types:", len(invalid_types))

    if invalid_types:
        for field, value in invalid_types:
            print(field, value)

    if timestamp_config:

        invalid_timestamps, out_of_order = check_timestamps(
            data,
            timestamp_config["field"],
            timestamp_config["order_field"],
            timestamp_config["group_field"]
        )

        print(
            "Invalid timestamp formats:",
            len(invalid_timestamps)
        )

        print(
            "Out of order timestamps:",
            len(out_of_order)
        )


if __name__ == "__main__":

    for name, dataset in DATASETS.items():

        print("\n" + "=" * 50)
        print(f"Validating {name.upper()}")
        print("=" * 50)

        data = load_data(dataset["file"])

        validate_data(
            data,
            dataset["config"]
        )