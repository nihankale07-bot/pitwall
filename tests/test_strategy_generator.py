"""Tests for strategy generator and multi-stop replay."""

import pytest
from pitwall.data import load_race, get_finishers
from pitwall.strategy_generator import generate_multi_stop_candidates
from pitwall.engine import replay, Strategy
from pitwall.pace_model import PaceModel
from pitwall.pit_loss import measure_pit_loss


@pytest.fixture(scope="module")
def setup():
    df = load_race(9558)
    model = PaceModel().fit(df)
    green_summary, _ = measure_pit_loss(df, model)
    return df, model, green_summary.median


def test_candidate_generation_returns_valid_candidates(setup):
    """
    Candidate generation must return a non-empty,
    structurally valid set of unique strategies.
    """

    df, _, _ = setup

    cands = generate_multi_stop_candidates(
        df,
        target_driver=44,
        decision_lap=26,
        race_length=52
    )

    # Candidate generation must produce strategies.
    assert not cands.empty

    # Verify the expected output structure.
    required_columns = {
        "pit_sequence",
        "pit_sequence_str",
        "current_compound",
        "num_stops",
        "description",
        "strategy_id"
    }

    assert required_columns.issubset(set(cands.columns))

    # Every candidate must have a unique strategy identifier.
    assert cands["strategy_id"].is_unique

    # Every candidate must have a valid pit sequence.
    assert cands["pit_sequence"].notna().all()

    # Stop counts must be valid.
    assert (cands["num_stops"] >= 0).all()

    # The generator must respect the configured maximum of two stops.
    assert (cands["num_stops"] <= 2).all()


def test_baseline_replay_hamilton(setup):
    df, model, pit_loss = setup
    strat = Strategy(pit_sequence=((27, "INTERMEDIATE"), (38, "SOFT")))
    res = replay(df, target_driver=44, decision_lap=26, strategy=strat, pace_model=model, pit_loss=pit_loss, race_length=52)
    assert res.summary["final_position"] == 1
    assert abs(res.summary["total_time_delta_vs_actual"]) < 2.0
