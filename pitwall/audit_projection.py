
import requests
import json

API_URL = "http://127.0.0.1:8000/optimize"

REQUEST = {
    "session_key": 9558,
    "target_driver": 11,  # Placeholder: replace with your chosen driver
    "decision_lap": 26,
    "race_length": 52,
    "track_mode": "causal",
    "pit_loss": 22.0,
    "max_stops": 2,
    "max_candidates": 95,
}


def run_projection_audit():

    print("Running PITWALL projection audit...")

    response = requests.post(API_URL, json=REQUEST)

    print("HTTP status:", response.status_code)
    response.raise_for_status()

    result = response.json()

    print("\nREQUEST CONFIGURATION")
    print("=" * 50)
    print(json.dumps(REQUEST, indent=2))

    print("\nPROJECTED CLASSIFICATION")
    print("=" * 50)

    classification = result.get("projected_classification")

    if not classification:
        print("No projected classification returned.")
    else:
        for driver in classification:
            print(
                f"Driver: {driver.get('driver_number')} | "
                f"Position: {driver.get('position')} | "
                f"Time: {driver.get('cumulative_time')} | "
                f"Gap: {driver.get('gap')} | "
                f"Finished: {driver.get('finished')}"
            )

    print("\nRECOMMENDATION")
    print("=" * 50)
    print(json.dumps(result["recommendation"], indent=2))

    print("\nRESPONSE METADATA")
    print("=" * 50)
    print("Session:", result["session_key"])
    print("Target driver:", result["target_driver"])
    print("Decision lap:", result["decision_lap"])
    print("Race length:", result["race_length"])
    print("Track mode:", result["track_mode"])


if __name__ == "__main__":
    run_projection_audit()
