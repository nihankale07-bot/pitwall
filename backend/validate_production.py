
import json
import time
import requests
from pathlib import Path
from statistics import mean

BASE_URL = "http://127.0.0.1:8000"

# Same race configuration used in our previous API validation
REQUEST = {
    "session_key": 9558,
    "target_driver": 44,
    "decision_lap": 26,
    "race_length": 52,
    "track_mode": "causal",
    "pit_loss": 22.0,
    "max_stops": 2,
    "max_candidates": 95,
}


def check(name, condition):
    if not condition:
        raise AssertionError(f"FAILED: {name}")
    print(f"PASSED: {name}")


def main():
    print("=" * 55)
    print("PITWALL PRODUCTION VALIDATION")
    print("=" * 55)

    # 1. API health
    health = requests.get(f"{BASE_URL}/health", timeout=10)
    check("API health", health.status_code == 200)

    # 2. Session discovery
    sessions_response = requests.get(
        f"{BASE_URL}/sessions", timeout=10
    )
    check("Session discovery", sessions_response.status_code == 200)

    sessions = sessions_response.json()["sessions"]
    check("Target session exists", 9558 in sessions)

# 3. Driver discovery
    drivers_response = requests.get(
       f"{BASE_URL}/sessions/9558/drivers", timeout=10
    )
    check("Driver discovery", drivers_response.status_code == 200)

    drivers = drivers_response.json()["drivers"]
    check("Target driver exists", 44 in drivers)

    # 4. Optimization performance
    timings = []
    result = None

    for run in range(1, 4):
        start = time.perf_counter()

        response = requests.post(
            f"{BASE_URL}/optimize",
            json=REQUEST,
            timeout=120
        )

        elapsed = time.perf_counter() - start

        check(
            f"Optimization run {run}",
            response.status_code == 200
        )

        result = response.json()
        timings.append(elapsed)

        print(f"  Run {run}: {elapsed:.3f} seconds")

    print(f"\nAverage API response time: {mean(timings):.3f}s")

    # 5. Response structure
    required_fields = {
        "session_key",
        "target_driver",
        "decision_lap",
        "race_length",
        "track_mode",
        "model",
        "recommendation",
        "ranking",
        "best_replay",
        "projected_classification",
    }

    check(
        "Response contract",
        set(result.keys()) == required_fields
    )

    check(
        "Ranking populated",
        len(result["ranking"]) > 0
    )

    check(
        "Recommendation populated",
        bool(result["recommendation"])
    )

    check(
        "Causal mode returned",
        result["track_mode"] == "causal"
    )

    # 6. Numerical validity
    serialized = json.dumps(result, allow_nan=False)
    check("Strict JSON serialization", bool(serialized))

    # 7. Invalid input
    invalid_request = REQUEST.copy()
    invalid_request["decision_lap"] = -1

    invalid_response = requests.post(
        f"{BASE_URL}/optimize",
        json=invalid_request,
        timeout=10
    )

    check(
        "Invalid input rejected",
        invalid_response.status_code == 422
    )

    # 8. Save report
    report = {
        "status": "PASSED",
        "request": REQUEST,
        "api_response_times_seconds": timings,
        "average_api_response_seconds": mean(timings),
        "ranking_count": len(result["ranking"]),
        "recommended_strategy": result["recommendation"],
    }

    report_dir = Path("data/audit")
    report_dir.mkdir(parents=True, exist_ok=True)

    report_path = report_dir / "production_validation_report.json"

    with open(report_path, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4, allow_nan=False)

    print("\n" + "=" * 55)
    print("PRODUCTION VALIDATION: PASSED")
    print(f"Report saved to: {report_path.resolve()}")
    print("=" * 55)


if __name__ == "__main__":
    main()
