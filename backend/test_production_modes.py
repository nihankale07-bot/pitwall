
import json
import time
import requests

from pathlib import Path
from statistics import mean


BASE_URL = "http://127.0.0.1:8000"

BASE_REQUEST = {
    "session_key": 9558,
    "target_driver": 44,
    "decision_lap": 26,
    "race_length": 52,
    "track_mode": "causal",
    "pit_loss": 22.0,
    "max_stops": 2,
    "max_candidates": 95,
}

results = []


def check(name, condition, details=""):
    status = "PASSED" if condition else "FAILED"
    results.append({
        "test": name,
        "status": status,
        "details": details
    })

    print(f"{status}: {name}")

    if details:
        print(f"  {details}")

    if not condition:
        raise AssertionError(f"{name} failed: {details}")


def expect_client_error(name, response, expected=(400, 404, 422)):
    check(
        name,
        response.status_code in expected,
        f"HTTP {response.status_code}: {response.text[:300]}"
    )


def main():

    print("=" * 60)
    print("PITWALL BACKEND HARDENING")
    print("=" * 60)

    # --------------------------------------------------
    # 1. REPLAY MODE
    # --------------------------------------------------

    print("\n1. REPLAY MODE VALIDATION")

    replay_request = BASE_REQUEST.copy()
    replay_request["track_mode"] = "replay"

    start = time.perf_counter()

    response = requests.post(
        f"{BASE_URL}/optimize",
        json=replay_request,
        timeout=180
    )

    replay_time = time.perf_counter() - start

    check(
        "Replay optimization HTTP response",
        response.status_code == 200,
        f"HTTP {response.status_code}, {replay_time:.3f}s"
    )

    replay_result = response.json()

    check(
        "Replay mode correctly identified",
        replay_result["track_mode"] == "replay"
    )

    check(
        "Replay ranking populated",
        len(replay_result["ranking"]) > 0
    )

    check(
        "Replay recommendation populated",
        bool(replay_result["recommendation"])
    )

    check(
        "Replay output valid JSON",
        bool(json.dumps(replay_result, allow_nan=False))
    )

    # --------------------------------------------------
    # 2. INVALID DRIVER
    # --------------------------------------------------

    print("\n2. INVALID DRIVER VALIDATION")

    invalid_driver = BASE_REQUEST.copy()
    invalid_driver["target_driver"] = 9999

    response = requests.post(
        f"{BASE_URL}/optimize",
        json=invalid_driver,
        timeout=30
    )

    expect_client_error(
        "Unknown driver rejected",
        response
    )

    # --------------------------------------------------
    # 3. INVALID DECISION LAP
    # --------------------------------------------------

    print("\n3. INVALID DECISION LAP VALIDATION")

    invalid_lap = BASE_REQUEST.copy()
    invalid_lap["decision_lap"] = 53

    response = requests.post(
        f"{BASE_URL}/optimize",
        json=invalid_lap,
        timeout=30
    )

    expect_client_error(
        "Decision lap beyond race length rejected",
        response
    )

    # --------------------------------------------------
    # 4. INVALID RACE LENGTH
    # --------------------------------------------------

    print("\n4. INVALID RACE LENGTH VALIDATION")

    invalid_race = BASE_REQUEST.copy()
    invalid_race["race_length"] = 20

    response = requests.post(
        f"{BASE_URL}/optimize",
        json=invalid_race,
        timeout=30
    )

    expect_client_error(
        "Race length shorter than decision lap rejected",
        response
    )

    # --------------------------------------------------
    # 5. INVALID OPTIMIZER CONFIGURATION
    # --------------------------------------------------

    print("\n5. INVALID OPTIMIZER CONFIGURATION")

    invalid_candidates = BASE_REQUEST.copy()
    invalid_candidates["max_candidates"] = 0

    response = requests.post(
        f"{BASE_URL}/optimize",
        json=invalid_candidates,
        timeout=15
    )

    check(
        "Zero candidates rejected by schema",
        response.status_code == 422,
        f"HTTP {response.status_code}"
    )

    # --------------------------------------------------
    # 6. MISSING SESSION
    # --------------------------------------------------

    print("\n6. MISSING SESSION VALIDATION")

    response = requests.get(
        f"{BASE_URL}/sessions/999999/drivers",
        timeout=15
    )

    check(
        "Missing session handled safely",
        response.status_code in (400, 404),
        f"HTTP {response.status_code}"
    )

    # --------------------------------------------------
    # 7. RESPONSE CONTRACT
    # --------------------------------------------------

    print("\n7. RESPONSE CONTRACT")

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
        "Replay response contract",
        set(replay_result.keys()) == required_fields
    )

    # --------------------------------------------------
    # 8. SAVE REPORT
    # --------------------------------------------------

    passed = sum(
        item["status"] == "PASSED"
        for item in results
    )

    failed = len(results) - passed

    report = {
        "project": "PITWALL",
        "validation": "Backend Production Hardening",
        "status": "PASSED" if failed == 0 else "FAILED",
        "passed": passed,
        "failed": failed,
        "replay_execution_seconds": replay_time,
        "replay_ranking_count": len(replay_result["ranking"]),
        "tests": results,
    }

    root = Path(__file__).resolve().parents[1]
    report_dir = root / "data" / "audit"
    report_dir.mkdir(parents=True, exist_ok=True)

    report_path = report_dir / "backend_hardening_report.json"

    with open(report_path, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4, allow_nan=False)

    print("\n" + "=" * 60)
    print(f"PASSED: {passed}")
    print(f"FAILED: {failed}")
    print(f"REPORT: {report_path}")
    print("=" * 60)

    if failed:
        raise SystemExit(1)

    print("BACKEND HARDENING: PASSED")


if __name__ == "__main__":
    main()
