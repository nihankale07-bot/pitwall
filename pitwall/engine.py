"""Replay engine for counterfactual race strategy simulation."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd


# ============================================================
# ACTIONS AND RESULT STRUCTURES
# ============================================================

@dataclass(frozen=True)
class Stay:
    """Stay out without pitting."""
    pass


@dataclass(frozen=True)
class Pit:
    """Pit on a specific lap for a new compound."""
    lap: int
    compound: str


@dataclass(frozen=True)
class Strategy:
    """Multi-stop strategy consisting of (pit_lap, new_compound)."""
    pit_sequence: Tuple[Tuple[int, str], ...] = field(default_factory=tuple)
    description: str = ""


Action = Union[Stay, Pit, Strategy]


@dataclass
class ReplayResult:
    """Output of a counterfactual race replay."""
    session_key: int
    target_driver: int
    decision_lap: int
    action: Action
    ground_truth_available: bool
    laps_table: pd.DataFrame
    summary: Dict[str, Union[int, float, bool, str, None]]
    classification: Optional[pd.DataFrame] = None


# ============================================================
# MAIN REPLAY ENGINE
# ============================================================

def replay(
    session_df: pd.DataFrame,
    target_driver: int,
    decision_lap: int,
    strategy: Optional[Action] = None,
    pace_model=None,
    pit_loss: float = 22.0,
    track_mode: str = "replay",
    race_length: Optional[int] = None,
) -> Union[ReplayResult, Dict[str, ReplayResult]]:
    """
    Replay a race with a counterfactual strategy for the target driver.

    Target-only counterfactual replay:
    - Target driver follows the alternative pit strategy and pace model.
    - All non-target drivers (rivals) follow their actual recorded race trajectory.
    - Full-grid positions and cumulative times are recalculated.

    track_mode:
        'replay': Target future pace uses observed lap-specific effects.
        'causal': Target future pace uses causal forecasts without future track data.
    """

    # --------------------------------------------------------
    # 1. INPUT VALIDATION AND PREPARATION
    # --------------------------------------------------------

    if session_df is None or session_df.empty:
        raise ValueError("session_df must contain race-lap data.")

    required = {
        "driver_number",
        "lap_number",
        "lap_duration",
        "compound",
        "tyre_age",
    }

    missing = required - set(session_df.columns)
    if missing:
        raise ValueError(
            f"session_df is missing required columns: {sorted(missing)}"
        )

    if track_mode not in {"replay", "causal"}:
        raise ValueError(
            "track_mode must be either 'replay' or 'causal'."
        )

    df = session_df.copy()

    df["lap_number"] = pd.to_numeric(
        df["lap_number"],
        errors="coerce",
    )
    df["lap_duration"] = pd.to_numeric(
        df["lap_duration"],
        errors="coerce",
    )

    if df["lap_number"].isna().any():
        raise ValueError("lap_number contains invalid values.")

    max_available_lap = int(df["lap_number"].max())

    if race_length is None:
        race_length = max_available_lap

    if race_length > max_available_lap:
        raise ValueError(
            f"race_length {race_length} exceeds maximum "
            f"lap {max_available_lap} present in session data."
        )

    race_length = int(race_length)
    decision_lap = int(decision_lap)
    target_driver = int(target_driver)

    if race_length < 1:
        raise ValueError("race_length must be positive.")

    if not 1 <= decision_lap < race_length:
        raise ValueError(
            "decision_lap must be between 1 and race_length - 1."
        )

    if target_driver not in set(df["driver_number"].unique()):
        raise ValueError(
            f"Target driver {target_driver} is not present in session_df."
        )

    if pace_model is not None and not pace_model.fitted:
        raise ValueError("The supplied pace model must be fitted.")

    # --------------------------------------------------------
    # 2. TARGET DRIVER HISTORY AT DECISION TIME
    # --------------------------------------------------------

    target_history = (
        df.loc[
            (df["driver_number"] == target_driver)
            & (df["lap_number"] <= decision_lap)
        ]
        .sort_values("lap_number")
    )

    decision_rows = target_history.loc[
        target_history["lap_number"] == decision_lap
    ]

    if decision_rows.empty:
        raise ValueError(
            f"Target driver has no recorded lap at decision_lap={decision_lap}."
        )

    current_row = decision_rows.iloc[-1]

    # --------------------------------------------------------
    # 3. GENERATE CANDIDATES IF NO STRATEGY IS PROVIDED
    # --------------------------------------------------------

    if strategy is None:
        from pitwall.strategy_generator import (
            generate_multi_stop_candidates,
        )

        candidates = generate_multi_stop_candidates(
            race_df=df,
            target_driver=target_driver,
            decision_lap=decision_lap,
            race_length=race_length,
            max_stops=2,
            supported_compounds={"SOFT", "MEDIUM", "HARD"},
        )

        results = {}
        for _, row in candidates.iterrows():
            candidate_strategy = Strategy(
                pit_sequence=tuple(row["pit_sequence"]),
                description=str(row["description"]),
            )
            results[row["strategy_id"]] = replay(
                session_df=df,
                target_driver=target_driver,
                decision_lap=decision_lap,
                strategy=candidate_strategy,
                pace_model=pace_model,
                pit_loss=pit_loss,
                track_mode=track_mode,
                race_length=race_length,
            )

        return results

    # --------------------------------------------------------
    # 4. NORMALIZE STRATEGY
    # --------------------------------------------------------

    if isinstance(strategy, Stay):
        pit_schedule = {}

    elif isinstance(strategy, Pit):
        pit_schedule = {
            int(strategy.lap): str(strategy.compound)
        }

    elif isinstance(strategy, Strategy):
        scheduled_laps = [
            int(lap)
            for lap, _ in strategy.pit_sequence
        ]
        if len(scheduled_laps) != len(set(scheduled_laps)):
            raise ValueError(
                "A strategy cannot contain multiple stops on the same lap."
            )
        pit_schedule = {
            int(lap): str(compound)
            for lap, compound in strategy.pit_sequence
        }

    else:
        raise TypeError(
            f"Unsupported strategy type: {type(strategy)}"
        )

    # --------------------------------------------------------
    # 5. TARGET DRIVER STATE & PIT SCHEDULE VALIDATION
    # --------------------------------------------------------

    target_actual_all = df.loc[df["driver_number"] == target_driver]
    target_recorded_laps = int(target_actual_all["lap_number"].max())

    target_final_record = df.loc[
        (df["driver_number"] == target_driver)
        & (df["lap_number"] == race_length)
    ]
    ground_truth_available = (
        not target_final_record.empty
        and pd.notna(target_final_record["lap_duration"].iloc[0])
    )

    sim_end_lap = race_length
    sim_compound = current_row["compound"]
    sim_tyre_age = (
        int(current_row["tyre_age"])
        if pd.notna(current_row["tyre_age"])
        else 0
    )

    invalid_laps = [
        lap
        for lap in pit_schedule
        if lap <= decision_lap or lap >= sim_end_lap
    ]
    if invalid_laps:
        raise ValueError(
            f"Pit laps must be after decision_lap and before "
            f"the final lap. Invalid laps: {invalid_laps}"
        )

    if any(
        not isinstance(compound, str) or not compound.strip()
        for compound in pit_schedule.values()
    ):
        raise ValueError(
            "Every pit stop must specify a valid compound."
        )

    pit_loss = float(pit_loss)
    if not np.isfinite(pit_loss) or pit_loss < 0:
        raise ValueError(
            "pit_loss must be finite and non-negative."
        )

    pit_loss_per_lap = pit_loss / 2.0

    # --------------------------------------------------------
    # 6. ACTIVE RACE FIELD & ACTUAL OBSERVATIONS LOOKUP
    # --------------------------------------------------------

    drivers = sorted(df["driver_number"].unique().tolist())

    actual_records = (
        df.set_index(["driver_number", "lap_number"])[
            ["lap_duration", "compound", "tyre_age"]
        ]
        .to_dict(orient="index")
    )

    # --------------------------------------------------------
    # 7. TARGET DRIVER PRE-DECISION TRAJECTORY
    # --------------------------------------------------------

    target_sim_durations = {}
    target_sim_compounds = {}
    target_sim_tyre_ages = {}

    for lap in range(1, decision_lap + 1):
        record = actual_records.get((target_driver, lap))
        if record is None or pd.isna(record["lap_duration"]):
            continue
        target_sim_durations[lap] = float(record["lap_duration"])
        target_sim_compounds[lap] = record["compound"]
        target_sim_tyre_ages[lap] = (
            int(record["tyre_age"])
            if pd.notna(record["tyre_age"])
            else 0
        )

    # --------------------------------------------------------
    # 8. SIMULATE TARGET DRIVER FUTURE LAPS
    # --------------------------------------------------------

    clean_history = target_history
    if "is_clean_lap" in clean_history.columns:
        clean_history = clean_history.loc[
            clean_history["is_clean_lap"].fillna(False)
        ]

    recent_pace = clean_history["lap_duration"].dropna().tail(3)
    if recent_pace.empty:
        recent_pace = target_history["lap_duration"].dropna().tail(3)

    if recent_pace.empty:
        raise ValueError(
            "Cannot calculate fallback pace for target driver."
        )

    placeholder_pace = float(recent_pace.median())

    for lap in range(decision_lap + 1, sim_end_lap + 1):
        is_pit_now = lap in pit_schedule

        if is_pit_now:
            # In-lap: complete lap on current compound, then pit
            sim_tyre_age += 1

            if pace_model is not None:
                lap_time = pace_model.predict_lap(
                    lap_number=lap,
                    driver_number=target_driver,
                    compound=sim_compound,
                    tyre_age=sim_tyre_age,
                    mode=track_mode,
                    decision_lap=decision_lap,
                )
            else:
                lap_time = placeholder_pace

            lap_time += pit_loss_per_lap

            target_sim_durations[lap] = lap_time
            target_sim_compounds[lap] = sim_compound
            target_sim_tyre_ages[lap] = sim_tyre_age

            # Switch to new compound and reset tyre age for following lap
            sim_compound = pit_schedule[lap]
            sim_tyre_age = 0

        else:
            sim_tyre_age += 1

            if pace_model is not None:
                lap_time = pace_model.predict_lap(
                    lap_number=lap,
                    driver_number=target_driver,
                    compound=sim_compound,
                    tyre_age=sim_tyre_age,
                    mode=track_mode,
                    decision_lap=decision_lap,
                )
            else:
                lap_time = placeholder_pace

            # Out-lap penalty if previous lap was pit-in lap
            if (lap - 1) in pit_schedule:
                lap_time += pit_loss_per_lap

            target_sim_durations[lap] = lap_time
            target_sim_compounds[lap] = sim_compound
            target_sim_tyre_ages[lap] = sim_tyre_age

    # --------------------------------------------------------
    # 9. SIMULATE THE FIELD (RECALCULATE FULL-GRID ORDER)
    # --------------------------------------------------------

    all_lap_rows = []

    driver_cum_times = {driver: 0.0 for driver in drivers}
    driver_completed_laps = {driver: 0 for driver in drivers}
    driver_last_compound = {driver: None for driver in drivers}
    driver_last_tyre_age = {driver: None for driver in drivers}

    for lap in range(1, sim_end_lap + 1):
        active_drivers = []
        lap_durations = {}
        lap_compounds = {}
        lap_tyre_ages = {}
        lap_gt_avail = {}

        for driver in drivers:
            if driver == target_driver:
                duration = target_sim_durations.get(lap)
                compound = target_sim_compounds.get(lap)
                tyre_age = target_sim_tyre_ages.get(lap)
                gt_available = (lap <= target_recorded_laps)
            else:
                # Rival drivers: read actual recorded observations directly
                record = actual_records.get((driver, lap))
                if record is not None and pd.notna(record["lap_duration"]):
                    duration = float(record["lap_duration"])
                    compound = record["compound"]
                    raw_age = record["tyre_age"]
                    tyre_age = int(raw_age) if pd.notna(raw_age) else None
                    gt_available = True
                else:
                    duration = None
                    compound = None
                    tyre_age = None
                    gt_available = False

            if duration is not None and pd.notna(duration):
                lap_durations[driver] = duration
                lap_compounds[driver] = compound
                lap_tyre_ages[driver] = tyre_age
                lap_gt_avail[driver] = gt_available
                driver_cum_times[driver] += duration
                driver_completed_laps[driver] += 1
                driver_last_compound[driver] = compound
                driver_last_tyre_age[driver] = tyre_age
                active_drivers.append(driver)

        if not active_drivers:
            continue

        sorted_active = sorted(
            active_drivers,
            key=lambda d: driver_cum_times[d],
        )

        leader_time = driver_cum_times[sorted_active[0]]

        for index, driver in enumerate(sorted_active):
            cumulative_time = driver_cum_times[driver]
            gap_leader = cumulative_time - leader_time
            gap_ahead = (
                cumulative_time - driver_cum_times[sorted_active[index - 1]]
                if index > 0
                else 0.0
            )
            gap_behind = (
                driver_cum_times[sorted_active[index + 1]] - cumulative_time
                if index < len(sorted_active) - 1
                else 0.0
            )

            all_lap_rows.append({
                "lap_number": lap,
                "driver_number": driver,
                "lap_duration": lap_durations[driver],
                "cum_time": cumulative_time,
                "position": index + 1,
                "gap_to_leader": gap_leader,
                "gap_ahead": gap_ahead,
                "gap_behind": gap_behind,
                "compound": lap_compounds[driver],
                "tyre_age": lap_tyre_ages[driver],
                "is_target": (driver == target_driver),
                "ground_truth_available": lap_gt_avail[driver],
            })

    # --------------------------------------------------------
    # 10. BUILD RESULT TABLE
    # --------------------------------------------------------

    result_df = pd.DataFrame(all_lap_rows)

    if result_df.empty:
        raise RuntimeError("Replay generated no lap results.")

    # --------------------------------------------------------
    # 11. PROJECTED FINAL RESULT FOR TARGET DRIVER
    # --------------------------------------------------------

    target_final = result_df.loc[
        (result_df["driver_number"] == target_driver)
        & (result_df["lap_number"] == sim_end_lap)
    ]

    if not target_final.empty:
        final_position = int(target_final["position"].iloc[0])
        final_cumulative_time = float(target_final["cum_time"].iloc[0])
    else:
        final_position = None
        final_cumulative_time = None

    # --------------------------------------------------------
    # 12. HISTORICAL COMPARISON
    # --------------------------------------------------------

    if ground_truth_available and final_position is not None:
        actual_target_end = df.loc[
            (df["driver_number"] == target_driver)
            & (df["lap_number"] == sim_end_lap)
        ]

        actual_position = (
            int(actual_target_end["position"].iloc[0])
            if (
                not actual_target_end.empty
                and "position" in df.columns
                and pd.notna(actual_target_end["position"].iloc[0])
            )
            else None
        )

        actual_time = float(
            df.loc[
                (df["driver_number"] == target_driver)
                & (df["lap_number"] <= sim_end_lap),
                "lap_duration",
            ].sum()
        )

        time_delta = final_cumulative_time - actual_time
        position_gain = (
            actual_position - final_position
            if actual_position is not None
            else None
        )
    else:
        time_delta = None
        position_gain = None

    summary = {
        "target_driver": target_driver,
        "decision_lap": decision_lap,
        "race_length": race_length,
        "ground_truth_available": ground_truth_available,
        "final_position": final_position,
        "final_cumulative_time": final_cumulative_time,
        "total_time_delta_vs_actual": time_delta,
        "positions_gained_vs_actual": position_gain,
    }

    # --------------------------------------------------------
    # 13. FULL-GRID RACE CLASSIFICATION
    # --------------------------------------------------------

    lead_lap_drivers = []
    lapped_finishers = []
    retired_drivers = []
    dns_drivers = []

    for driver in drivers:
        completed = driver_completed_laps[driver]
        c_time = driver_cum_times[driver]
        l_comp = driver_last_compound[driver]
        l_age = driver_last_tyre_age[driver]

        if completed == sim_end_lap:
            lead_lap_drivers.append({
                "driver_number": driver,
                "completed_laps": completed,
                "cum_time": c_time,
                "compound": l_comp,
                "tyre_age": l_age,
                "is_target": (driver == target_driver),
                "status": "FINISHED",
                "finished": True,
            })
        elif completed >= int(0.9 * sim_end_lap):
            lapped_finishers.append({
                "driver_number": driver,
                "completed_laps": completed,
                "cum_time": c_time,
                "compound": l_comp,
                "tyre_age": l_age,
                "is_target": (driver == target_driver),
                "status": "FINISHED",
                "finished": True,
            })
        elif completed > 0:
            retired_drivers.append({
                "driver_number": driver,
                "completed_laps": completed,
                "cum_time": c_time,
                "compound": l_comp,
                "tyre_age": l_age,
                "is_target": (driver == target_driver),
                "status": "DNF",
                "finished": False,
            })
        else:
            dns_drivers.append({
                "driver_number": driver,
                "completed_laps": 0,
                "cum_time": None,
                "compound": l_comp,
                "tyre_age": l_age,
                "is_target": (driver == target_driver),
                "status": "DNS",
                "finished": False,
            })

    lead_lap_drivers.sort(key=lambda x: x["cum_time"])
    lapped_finishers.sort(key=lambda x: (-x["completed_laps"], x["cum_time"]))
    retired_drivers.sort(key=lambda x: (-x["completed_laps"], x["cum_time"]))
    dns_drivers.sort(key=lambda x: x["driver_number"])

    all_classified = lead_lap_drivers + lapped_finishers + retired_drivers + dns_drivers
    leader_final_time = lead_lap_drivers[0]["cum_time"] if lead_lap_drivers else None

    for pos_idx, entry in enumerate(all_classified):
        pos = pos_idx + 1
        entry["position"] = pos
        c_time = entry["cum_time"]

        if entry["status"] == "FINISHED" and c_time is not None and leader_final_time is not None:
            entry["gap_to_leader"] = float(c_time - leader_final_time)
            if pos_idx > 0 and all_classified[pos_idx - 1]["cum_time"] is not None:
                entry["gap_ahead"] = float(c_time - all_classified[pos_idx - 1]["cum_time"])
            else:
                entry["gap_ahead"] = 0.0
        else:
            entry["gap_to_leader"] = None
            entry["gap_ahead"] = None

        entry["lap_number"] = entry["completed_laps"]
        last_lap_num = entry["completed_laps"]
        if entry["is_target"]:
            entry["lap_duration"] = target_sim_durations.get(last_lap_num)
        else:
            rec = actual_records.get((entry["driver_number"], last_lap_num))
            entry["lap_duration"] = float(rec["lap_duration"]) if (rec and pd.notna(rec.get("lap_duration"))) else None

        entry["gap_behind"] = None
        entry["ground_truth_available"] = (
            ground_truth_available if entry["is_target"] else (entry["completed_laps"] > 0)
        )

    classification_df = pd.DataFrame(all_classified)

    # --------------------------------------------------------
    # 14. RETURN RESULT
    # --------------------------------------------------------

    return ReplayResult(
        session_key=(
            int(df["session_key"].iloc[0])
            if "session_key" in df.columns
            else 9558
        ),
        target_driver=target_driver,
        decision_lap=decision_lap,
        action=strategy,
        ground_truth_available=ground_truth_available,
        laps_table=result_df,
        summary=summary,
        classification=classification_df,
    )


# ============================================================
# ACTUAL RACE REPLAY
# ============================================================

def replay_actual(
    session_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate actual cumulative race times and final positions.

    Retrospective utility only. Uses the complete historical session.
    """

    df = session_df.copy()

    max_laps = int(df["lap_number"].max())

    df = df.sort_values(
        ["driver_number", "lap_number"]
    )

    df["cum_time"] = (
        df.groupby("driver_number")["lap_duration"]
        .cumsum()
    )

    final_df = df.loc[
        df["lap_number"] == max_laps
    ].copy()

    final_df["computed_position"] = (
        final_df["cum_time"]
        .rank(method="min")
        .astype(int)
    )

    return (
        final_df
        .sort_values("computed_position")
        .reset_index(drop=True)
    )
