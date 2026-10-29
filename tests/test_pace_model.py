"""Tests for the lap fixed-effects pace model."""

import pytest
from pitwall.data import load_race
from pitwall.pace_model import PaceModel


@pytest.fixture(scope="module")
def fitted_model():
    df = load_race(9558)
    model = PaceModel().fit(df)
    return model


def test_model_r_squared(fitted_model):
    """Pace model should capture the vast majority of lap time variance (>90%)."""
    assert fitted_model.rsquared > 0.90


def test_identification_report(fitted_model):
    """Identification report should exist and identify weak pairs."""
    rep = fitted_model.identification_report
    assert rep is not None
    assert rep.n_clean_laps > 700
    assert "MEDIUM vs INTERMEDIATE" in rep.weakly_identified_pairs


def test_predict_replay_mode(fitted_model):
    """Test replay mode prediction returns reasonable lap times."""
    lap_time = fitted_model.predict_lap(
        lap_number=10,
        driver_number=44,
        compound="MEDIUM",
        tyre_age=10,
        mode="replay",
    )
    assert 85.0 <= lap_time <= 100.0


def test_predict_causal_mode(fitted_model):
    """Test causal mode prediction uses decision lap state."""
    lap_time = fitted_model.predict_lap(
        lap_number=30,
        driver_number=44,
        compound="MEDIUM",
        tyre_age=10,
        mode="causal",
        decision_lap=20,
    )
    assert 85.0 <= lap_time <= 105.0
