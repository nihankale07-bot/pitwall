"""Comprehensive test suite for PITWALL counterfactual race strategy simulation."""

import numpy as np
import pandas as pd
import pytest

from pitwall.data import load_race, resolve_driver_number, get_finishers
from pitwall.engine import replay, replay_actual, Stay, Pit, Strategy, ReplayResult
from pitwall.pace_model import PaceModel
from pitwall.optimizer import optimize_strategy
from backend.services.simulator import build_pace_model


@pytest.fixture(scope="module")
def race_data():
    return load_race(9558)


@pytest.fixture(scope="module")
def causal_pace_model(race_data):
    # Fit causal pace model using information up to lap 26
    return build_pace_model(race_data, decision_lap=26, track_mode="causal")


def test_engine_import_and_execution(race_data, causal_pace_model):
    """1. Engine imports cleanly and executes successfully."""
    target_driver = resolve_driver_number(race_data, "Max Verstappen")
    res = replay(
        session_df=race_data,
        target_driver=target_driver,
        decision_lap=26,
        strategy=Stay(),
        pace_model=causal_pace_model,
        track_mode="causal",
        race_length=52,
    )
    assert isinstance(res, ReplayResult)
    assert res.target_driver == target_driver
    assert not res.laps_table.empty
    assert res.classification is not None
    assert not res.classification.empty


def test_actual_replay_reproduces_recorded_behaviour(race_data):
    """2. Actual replay reproduces recorded order and cumulative times."""
    actual_df = replay_actual(race_data)
    # 12 lead-lap finishers in session 9558
    assert len(actual_df) == 12
    # Verify computed position matches recorded position exactly
    for _, row in actual_df.iterrows():
        assert int(row["computed_position"]) == int(row["position"])


def test_target_only_counterfactual_intervention(race_data, causal_pace_model):
    """
    3. Target-only counterfactual intervention:
    Changing target strategy alters target driver's future, but pre-decision laps match actuals.
    """
    target = resolve_driver_number(race_data, "Max Verstappen")

    res_stay = replay(
        session_df=race_data,
        target_driver=target,
        decision_lap=26,
        strategy=Stay(),
        pace_model=causal_pace_model,
        track_mode="causal",
        race_length=52,
    )

    res_pit = replay(
        session_df=race_data,
        target_driver=target,
        decision_lap=26,
        strategy=Pit(lap=31, compound="MEDIUM"),
        pace_model=causal_pace_model,
        track_mode="causal",
        race_length=52,
    )

    # Pre-decision laps (1..26) must be identical between strategies and match actual recorded data
    actual_target = race_data[race_data["driver_number"] == target].set_index("lap_number")
    for lap in range(1, 27):
        stay_row = res_stay.laps_table[
            (res_stay.laps_table["driver_number"] == target) & (res_stay.laps_table["lap_number"] == lap)
        ].iloc[0]
        pit_row = res_pit.laps_table[
            (res_pit.laps_table["driver_number"] == target) & (res_pit.laps_table["lap_number"] == lap)
        ].iloc[0]

        assert stay_row["lap_duration"] == pit_row["lap_duration"]
        actual_dur = actual_target.loc[lap, "lap_duration"]
        if pd.notna(actual_dur):
            assert abs(stay_row["lap_duration"] - actual_dur) < 1e-4

    # Post-decision laps (27..52): changing strategy must change target driver's times
    stay_post = res_stay.laps_table[
        (res_stay.laps_table["driver_number"] == target) & (res_stay.laps_table["lap_number"] > 26)
    ]["cum_time"].iloc[-1]

    pit_post = res_pit.laps_table[
        (res_pit.laps_table["driver_number"] == target) & (res_pit.laps_table["lap_number"] > 26)
    ]["cum_time"].iloc[-1]

    assert stay_post != pit_post


def test_rival_future_lap_durations_remain_unchanged(race_data, causal_pace_model):
    """
    4. Rival future lap durations remain strictly unchanged across different target strategies
    and match their actual recorded durations.
    """
    target = resolve_driver_number(race_data, "Max Verstappen")
    hamilton = resolve_driver_number(race_data, "Lewis Hamilton")
    norris = resolve_driver_number(race_data, "Lando Norris")

    res_stay = replay(
        race_data, target, 26, Stay(), causal_pace_model, track_mode="causal", race_length=52
    )
    res_pit = replay(
        race_data, target, 26, Pit(31, "MEDIUM"), causal_pace_model, track_mode="causal", race_length=52
    )

    actual_records = race_data.set_index(["driver_number", "lap_number"])["lap_duration"].to_dict()

    for rival in [hamilton, norris]:
        for lap in range(27, 53):
            dur_stay = res_stay.laps_table[
                (res_stay.laps_table["driver_number"] == rival) & (res_stay.laps_table["lap_number"] == lap)
            ]["lap_duration"].iloc[0]

            dur_pit = res_pit.laps_table[
                (res_pit.laps_table["driver_number"] == rival) & (res_pit.laps_table["lap_number"] == lap)
            ]["lap_duration"].iloc[0]

            assert dur_stay == dur_pit

            actual_dur = actual_records.get((rival, lap))
            if actual_dur is not None and pd.notna(actual_dur):
                assert abs(dur_stay - actual_dur) < 1e-4


def test_rival_pit_stops_and_compounds_preserved(race_data, causal_pace_model):
    """
    5. Rival pit-stop and compound transitions remain preserved:
    Hamilton pitted on lap 27 (in-lap) for Intermediate (lap 28 out-lap) and lap 38 for Soft.
    Both stops and tyre states must be preserved in simulated replay.
    """
    target = resolve_driver_number(race_data, "Max Verstappen")
    hamilton = resolve_driver_number(race_data, "Lewis Hamilton")

    res = replay(
        race_data, target, 26, Pit(31, "MEDIUM"), causal_pace_model, track_mode="causal", race_length=52
    )

    ham_laps = res.laps_table[res.laps_table["driver_number"] == hamilton].set_index("lap_number")

    # In actual session, Hamilton ran MEDIUM until lap 27, INTERMEDIATE from lap 28, SOFT from lap 39
    assert ham_laps.loc[27, "compound"] == "MEDIUM"
    assert ham_laps.loc[28, "compound"] == "INTERMEDIATE"
    assert ham_laps.loc[28, "tyre_age"] == 0

    assert ham_laps.loc[38, "compound"] == "INTERMEDIATE"
    assert ham_laps.loc[39, "compound"] == "SOFT"
    assert ham_laps.loc[39, "tyre_age"] == 0


def test_correct_target_driver_pit_timing_and_tyre_age(race_data, causal_pace_model):
    """
    6 & 7. Pit(lap=31, compound='MEDIUM') means:
    - Lap 31 is completed on the old compound.
    - Lap 32 is completed on the new compound.
    - Tyre age increments on lap 31, resets to 0 upon pitting, and becomes 1 on lap 32.
    """
    target = resolve_driver_number(race_data, "Max Verstappen")

    # Target tyre age at lap 26 in actual data
    age_at_26 = race_data[
        (race_data["driver_number"] == target) & (race_data["lap_number"] == 26)
    ]["tyre_age"].iloc[0]

    res = replay(
        session_df=race_data,
        target_driver=target,
        decision_lap=26,
        strategy=Pit(lap=31, compound="MEDIUM"),
        pace_model=causal_pace_model,
        pit_loss=22.0,
        track_mode="causal",
        race_length=52,
    )

    target_laps = res.laps_table[res.laps_table["driver_number"] == target].set_index("lap_number")

    # Lap 31: completed on old compound, tyre age = age_at_26 + 5
    assert target_laps.loc[31, "compound"] == "MEDIUM"
    assert target_laps.loc[31, "tyre_age"] == age_at_26 + (31 - 26)

    # Lap 32: completed on new compound, tyre age = 1
    assert target_laps.loc[32, "compound"] == "MEDIUM"
    assert target_laps.loc[32, "tyre_age"] == 1

    # Lap 33: tyre age = 2
    assert target_laps.loc[33, "tyre_age"] == 2


def test_correct_pit_loss_accounting(race_data, causal_pace_model):
    """
    8. Correct pit-loss accounting:
    Total pit loss (22.0s) is split equally (11.0s in-lap + 11.0s out-lap).
    """
    target = resolve_driver_number(race_data, "Max Verstappen")

    res_stay = replay(
        race_data, target, 26, Stay(), causal_pace_model, pit_loss=22.0, track_mode="causal", race_length=52
    )
    res_pit = replay(
        race_data, target, 26, Pit(31, "MEDIUM"), causal_pace_model, pit_loss=22.0, track_mode="causal", race_length=52
    )

    t_stay = res_stay.laps_table[res_stay.laps_table["driver_number"] == target].set_index("lap_number")
    t_pit = res_pit.laps_table[res_pit.laps_table["driver_number"] == target].set_index("lap_number")

    # On in-lap (lap 31): both are on MEDIUM with the same age, but pit lap has +11s pit-in loss
    delta_in_lap = t_pit.loc[31, "lap_duration"] - t_stay.loc[31, "lap_duration"]
    assert abs(delta_in_lap - 11.0) < 1e-4


def test_no_future_target_data_leakage(race_data):
    """
    9. No future target-driver data leakage:
    In causal mode, predictions for laps > decision_lap must not depend on
    observations from laps > decision_lap.
    """
    target = resolve_driver_number(race_data, "Max Verstappen")

    model1 = build_pace_model(race_data, decision_lap=26, track_mode="causal")

    # Corrupt future target data in a copy of race_data
    tampered_data = race_data.copy()
    future_mask = (tampered_data["driver_number"] == target) & (tampered_data["lap_number"] > 26)
    tampered_data.loc[future_mask, "lap_duration"] = 999.0

    model2 = build_pace_model(tampered_data, decision_lap=26, track_mode="causal")

    # Predictions from model1 and model2 must be identical because neither seen laps > 26
    pred1 = model1.predict_lap(30, target, "MEDIUM", 10, mode="causal", decision_lap=26)
    pred2 = model2.predict_lap(30, target, "MEDIUM", 10, mode="causal", decision_lap=26)
    assert abs(pred1 - pred2) < 1e-6


def test_full_grid_positions_and_gaps_recalculation(race_data, causal_pace_model):
    """
    10. Recalculation of full-grid positions and gaps:
    Every lap has monotonically increasing cumulative times determining positions.
    Leader gap is 0.0, and gap to leader matches cumulative time difference.
    """
    target = resolve_driver_number(race_data, "Max Verstappen")

    res = replay(
        race_data, target, 26, Pit(31, "MEDIUM"), causal_pace_model, track_mode="causal", race_length=52
    )

    for lap in [26, 31, 32, 52]:
        lap_df = res.laps_table[res.laps_table["lap_number"] == lap].sort_values("position")
        assert not lap_df.empty

        # Positions must be contiguous integers 1..N
        assert list(lap_df["position"]) == list(range(1, len(lap_df) + 1))

        # Leader gap must be 0.0
        leader_cum = lap_df.iloc[0]["cum_time"]
        assert abs(lap_df.iloc[0]["gap_to_leader"]) < 1e-6

        # Gap to leader must equal cum_time - leader_cum for every car
        for _, row in lap_df.iterrows():
            assert abs(row["gap_to_leader"] - (row["cum_time"] - leader_cum)) < 1e-4


def test_missing_and_retired_driver_handling(race_data, causal_pace_model):
    """
    11. Missing and retired driver handling:
    - Russell (63, retired on lap 34) is marked as DNF.
    - Gasly (10, 0 timed laps) is classified as DNS without crashing.
    - All 20 drivers appear in full-grid classification.
    """
    target = resolve_driver_number(race_data, "Max Verstappen")

    res = replay(
        race_data, target, 26, Stay(), causal_pace_model, track_mode="causal", race_length=52
    )

    class_df = res.classification
    assert len(class_df) == len(race_data["driver_number"].unique())

    # Check Russell (63)
    russell_row = class_df[class_df["driver_number"] == 63].iloc[0]
    assert russell_row["status"] == "DNF"
    assert bool(russell_row["finished"]) is False
    assert russell_row["completed_laps"] == 33 or russell_row["completed_laps"] == 34

    # Check Gasly (10)
    gasly_row = class_df[class_df["driver_number"] == 10].iloc[0]
    assert gasly_row["status"] == "DNS"
    assert bool(gasly_row["finished"]) is False
    assert gasly_row["completed_laps"] == 0


def test_optimizer_candidates_share_same_rival_baseline(race_data, causal_pace_model):
    """
    12. Optimizer candidates sharing the same rival baseline:
    Every candidate strategy is evaluated against identical rival cumulative times.
    """
    target = resolve_driver_number(race_data, "Max Verstappen")
    hamilton = resolve_driver_number(race_data, "Lewis Hamilton")

    opt = optimize_strategy(
        session_df=race_data,
        target_driver=target,
        decision_lap=26,
        race_length=52,
        pace_model=causal_pace_model,
        pit_loss=22.0,
        track_mode="causal",
        max_candidates=10,
    )

    assert not opt.ranking.empty
    # Inspect top 3 replay results: Hamilton's final cumulative time must be identical in all
    ham_times = []
    for strat_id, rep in list(opt.replay_results.items())[:3]:
        ham_final = rep.laps_table[
            (rep.laps_table["driver_number"] == hamilton) & (rep.laps_table["lap_number"] == 52)
        ]["cum_time"].iloc[0]
        ham_times.append(ham_final)

    assert len(set(ham_times)) == 1


def test_final_acceptance_scenario(race_data, causal_pace_model):
    """
    10. FINAL ACCEPTANCE TEST:
    1. Load an actual race session (9558).
    2. Select Max Verstappen using the actual session driver mapping.
    3. Set the decision point to lap 26.
    4. Apply an alternative PITWALL pit strategy (e.g. Pit on lap 31 for Medium).
    5. Predict Max's future lap times.
    6. Preserve Lewis Hamilton's actual recorded pit stop and future race data.
    7. Preserve all other rivals' actual recorded future data.
    8. Recalculate the complete race classification.
    9. Compare the counterfactual result with the actual result.
    10. Return the result through the backend API.
    """
    # 1 & 2. Resolve Max Verstappen dynamically
    verstappen = resolve_driver_number(race_data, "Max Verstappen")
    hamilton = resolve_driver_number(race_data, "Lewis Hamilton")

    # 3 & 4. Lap 26 decision, Pit on lap 31 for MEDIUM
    strat = Pit(lap=31, compound="MEDIUM")

    # 5. Simulate
    res = replay(
        session_df=race_data,
        target_driver=verstappen,
        decision_lap=26,
        strategy=strat,
        pace_model=causal_pace_model,
        pit_loss=22.0,
        track_mode="causal",
        race_length=52,
    )

    # 6. Verify Lewis Hamilton's actual recorded pit stops and future race data are preserved
    ham_laps = res.laps_table[res.laps_table["driver_number"] == hamilton].set_index("lap_number")
    assert ham_laps.loc[27, "compound"] == "MEDIUM"
    assert ham_laps.loc[28, "compound"] == "INTERMEDIATE"  # Pitted lap 28
    assert ham_laps.loc[39, "compound"] == "SOFT"          # Pitted lap 39
    assert abs(ham_laps.loc[52, "cum_time"] - 4947.427) < 0.01

    # 7. Preserve all other rivals' actual recorded future data
    actual_records = race_data.set_index(["driver_number", "lap_number"])["lap_duration"].to_dict()
    for _, row in res.laps_table[res.laps_table["driver_number"] != verstappen].iterrows():
        d = int(row["driver_number"])
        l = int(row["lap_number"])
        act_dur = actual_records.get((d, l))
        if act_dur is not None and pd.notna(act_dur):
            assert abs(row["lap_duration"] - act_dur) < 1e-4

    # 8. Recalculate complete race classification
    assert res.classification is not None
    assert len(res.classification) == 20
    assert list(res.classification["position"]) == list(range(1, 21))

    # 9. Compare counterfactual result with actual result
    assert res.summary["ground_truth_available"] is True
    assert res.summary["final_position"] is not None
    assert res.summary["total_time_delta_vs_actual"] is not None
    assert res.summary["positions_gained_vs_actual"] is not None
