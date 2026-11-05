import requests

BASE_URL = "http://127.0.0.1:8000"

SESSION_KEY = 9558
TARGET_DRIVER = 63
DECISION_LAP = 26
RACE_LENGTH = 52


def check(condition, message):
    if not condition:
        raise AssertionError(message)

    print(f"PASSED: {message}")


def main():
    print("\nPITWALL LATEST CORRECTION VALIDATION")
    print("=" * 50)

    # 1. Check API health
    response = requests.get(f"{BASE_URL}/health", timeout=10)
    response.raise_for_status()

    check(response.status_code == 200, "API health")

    # 2. Load available drivers
    response = requests.get(
        f"{BASE_URL}/sessions/{SESSION_KEY}/drivers",
        timeout=20,
    )
    response.raise_for_status()

    driver_payload = response.json()
    drivers = driver_payload["drivers"]

    print(f"\nDrivers discovered: {len(drivers)}")

    # 3. Run a causal strategy optimization
    payload = {
        "session_key": SESSION_KEY,
        "target_driver": TARGET_DRIVER,
        "decision_lap": DECISION_LAP,
        "race_length": RACE_LENGTH,
        "track_mode": "causal",
        "pit_loss": 22.0,
        "max_stops": 2,
        "max_candidates": 95,
    }

    response = requests.post(
        f"{BASE_URL}/optimize",
        json=payload,
        timeout=180,
    )
    response.raise_for_status()

    result = response.json()

    check(
        result["session_key"] == SESSION_KEY,
        "Correct session returned",
    )

    check(
        result["target_driver"] == TARGET_DRIVER,
        "Correct target driver returned",
    )

    classification = result["projected_classification"]

    check(
        isinstance(classification, list) and len(classification) > 0,
        "Projected classification is populated",
    )

    # 4. Inspect classification structure
    print("\nClassification fields:")
    print(list(classification[0].keys()))

    print("\nProjected classification:")
    for row in classification:
        print(row)

    # 5. Check driver coverage
    classification_drivers = {
        int(row["driver_number"])
        for row in classification
        if row.get("driver_number") is not None
    }

    expected_drivers = {
        int(driver["driver_number"])
        if isinstance(driver, dict)
        else int(driver)
        for driver in drivers
    }

    non_starters = {10}

    expected_drivers -= non_starters

    missing_drivers = expected_drivers - classification_drivers

    check(
        not missing_drivers,
        f"All discovered drivers represented; missing: {missing_drivers}",
    )

    # 6. Check classification positions
        # 6. Validate finishing positions using only the final race lap
    final_lap_rows = [
        row for row in classification
        if int(row["lap_number"]) == RACE_LENGTH
    ]

    positioned_rows = [
        row for row in final_lap_rows
        if row.get("position") is not None
    ]

    positions = [
        int(row["position"])
        for row in positioned_rows
    ]

    check(
        len(positions) == len(set(positions)),
        "No duplicate positions on final race lap",
    )

    check(
        positions == sorted(positions),
        "Final-lap classification is ordered by position",
    )

    print(f"\nDrivers on final lap: {len(final_lap_rows)}")
    print(f"Positioned drivers: {len(positioned_rows)}")

    # Drivers with no finishing position
    unclassified = [
        row for row in classification
        if row.get("position") is None
    ]

    print(f"Unclassified records: {len(unclassified)}")

    # 7. Check retired/unclassified drivers
    unclassified = [
        row for row in classification
        if row.get("position") is None
    ]

    print(
        f"\nPositioned drivers: {len(positioned_rows)}"
        f"\nUnclassified drivers: {len(unclassified)}"
    )

    print("\nAPI CORRECTION VALIDATION COMPLETED")


if __name__ == "__main__":
    main()