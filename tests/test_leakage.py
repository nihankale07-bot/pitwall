"""
Regression tests for counterfactual future-information leakage.

Verifies that:
  1. The pace model fitted inside optimize_strategy uses only laps <= decision_lap.
  2. Modifying post-decision target-driver lap times does not change fitted coefficients.
  3. Historical target-driver laps through decision_lap are unaffected by the replay.
  4. Future predictions use causal mode (decision-lap effect frozen).
  5. Pit-loss accounting remains 22 s per stop (11 s on each of in-lap and out-lap).
  6. Rival actual trajectories are unchanged in the laps_table.
  7. Final cumulative time covers all 52 laps.
"""

import pytest

from pitwall.data import load_race
from pitwall.engine import Stay, Strategy, replay
from pitwall.optimizer import optimize_strategy, _fit_on_history
from pitwall.pace_model import PaceModel


DECISION_LAP = 26
RACE_LENGTH = 52
TARGET_DRIVER = 81   # Piastri – used only because the fixture data is for session 9558


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def race_df():
    return load_race(session_key=9558)


@pytest.fixture(scope="module")
def fresh_model():
    """An unfitted PaceModel instance (used as a template for _fit_on_history)."""
    return PaceModel(reference_compound="MEDIUM")


# ---------------------------------------------------------------------------
# 1. Model fitted only on laps <= decision_lap
# ---------------------------------------------------------------------------

def test_history_model_contains_no_future_laps(race_df, fresh_model):
    """_fit_on_history must exclude every lap > decision_lap."""
    fitted = _fit_on_history(fresh_model, race_df, DECISION_LAP)
    assert fitted.fitted, "Model must report itself as fitted"
    # Every lap_effect key must be <= DECISION_LAP
    future_keys = [k for k in fitted.lap_effects if k > DECISION_LAP]
    assert future_keys == [], (
        f"Model contains lap effects for future laps: {sorted(future_keys)}"
    )


# ---------------------------------------------------------------------------
# 2. Post-decision lap modifications cannot influence the fitted coefficients
# ---------------------------------------------------------------------------

def test_future_lap_modification_does_not_change_model(race_df, fresh_model):
    """Inflating future target-driver laps must not alter the fitted model."""
    fitted_original = _fit_on_history(fresh_model, race_df, DECISION_LAP)

    # Create a modified copy where future target laps are doubled
    df_modified = race_df.copy()
    future_target_mask = (
        (df_modified["driver_number"] == TARGET_DRIVER)
        & (df_modified["lap_number"] > DECISION_LAP)
    )
    df_modified.loc[future_target_mask, "lap_duration"] *= 2.0

    fitted_modified = _fit_on_history(fresh_model, df_modified, DECISION_LAP)

    # All lap effects must be identical (modifications were post-decision)
    assert set(fitted_original.lap_effects.keys()) == set(fitted_modified.lap_effects.keys()), (
        "Fitted lap effect keys differ between original and modified data"
    )
    for lap, coef in fitted_original.lap_effects.items():
        assert coef == pytest.approx(fitted_modified.lap_effects[lap], abs=1e-6), (
            f"Lap effect for lap {lap} changed after future modification"
        )

    # Driver effect for TARGET_DRIVER must also be identical
    orig_eff = fitted_original.driver_effects.get(TARGET_DRIVER, 0.0)
    mod_eff  = fitted_modified.driver_effects.get(TARGET_DRIVER, 0.0)
    assert orig_eff == pytest.approx(mod_eff, abs=1e-6), (
        "Driver effect changed after future modification"
    )


# ---------------------------------------------------------------------------
# 3. Historical target laps through decision_lap are unaltered in laps_table
# ---------------------------------------------------------------------------

def test_historical_laps_unchanged_in_laps_table(race_df):
    """Laps 1..decision_lap for the target driver must match recorded actuals."""
    pace = PaceModel()
    result = optimize_strategy(
        session_df=race_df,
        target_driver=TARGET_DRIVER,
        decision_lap=DECISION_LAP,
        race_length=RACE_LENGTH,
        pace_model=pace,
        pit_loss=22.0,
        track_mode="causal",
        max_stops=2,
        max_candidates=5,
    )
    laps = result.best_replay.laps_table

    hist_sim = (
        laps.loc[
            (laps["driver_number"] == TARGET_DRIVER)
            & (laps["lap_number"] <= DECISION_LAP),
            ["lap_number", "lap_duration"],
        ]
        .sort_values("lap_number")
        .reset_index(drop=True)
    )
    actual = (
        race_df.loc[
            (race_df["driver_number"] == TARGET_DRIVER)
            & (race_df["lap_number"] <= DECISION_LAP),
            ["lap_number", "lap_duration"],
        ]
        .sort_values("lap_number")
        .reset_index(drop=True)
    )

    merged = hist_sim.merge(actual, on="lap_number", suffixes=("_sim", "_actual"))
    for _, row in merged.iterrows():
        assert row["lap_duration_sim"] == pytest.approx(row["lap_duration_actual"], abs=1e-3), (
            f"Historical lap {int(row['lap_number'])} duration changed in laps_table"
        )


# ---------------------------------------------------------------------------
# 4. Future predictions use the causal (frozen decision-lap) effect
# ---------------------------------------------------------------------------

def test_causal_mode_freezes_decision_lap_effect(race_df, fresh_model):
    """In causal mode every future lap uses the decision-lap fixed effect."""
    fitted = _fit_on_history(fresh_model, race_df, DECISION_LAP)

    # Reference: predict at the decision lap itself (causal)
    pred_at_decision = fitted.predict_lap(
        lap_number=DECISION_LAP,
        driver_number=TARGET_DRIVER,
        compound="MEDIUM",
        tyre_age=10,
        mode="causal",
        decision_lap=DECISION_LAP,
    )

    for future_lap in [27, 35, 45, 52]:
        pred_future = fitted.predict_lap(
            lap_number=future_lap,
            driver_number=TARGET_DRIVER,
            compound="MEDIUM",
            tyre_age=10,         # same tyre_age → only lap effect differs
            mode="causal",
            decision_lap=DECISION_LAP,
        )
        # With identical compound and tyre_age the only source of difference is the
        # lap fixed-effect.  In causal mode it must equal the decision-lap effect.
        assert pred_future == pytest.approx(pred_at_decision, abs=1e-6), (
            f"Causal prediction for lap {future_lap} ({pred_future:.4f}) "
            f"!= decision-lap prediction ({pred_at_decision:.4f})"
        )


# ---------------------------------------------------------------------------
# 5. Pit-loss accounting: 22 s total per stop (11 s in-lap + 11 s out-lap)
# ---------------------------------------------------------------------------

def test_pit_loss_accounting(race_df):
    """A one-stop strategy adds exactly 22 s across in-lap and out-lap."""
    PIT_LAP = 30
    PIT_COMPOUND = "HARD"

    # No pace model → placeholder pace is used uniformly, isolating the pit penalty
    result_pit = replay(
        session_df=race_df,
        target_driver=TARGET_DRIVER,
        decision_lap=DECISION_LAP,
        strategy=Strategy(pit_sequence=((PIT_LAP, PIT_COMPOUND),)),
        pace_model=None,
        pit_loss=22.0,
        track_mode="causal",
        race_length=RACE_LENGTH,
    )
    result_stay = replay(
        session_df=race_df,
        target_driver=TARGET_DRIVER,
        decision_lap=DECISION_LAP,
        strategy=Stay(),
        pace_model=None,
        pit_loss=22.0,
        track_mode="causal",
        race_length=RACE_LENGTH,
    )

    pit_target  = result_pit.laps_table.loc[
        result_pit.laps_table["driver_number"] == TARGET_DRIVER
    ].set_index("lap_number")
    stay_target = result_stay.laps_table.loc[
        result_stay.laps_table["driver_number"] == TARGET_DRIVER
    ].set_index("lap_number")

    in_lap_extra  = pit_target.loc[PIT_LAP,     "lap_duration"] - stay_target.loc[PIT_LAP,     "lap_duration"]
    out_lap_extra = pit_target.loc[PIT_LAP + 1, "lap_duration"] - stay_target.loc[PIT_LAP + 1, "lap_duration"]
    total_extra   = in_lap_extra + out_lap_extra

    assert total_extra == pytest.approx(22.0, abs=1e-3), (
        f"Expected 22.0 s total pit loss, got {total_extra:.3f} s"
    )


# ---------------------------------------------------------------------------
# 6. Rival actual trajectories are unchanged in the laps_table
# ---------------------------------------------------------------------------

def test_rival_trajectories_unchanged(race_df):
    """Non-target drivers must have exactly their actual recorded lap times."""
    pace = PaceModel()
    result = optimize_strategy(
        session_df=race_df,
        target_driver=TARGET_DRIVER,
        decision_lap=DECISION_LAP,
        race_length=RACE_LENGTH,
        pace_model=pace,
        pit_loss=22.0,
        track_mode="causal",
        max_stops=2,
        max_candidates=5,
    )
    laps = result.best_replay.laps_table

    for driver in race_df["driver_number"].unique():
        if driver == TARGET_DRIVER:
            continue
        sim_rows = (
            laps.loc[laps["driver_number"] == driver, ["lap_number", "lap_duration"]]
            .sort_values("lap_number")
            .reset_index(drop=True)
        )
        actual_rows = (
            race_df.loc[
                race_df["driver_number"] == driver, ["lap_number", "lap_duration"]
            ]
            .sort_values("lap_number")
            .reset_index(drop=True)
        )
        merged = sim_rows.merge(actual_rows, on="lap_number", suffixes=("_sim", "_actual"))
        for _, row in merged.iterrows():
            assert row["lap_duration_sim"] == pytest.approx(row["lap_duration_actual"], abs=1e-3), (
                f"Rival driver {driver} lap {int(row['lap_number'])} "
                f"sim={row['lap_duration_sim']:.3f} actual={row['lap_duration_actual']:.3f}"
            )


# ---------------------------------------------------------------------------
# 7. Full-race cumulative time covers all race_length laps
# ---------------------------------------------------------------------------

def test_full_race_cumulative_time(race_df):
    """summary.final_cumulative_time must equal the sum of all 52 simulated laps."""
    pace = PaceModel()
    result = optimize_strategy(
        session_df=race_df,
        target_driver=TARGET_DRIVER,
        decision_lap=DECISION_LAP,
        race_length=RACE_LENGTH,
        pace_model=pace,
        pit_loss=22.0,
        track_mode="causal",
        max_stops=2,
        max_candidates=5,
    )
    laps = result.best_replay.laps_table
    target_laps = laps.loc[laps["driver_number"] == TARGET_DRIVER].sort_values("lap_number")

    assert len(target_laps) == RACE_LENGTH, (
        f"Expected {RACE_LENGTH} target laps, got {len(target_laps)}"
    )

    lap_sum  = float(target_laps["lap_duration"].sum())
    reported = result.best_replay.summary.get("final_cumulative_time")
    assert reported == pytest.approx(lap_sum, abs=0.01), (
        f"summary final_cumulative_time {reported:.3f} != lap sum {lap_sum:.3f}"
    )

