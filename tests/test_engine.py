"""Tests for the PITWALL replay engine."""

import pytest
from pitwall.data import load_race, get_finishers
from pitwall.engine import replay, replay_actual, Stay, Pit
from pitwall.validation import run_plumbing_test, run_support_test, run_sanity_bound_test


@pytest.fixture(scope="module")
def race_data():
    return load_race(9558)


def test_finishers_count(race_data):
    finishers = get_finishers(race_data)
    assert len(finishers) == 12
    assert 44 in finishers
    assert 63 not in finishers  # Russell retired


def test_replay_actual_exact(race_data):
    """Phase 1 check: replay_actual reproduces recorded order and times exactly."""
    res = run_plumbing_test(race_data)
    assert res.passed, res.message


def test_non_finisher_handling(race_data):
    """Engine refuses to claim final position for non-finisher beyond ground truth."""
    res = replay(race_data, target_driver=63, decision_lap=20, action=Stay())
    assert res.ground_truth_available is False
    assert res.summary["final_position"] is None
    assert res.summary["total_time_delta_vs_actual"] is None


def test_support_test(race_data):
    """Support test flags unsupported compounds."""
    supported, _ = run_support_test(race_data, "INTERMEDIATE", (28, 38))
    assert supported is True

    unsupported, _ = run_support_test(race_data, "HARD", (28, 35))
    assert unsupported is False
