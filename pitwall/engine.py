
"""Replay engine for counterfactual race strategy simulation."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
# Clean up imports: remove unused rival modules
# from .rival_strategy import generate_rival_strategies
# from .rival_probability import assign_rival_strategy_probabilities
# from .rival_scenario import simulate_rival_scenarios
from .rival_probability import assign_rival_strategy_probabilities
from .rival_scenario import simulate_rival_scenarios
import pandas as pd


# NOTE: In causal mode rivals are assumed to make no future pit stops. This limitation is intentional and documented here.
# ACTIONS AND RESULT STRUCTURES

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


# NOTE: In causal mode rivals are assumed to make no future pit stops. This limitation is intentional and documented here.

# RIVAL STATE PRECOMPUTATION
# NOTE: In causal mode rivals are assumed to make no future pit stops. This limitation is intentional and documented here.


def _build_rival_states(
    df: pd.DataFrame,
    drivers,
    target_driver: int,
    decision_lap: int,
) -> Dict[int, dict]:
    """
    Build one compact decision-time state per rival.

    Only observations at or before decision_lap are used.

    This avoids repeatedly filtering DataFrames, sorting histories,
    and extracting Pandas rows during every simulated lap.
    """

    rival_drivers = [
        driver for driver in drivers
        if driver != target_driver
    ]

    states = {
        driver: {
            "has_history": False,
            "compound": None,
            "tyre_age": None,
            "fallback_pace": np.nan,
        }
        for driver in rival_drivers
    }

    if not rival_drivers:
        return states

    history_columns = [
        "driver_number",
        "lap_number",
        "compound",
        "tyre_age",
        "lap_duration",
    ]

    if "is_clean_lap" in df.columns:
        history_columns.append("is_clean_lap")

    causal_history = (
        df.loc[
            df["lap_number"] <= decision_lap,
            history_columns,
        ]
        .sort_values(
            ["driver_number", "lap_number"],
            kind="mergesort",
        )
    )

    for driver, history in causal_history.groupby(
        "driver_number",
        sort=False,
    ):

        if driver == target_driver or driver not in states:
            continue

        if history.empty:
            continue

        compound = history["compound"].iat[-1]

        latest_age = history["tyre_age"].iat[-1]

        tyre_age = (
            int(latest_age)
            if pd.notna(latest_age)
            else 0
        )

        clean_history = history

        if "is_clean_lap" in history.columns:
            clean_history = history.loc[
                history["is_clean_lap"].fillna(False)
            ]

        recent = (
            clean_history["lap_duration"]
            .dropna()
            .tail(3)
        )

        if recent.empty:
            recent = (
                history["lap_duration"]
                .dropna()
                .tail(3)
            )

        fallback_pace = (
            float(recent.median())
            if not recent.empty
            else np.nan
        )

        states[driver] = {
            "has_history": True,
            "compound": compound,
            "tyre_age": tyre_age,
            "fallback_pace": fallback_pace,
        }

    return states


# NOTE: In causal mode rivals are assumed to make no future pit stops. This limitation is intentional and documented here.

# RIVAL PACE FORECASTING
# NOTE: In causal mode rivals are assumed to make no future pit stops. This limitation is intentional and documented here.


def _project_rival_lap_time(
    df,
    driver_number,
    decision_lap,
    lap_number,
    pace_model=None,
    history=None,
    rival_state=None,
):
    """
    Project rival lap time using only decision-time information.

    Preferred path:
        Use precomputed rival_state.

    Compatibility path:
        Accept an existing history DataFrame or construct one
        from df when no cached state is supplied.
    """

    if rival_state is not None:

        if not rival_state["has_history"]:
            return np.nan

        compound = rival_state["compound"]
        tyre_age = rival_state["tyre_age"]
        fallback_pace = rival_state["fallback_pace"]

    else:

        if history is None:
            history = df.loc[
                (df["driver_number"] == driver_number)
                & (df["lap_number"] <= decision_lap)
            ].sort_values("lap_number")

        if history.empty:
            return np.nan

        compound = history["compound"].iat[-1]

        latest_age = history["tyre_age"].iat[-1]

        tyre_age = (
            int(latest_age)
            if pd.notna(latest_age)
            else 0
        )

        clean_history = history

        if "is_clean_lap" in history.columns:
            clean_history = history.loc[
                history["is_clean_lap"].fillna(False)
            ]

        recent = (
            clean_history["lap_duration"]
            .dropna()
            .tail(3)
        )

        if recent.empty:
            recent = (
                history["lap_duration"]
                .dropna()
                .tail(3)
            )

        fallback_pace = (
            float(recent.median())
            if not recent.empty
            else np.nan
        )

    projected_age = tyre_age + (
        lap_number - decision_lap
    )

    if pace_model is not None:

        return pace_model.predict_lap(
            lap_number=lap_number,
            driver_number=driver_number,
            compound=compound,
            tyre_age=projected_age,
            mode="causal",
            decision_lap=decision_lap,
        )

    return fallback_pace


# NOTE: In causal mode rivals are assumed to make no future pit stops. This limitation is intentional and documented here.
# MAIN REPLAY ENGINE
# NOTE: In causal mode rivals are assumed to make no future pit stops. This limitation is intentional and documented here.


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

    replay:
        Uses actual future rival lap times.

    causal:
        Forecasts future rival pace using decision-time information.

    Important:
        Causal rival forecasts assume rivals make no future pit stops.
        The rival scenario engine handles alternative rival strategies.
    """

    # --------------------------------------------------------
    # 1. INPUT VALIDATION
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

        
    # --------------------------------------------------------
    # 1. INPUT VALIDATION AND DATA PREPARATION
    # --------------------------------------------------------

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
            f"Target driver has no recorded lap at "
            f"decision_lap={decision_lap}."
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
            int(strategy.lap): strategy.compound
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
            int(lap): compound
            for lap, compound in strategy.pit_sequence
        }

    else:

        raise TypeError(
            f"Unsupported strategy type: {type(strategy)}"
        )

    # --------------------------------------------------------
    # 5. TARGET DRIVER STATE
    # --------------------------------------------------------

    target_recorded_laps = int(
        target_history["lap_number"].max()
    )

    target_final_record = df.loc[
        (df["driver_number"] == target_driver)
        & (df["lap_number"] == race_length)
    ]

    ground_truth_available = not target_final_record.empty

    sim_end_lap = race_length

    sim_compound = current_row["compound"]

    sim_tyre_age = (
        int(current_row["tyre_age"])
        if pd.notna(current_row["tyre_age"])
        else 0
    )

    # --------------------------------------------------------
    # 6. VALIDATE PIT SCHEDULE
    # --------------------------------------------------------

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
    # 7. IDENTIFY RACE STARTERS
    # --------------------------------------------------------

    # Retains the existing provisional starter-selection logic.
    starter_counts = (
        df.groupby("driver_number")["lap_number"]
        .nunique()
    )

    drivers = sorted(
        starter_counts[starter_counts > 1].index.tolist()
    )

    if target_driver not in drivers:
        raise ValueError(
            f"Target driver {target_driver} is not in the active race field."
        )

    # --------------------------------------------------------
    # 8. INDEX ACTUAL RACE RECORDS
    # --------------------------------------------------------

    actual_records = (
        df.set_index(["driver_number", "lap_number"])[
            ["lap_duration", "compound", "tyre_age"]
        ]
        .to_dict(orient="index")
    )

    # --------------------------------------------------------
    # 9. COPY ACTUAL TARGET HISTORY
    # --------------------------------------------------------

    target_sim_durations = {}
    target_sim_compounds = {}
    target_sim_tyre_ages = {}

    for lap in range(1, decision_lap + 1):

        record = actual_records.get(
            (target_driver, lap)
        )

        if record is None:
            continue

        target_sim_durations[lap] = record["lap_duration"]
        target_sim_compounds[lap] = record["compound"]

        target_sim_tyre_ages[lap] = (
            int(record["tyre_age"])
            if pd.notna(record["tyre_age"])
            else 0
        )

    # --------------------------------------------------------
    # 10. FALLBACK TARGET PACE
    # --------------------------------------------------------

    clean_history = target_history

    if "is_clean_lap" in clean_history.columns:
        clean_history = clean_history.loc[
            clean_history["is_clean_lap"].fillna(False)
        ]

    recent_pace = (
        clean_history["lap_duration"]
        .dropna()
        .tail(3)
    )

    if recent_pace.empty:
        recent_pace = (
            target_history["lap_duration"]
            .dropna()
            .tail(3)
        )

    if recent_pace.empty:
        raise ValueError(
            "Cannot calculate fallback pace for target driver."
        )

    placeholder_pace = float(recent_pace.median())

    # --------------------------------------------------------
    # 11. SIMULATE TARGET DRIVER FUTURE LAPS
    # --------------------------------------------------------

    for lap in range(decision_lap + 1, sim_end_lap + 1):

        is_pit_now = lap in pit_schedule

        if is_pit_now:

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

            if (lap - 1) in pit_schedule:
                lap_time += pit_loss_per_lap

            target_sim_durations[lap] = lap_time
            target_sim_compounds[lap] = sim_compound
            target_sim_tyre_ages[lap] = sim_tyre_age

    # --------------------------------------------------------
    # 12. PRECOMPUTE RIVAL STATES
    # --------------------------------------------------------

    rival_states = _build_rival_states(
        df=df,
        drivers=drivers,
        target_driver=target_driver,
        decision_lap=decision_lap,
    )

    # --------------------------------------------------------
    # 13. SIMULATE THE FIELD
    # --------------------------------------------------------

    all_lap_rows = []

    driver_cum_times = {
        driver: 0.0
        for driver in drivers
    }

    for lap in range(1, sim_end_lap + 1):

        active_drivers = []
        lap_durations = {}

        # ----------------------------------------------------
        # 13A. Calculate lap durations and cumulative times
        # ----------------------------------------------------

                    if driver == target_driver:
                # Use the counterfactual simulation for the target driver
                duration = target_sim_durations.get(lap, np.nan)
                # For the target driver, compound and tyre_age are filled later from the simulated dicts
                compound = None
                tyre_age = None
                status = None
            else:
                # Rivals: pull the recorded data directly
                record = actual_records.get((driver, lap))
                if record is not None:
                    duration = record["lap_duration"]
                    compound = record.get("compound")
                    raw_age = record.get("tyre_age")
                    tyre_age = int(raw_age) if pd.notna(raw_age) else None
                    status = record.get("status") if "status" in record else None
                else:
                    # No recorded row for this lap (missing telemetry, driver did not start, or race ended early)
                    duration = np.nan
                    compound = None
                    tyre_age = None
                    status = None


            if driver == target_driver:

                duration = target_sim_durations.get(
                    lap,
                    np.nan,
                )

            // In causal mode we still use recorded rival data (target‑only counterfactual)
// The old projection branch is removed. All rivals are handled by the
// ``else`` branch below which fetches the actual recorded row.


                duration = _project_rival_lap_time(
                    df=df,
                    driver_number=driver,
                    decision_lap=decision_lap,
                    lap_number=lap,
                    pace_model=pace_model,
                    rival_state=rival_states[driver],
                )

            else:

                record = actual_records.get(
                    (driver, lap)
                )

                duration = (
                    record["lap_duration"]
                    if record is not None
                    else np.nan
                )

            lap_durations[driver] = duration

            if pd.notna(duration):
                driver_cum_times[driver] += float(duration)
                active_drivers.append(driver)

        # ----------------------------------------------------
        # 13B. Calculate running positions
        # ----------------------------------------------------

        sorted_active = sorted(
            active_drivers,
            key=lambda driver: driver_cum_times[driver],
        )

        if not sorted_active:
            continue

        leader_time = driver_cum_times[sorted_active[0]]

        # ----------------------------------------------------
        # 13C. Store lap-level results
        # ----------------------------------------------------

        for index, driver in enumerate(sorted_active):

            cumulative_time = driver_cum_times[driver]

            gap_leader = cumulative_time - leader_time

            gap_ahead = (
                cumulative_time
                - driver_cum_times[sorted_active[index - 1]]
                if index > 0
                else 0.0
            )

            gap_behind = (
                driver_cum_times[sorted_active[index + 1]]
                - cumulative_time
                if index < len(sorted_active) - 1
                else 0.0
            )

            if driver == target_driver:

                compound = target_sim_compounds.get(lap)
                tyre_age = target_sim_tyre_ages.get(lap)
                duration = target_sim_durations.get(lap)

                gt_available = lap <= target_recorded_laps

            // In causal mode we still use recorded rival data (target‑only counterfactual)
// The old projection branch is removed. All rivals are handled by the
// ``else`` branch below which fetches the actual recorded row.


                state = rival_states[driver]

                compound = state["compound"]

                tyre_age = state["tyre_age"]

                if tyre_age is not None:
                    tyre_age += lap - decision_lap

                duration = lap_durations[driver]
                gt_available = False

            else:

                record = actual_records.get(
                    (driver, lap)
                )

                compound = (
                    record["compound"]
                    if record is not None
                    else None
                )

                recorded_age = (
                    record["tyre_age"]
                    if record is not None
                    else None
                )

                tyre_age = (
                    int(recorded_age)
                    if pd.notna(recorded_age)
                    else None
                )

                duration = lap_durations[driver]
                gt_available = True

            all_lap_rows.append({

                "lap_number": lap,
                "driver_number": driver,
                "lap_duration": duration,
                "cum_time": cumulative_time,
                "position": index + 1,
                "gap_to_leader": gap_leader,
                "gap_ahead": gap_ahead,
                "gap_behind": gap_behind,
                "compound": compound,
                "tyre_age": tyre_age,
                "is_target": driver == target_driver,
                "ground_truth_available": gt_available,

            })

    # --------------------------------------------------------
    # 14. BUILD RESULT TABLE
    # --------------------------------------------------------

    result_df = pd.DataFrame(all_lap_rows)

    if result_df.empty:
        raise RuntimeError(
            "Replay generated no lap results."
        )

    # --------------------------------------------------------
    # 15. PROJECTED FINAL RESULT
    # --------------------------------------------------------

    target_final = result_df.loc[
        (result_df["driver_number"] == target_driver)
        & (result_df["lap_number"] == sim_end_lap)
    ]

    if not target_final.empty:

        final_position = int(
            target_final["position"].iloc[0]
        )

        final_cumulative_time = float(
            target_final["cum_time"].iloc[0]
        )

    else:

        final_position = None
        final_cumulative_time = None

    # --------------------------------------------------------
    # 16. HISTORICAL COMPARISON
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

        actual_time = (
            target_history["lap_duration"].sum()
            + df.loc[
                (df["driver_number"] == target_driver)
                & (df["lap_number"] > decision_lap)
                & (df["lap_number"] <= race_length),
                "lap_duration",
            ].sum()
        )

        time_delta = (
            final_cumulative_time - actual_time
        )

        position_gain = (
            actual_position - final_position
            if actual_position is not None
            else None
        )

    else:

        time_delta = None
        position_gain = None

    # --------------------------------------------------------
    # 17. SUMMARY
    # --------------------------------------------------------

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
    # 18. RETURN
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

    )


# NOTE: In causal mode rivals are assumed to make no future pit stops. This limitation is intentional and documented here.

# ACTUAL RACE REPLAY
# NOTE: In causal mode rivals are assumed to make no future pit stops. This limitation is intentional and documented here.


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
