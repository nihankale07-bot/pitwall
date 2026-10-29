"""Replay engine for counterfactual strategy simulation."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Union
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Stay:
    """Action representing staying out without pitting."""
    pass


@dataclass(frozen=True)
class Pit:
    """Action representing pitting on a specific lap for a new compound."""
    lap: int
    compound: str


# Type alias for actions
Action = Union[Stay, Pit]


@dataclass
class ReplayResult:
    """Container for the output of a counterfactual race replay."""
    session_key: int
    target_driver: int
    decision_lap: int
    action: Action
    ground_truth_available: bool
    laps_table: pd.DataFrame
    summary: Dict[str, Union[int, float, bool, str, None]]


def replay(
    session_df: pd.DataFrame,
    target_driver: int,
    decision_lap: int,
    action: Action,
    pace_model=None,
    pit_loss: float = 22.0,
    track_mode: str = "replay",
) -> ReplayResult:
    """Replay race with a counterfactual strategy for target_driver.
    
    Laps <= decision_lap: actual data for everyone.
    Laps > decision_lap: rivals replay actual lap times. Target is simulated.
    """
    df = session_df
    max_race_laps = int(df["lap_number"].max())
    
    # Target driver's max recorded lap
    target_df = df[df["driver_number"] == target_driver].sort_values("lap_number")
    target_recorded_laps = int(target_df["lap_number"].max())
    ground_truth_available = (target_recorded_laps >= max_race_laps)
    sim_end_lap = max_race_laps

    curr_row = target_df[target_df["lap_number"] == decision_lap].iloc[0]
    curr_compound = curr_row["compound"]
    curr_tyre_age = int(curr_row["tyre_age"])

    drivers = sorted(df["driver_number"].unique())

    # Pre-index driver lap durations and metadata into dicts
    # (driver, lap) -> duration, compound, tyre_age
    actual_records = df.set_index(["driver_number", "lap_number"])[["lap_duration", "compound", "tyre_age", "position"]].to_dict(orient="index")

    # Target simulated laps
    target_sim_durations: Dict[int, float] = {}
    target_sim_compounds: Dict[int, str] = {}
    target_sim_tyre_ages: Dict[int, int] = {}
    target_is_pit_lap: Dict[int, bool] = {}

    # Copy actual laps up to decision lap
    for l_num in range(1, decision_lap + 1):
        rec = actual_records.get((target_driver, l_num))
        if rec:
            target_sim_durations[l_num] = rec["lap_duration"]
            target_sim_compounds[l_num] = rec["compound"]
            target_sim_tyre_ages[l_num] = int(rec["tyre_age"]) if pd.notna(rec["tyre_age"]) else 0
            target_is_pit_lap[l_num] = False

    # Placeholder baseline calculation
    clean_history = target_df[
        (target_df["lap_number"] <= decision_lap) & 
        (target_df.get("is_clean_lap", pd.Series(True, index=target_df.index)))
    ]
    if len(clean_history) >= 3:
        placeholder_pace = float(clean_history.tail(3)["lap_duration"].median())
    elif len(clean_history) > 0:
        placeholder_pace = float(clean_history["lap_duration"].median())
    else:
        placeholder_pace = float(target_df[target_df["lap_number"] <= decision_lap]["lap_duration"].dropna().median())

    # Determine pit lap and new compound if action is Pit
    pit_lap = action.lap if isinstance(action, Pit) else -1
    new_compound = action.compound if isinstance(action, Pit) else None

    # Simulate laps from decision_lap + 1 to sim_end_lap
    sim_compound = curr_compound
    sim_tyre_age = curr_tyre_age

    for l_num in range(decision_lap + 1, sim_end_lap + 1):
        is_pit_now = (l_num == pit_lap)
        target_is_pit_lap[l_num] = is_pit_now

        if is_pit_now:
            base_tyre_age = sim_tyre_age + 1
            if pace_model is not None:
                lap_time = pace_model.predict_lap(
                    lap_number=l_num,
                    driver_number=target_driver,
                    compound=sim_compound,
                    tyre_age=base_tyre_age,
                    mode=track_mode,
                    decision_lap=decision_lap,
                )
            else:
                lap_time = placeholder_pace
            lap_time += pit_loss
            
            target_sim_durations[l_num] = lap_time
            target_sim_compounds[l_num] = sim_compound
            target_sim_tyre_ages[l_num] = base_tyre_age

            # Switch compound for the next lap, starting at tyre_age 0
            sim_compound = new_compound
            sim_tyre_age = 0
        else:
            sim_tyre_age += 1
            if pace_model is not None:
                lap_time = pace_model.predict_lap(
                    lap_number=l_num,
                    driver_number=target_driver,
                    compound=sim_compound,
                    tyre_age=sim_tyre_age,
                    mode=track_mode,
                    decision_lap=decision_lap,
                )
            else:
                lap_time = placeholder_pace

            target_sim_durations[l_num] = lap_time
            target_sim_compounds[l_num] = sim_compound
            target_sim_tyre_ages[l_num] = sim_tyre_age

    # Compute running cumulative times and positions for every lap
    all_lap_rows = []
    driver_cum_times = {d: 0.0 for d in drivers}

    for l_num in range(1, sim_end_lap + 1):
        active_drivers = []
        for d in drivers:
            if d == target_driver:
                dur = target_sim_durations.get(l_num, np.nan)
            else:
                rec = actual_records.get((d, l_num))
                dur = rec["lap_duration"] if rec else np.nan
            
            if pd.notna(dur):
                driver_cum_times[d] += dur
                active_drivers.append(d)

        # Rank active drivers by cumulative time ascending
        sorted_active = sorted(active_drivers, key=lambda d: driver_cum_times[d])
        leader_time = driver_cum_times[sorted_active[0]]

        for pos_idx, d in enumerate(sorted_active, start=1):
            cum_t = driver_cum_times[d]
            gap_leader = cum_t - leader_time
            gap_ahead = (cum_t - driver_cum_times[sorted_active[pos_idx - 2]]) if pos_idx > 1 else 0.0
            gap_behind = (driver_cum_times[sorted_active[pos_idx]] - cum_t) if pos_idx < len(sorted_active) else 0.0

            if d == target_driver:
                comp = target_sim_compounds.get(l_num, None)
                t_age = target_sim_tyre_ages.get(l_num, None)
                dur = target_sim_durations.get(l_num, np.nan)
                gt_avail = (l_num <= target_recorded_laps)
            else:
                rec = actual_records.get((d, l_num))
                comp = rec["compound"] if rec else None
                t_age = int(rec["tyre_age"]) if rec and pd.notna(rec["tyre_age"]) else None
                dur = rec["lap_duration"] if rec else np.nan
                gt_avail = True

            all_lap_rows.append({
                "lap_number": l_num,
                "driver_number": d,
                "lap_duration": dur,
                "cum_time": cum_t,
                "position": pos_idx,
                "gap_to_leader": gap_leader,
                "gap_ahead": gap_ahead,
                "gap_behind": gap_behind,
                "compound": comp,
                "tyre_age": t_age,
                "is_target": (d == target_driver),
                "ground_truth_available": gt_avail,
            })

    result_df = pd.DataFrame(all_lap_rows)

    # Compute summary
    target_final = result_df[(result_df["driver_number"] == target_driver) & (result_df["lap_number"] == sim_end_lap)]
    if ground_truth_available and len(target_final) > 0:
        final_sim_pos = int(target_final["position"].iloc[0])
        final_sim_time = float(target_final["cum_time"].iloc[0])
        
        actual_target_end = target_df[target_df["lap_number"] == sim_end_lap].iloc[0]
        actual_pos = int(actual_target_end["position"])
        actual_time = float(target_df["lap_duration"].sum())
        
        delta_time = final_sim_time - actual_time
        pos_gain = actual_pos - final_sim_pos
    else:
        final_sim_pos = None
        final_sim_time = None
        delta_time = None
        pos_gain = None

    summary = {
        "target_driver": target_driver,
        "decision_lap": decision_lap,
        "ground_truth_available": ground_truth_available,
        "final_position": final_sim_pos,
        "total_time_delta_vs_actual": delta_time,
        "positions_gained_vs_actual": pos_gain,
    }

    return ReplayResult(
        session_key=int(df["session_key"].iloc[0]) if "session_key" in df.columns else 9558,
        target_driver=target_driver,
        decision_lap=decision_lap,
        action=action,
        ground_truth_available=ground_truth_available,
        laps_table=result_df,
        summary=summary,
    )


def replay_actual(session_df: pd.DataFrame) -> pd.DataFrame:
    """Passthrough replay using actual recorded laps for all drivers.
    
    Returns table of final lap results per driver: position, cum_time.
    """
    df = session_df.copy()
    max_laps = int(df["lap_number"].max())
    
    df = df.sort_values(["driver_number", "lap_number"])
    df["cum_time"] = df.groupby("driver_number")["lap_duration"].cumsum()
    
    final_df = df[df["lap_number"] == max_laps].copy()
    final_df["computed_position"] = final_df["cum_time"].rank(method="min").astype(int)
    
    return final_df.sort_values("computed_position").reset_index(drop=True)
