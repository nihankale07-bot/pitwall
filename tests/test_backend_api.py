"""Tests for the PITWALL Backend FastAPI Application endpoints."""

import pytest

from backend.main import home, health, get_sessions, get_drivers, optimize
from backend.schemas import OptimizeRequest, OptimizationResponse
from pitwall.data import load_race, resolve_driver_number


def test_home_and_health():
    res_home = home()
    assert res_home["status"] == "online"
    assert res_home["application"] == "PITWALL"

    res_health = health()
    assert res_health["status"] == "healthy"


def test_get_sessions():
    res = get_sessions()
    assert "sessions" in res
    assert 9558 in res["sessions"]
    assert res["count"] >= 1


def test_get_drivers():
    res = get_drivers(session_key=9558)
    assert res["session_key"] == 9558
    assert "drivers" in res
    assert 1 in res["drivers"]   # Verstappen
    assert 44 in res["drivers"]  # Hamilton
    assert res["count"] >= 12


def test_optimize_endpoint_verstappen():
    """
    Test POST /optimize with Max Verstappen at lap 26 in session 9558.
    Verifies that the backend returns recommended strategy, candidate ranking,
    projected classification, and preserves rivals' actual trajectories.
    """
    race_df = load_race(9558)
    verstappen = resolve_driver_number(race_df, "Max Verstappen")
    hamilton = resolve_driver_number(race_df, "Lewis Hamilton")

    req = OptimizeRequest(
        session_key=9558,
        target_driver=verstappen,
        decision_lap=26,
        race_length=52,
        track_mode="causal",
        pit_loss=22.0,
        max_stops=2,
        max_candidates=10,
    )

    data = optimize(req)

    # Check root fields
    assert data["session_key"] == 9558
    assert data["target_driver"] == verstappen
    assert data["decision_lap"] == 26
    assert data["race_length"] == 52
    assert data["track_mode"] == "causal"

    # Check recommendation & ranking
    assert "recommendation" in data
    assert "strategy_id" in data["recommendation"]
    assert len(data["ranking"]) > 0

    # Check best replay
    best_replay = data["best_replay"]
    assert "summary" in best_replay
    assert "laps_table" in best_replay
    assert len(best_replay["laps_table"]) > 0

    # Check projected classification
    classification = data["projected_classification"]
    assert classification is not None
    assert len(classification) == 20  # Full grid

    # Verify positions are 1..20
    positions = [row["position"] for row in classification]
    assert positions == list(range(1, 21))

    # Verify Hamilton retains his recorded cumulative time (4947.427s)
    ham_entry = next(r for r in classification if r["driver_number"] == hamilton)
    assert abs(ham_entry["cum_time"] - 4947.427) < 0.01

    # Verify Verstappen is marked as target
    ver_entry = next(r for r in classification if r["driver_number"] == verstappen)
    assert ver_entry["is_target"] is True
