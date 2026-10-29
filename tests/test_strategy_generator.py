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


def test_candidate_generation_contains_baseline(setup):
    df, _, _ = setup
    cands = generate_multi_stop_candidates(df, target_driver=44, decision_lap=26)
    assert len(cands) > 0
    assert len(cands) < 100
    assert cands["is_baseline"].any()
    # Baseline should be ranked in the top 5
    base_idx = cands[cands["is_baseline"]].index[0]
    assert base_idx < 5


def test_baseline_replay_hamilton(setup):
    df, model, pit_loss = setup
    strat = Strategy(pit_sequence=((27, "INTERMEDIATE"), (38, "SOFT")))
    res = replay(df, target_driver=44, decision_lap=26, strategy=strat, pace_model=model, pit_loss=pit_loss)
    assert res.summary["final_position"] == 1
    assert abs(res.summary["total_time_delta_vs_actual"]) < 2.0
