"""Tests for the pit loss measurement module."""

import pytest
from pitwall.data import load_race
from pitwall.pace_model import PaceModel
from pitwall.pit_loss import measure_pit_loss


@pytest.fixture(scope="module")
def race_setup():
    df = load_race(9558)
    model = PaceModel().fit(df)
    return df, model


def test_measure_pit_loss_green_flag(race_setup):
    df, model = race_setup
    green_summary, sc_summary = measure_pit_loss(df, model)
    assert green_summary.n_stops > 0
    assert 18.0 <= green_summary.median <= 26.0
    assert green_summary.iqr_low < green_summary.median < green_summary.iqr_high
