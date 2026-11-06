#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
strategy_validation.py

Read-only validation of the selected counterfactual strategies for
Piastri (81) and Hamilton (44) at decision lap 26.

Extracts optimizer results and compares with actual recorded strategies.
Does NOT modify production code, retrain models, or generate new strategies.
"""

import sys
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("C:/Users/Nihan/.vscode/pitwall")
sys.path.insert(0, str(ROOT))

from pitwall.pace_model import PaceModel
from pitwall.optimizer import optimize_strategy, OptimizationResult
from pitwall.engine import ReplayResult, Strategy, Stay
from pitwall.data import load_race

# ──────────────────────────────────────────────────────────────
# 1. Load canonical production data
# ──────────────────────────────────────────────────────────────
print("=" * 70)
print("PITWALL | COUNTERFACTUAL STRATEGY VALIDATION")
print("=" * 70)

production_df = load_race(session_key=9558)
print(f"\nCanonical DataFrame: {len(production_df)} rows, "
      f"{len(production_df['driver_number'].unique())} drivers")

# ──────────────────────────────────────────────────────────────
# 2. Run optimizer for each driver
# ──────────────────────────────────────────────────────────────
DECISION_LAP = 26
RACE_LENGTH = 52

results = {}
for driver in [81, 44]:
    name = "Piastri" if driver == 81 else "Hamilton"
    print(f"\n{'─' * 50}")
    print(f"Running optimizer for {name} (driver {driver})...")

    result = optimize_strategy(
        session_df=production_df,
        target_driver=driver,
        decision_lap=DECISION_LAP,
        race_length=RACE_LENGTH,
        pace_model=PaceModel(),
        pit_loss=22.0,
        track_mode="causal",
        max_stops=2,
        max_candidates=None,
    )
    results[driver] = result
    print(f"  Best strategy ID: {result.best_strategy_id}")
    print(f"  Candidates evaluated: {len(result.ranking)}")

# ──────────────────────────────────────────────────────────────
# 3. Extract strategy details from each best replay
# ──────────────────────────────────────────────────────────────

def extract_strategy_details(result: OptimizationResult, driver: int, production_df: pd.DataFrame):
    """Extract comprehensive strategy details from an OptimizationResult."""
    best = result.best_replay
    laps_table = best.laps_table
    summary = best.summary
    action = best.action

    info = {
        "driver": driver,
        "driver_name": "Piastri" if driver == 81 else "Hamilton",
        "strategy_id": result.best_strategy_id,
        "decision_lap": DECISION_LAP,
    }

    # ── Pit sequence from the Strategy action ──
    if isinstance(action, Strategy):
        pit_sequence = list(action.pit_sequence)
        info["pit_laps"] = [lap for lap, _ in pit_sequence]
        info["pit_compounds"] = [(lap, compound) for lap, compound in pit_sequence]
        info["num_stops"] = len(pit_sequence)
    elif isinstance(action, Stay):
        info["pit_laps"] = []
        info["pit_compounds"] = []
        info["num_stops"] = 0
    else:
        info["pit_laps"] = []
        info["pit_compounds"] = []
        info["num_stops"] = 0

    # ── Stints: compound per stint ──
    target_laps = laps_table[
        laps_table["driver_number"] == driver
    ].sort_values("lap_number").copy()

    stints = []
    current_compound = None
    stint_start = None
    for _, row in target_laps.iterrows():
        lap = int(row["lap_number"])
        compound = row.get("compound")
        if compound != current_compound:
            if current_compound is not None:
                stints.append({
                    "compound": current_compound,
                    "lap_start": stint_start,
                    "lap_end": prev_lap,
                    "length": prev_lap - stint_start + 1,
                })
            current_compound = compound
            stint_start = lap
        prev_lap = lap
    if current_compound is not None:
        stints.append({
            "compound": current_compound,
            "lap_start": stint_start,
            "lap_end": prev_lap,
            "length": prev_lap - stint_start + 1,
        })
    info["stints"] = stints

    # ── Tyre age at each pit stop ──
    tyre_ages_at_pit = []
    for pit_lap, pit_compound in info["pit_compounds"]:
        # The pit-in lap is the lap OF the pit stop
        pit_in_row = target_laps[target_laps["lap_number"] == pit_lap]
        if not pit_in_row.empty:
            tyre_age_val = pit_in_row.iloc[0].get("tyre_age")
            tyre_ages_at_pit.append({
                "pit_lap": pit_lap,
                "new_compound": pit_compound,
                "tyre_age_at_stop": int(tyre_age_val) if pd.notna(tyre_age_val) else None,
            })
        else:
            tyre_ages_at_pit.append({
                "pit_lap": pit_lap,
                "new_compound": pit_compound,
                "tyre_age_at_stop": None,
            })
    info["tyre_ages_at_pit"] = tyre_ages_at_pit

    # ── Projected results ──
    info["projected_final_cumulative_time"] = summary.get("final_cumulative_time")
    info["projected_final_position"] = summary.get("final_position")
    info["time_delta_vs_actual"] = summary.get("total_time_delta_vs_actual")
    info["positions_gained_vs_actual"] = summary.get("positions_gained_vs_actual")

    # ── Constraint checks ──
    ALLOWED_COMPOUNDS = {"SOFT", "MEDIUM", "HARD"}
    compounds_used = set()
    for stint in stints:
        compounds_used.add(stint["compound"])

    info["all_compounds_valid"] = compounds_used.issubset(ALLOWED_COMPOUNDS)
    info["compounds_used"] = sorted(compounds_used)

    # At least 2 different compounds must be used (FIA regulation)
    info["two_compound_rule_satisfied"] = len(compounds_used) >= 2

    # Pit stops within valid range
    valid_pit_range = all(
        DECISION_LAP < lap < RACE_LENGTH for lap in info["pit_laps"]
    )
    info["pit_laps_in_valid_range"] = valid_pit_range

    return info


def extract_actual_strategy(production_df: pd.DataFrame, driver: int):
    """Extract the actual recorded pit strategy from production data."""
    driver_df = production_df[
        production_df["driver_number"] == driver
    ].sort_values("lap_number").copy()

    # Identify actual pit stops from is_pit_out_lap
    pit_out_laps = driver_df[driver_df["is_pit_out_lap"] == True]

    # Actual stints by compound changes
    stints = []
    current_compound = None
    stint_start = None
    prev_lap = None
    for _, row in driver_df.iterrows():
        lap = int(row["lap_number"])
        compound = row.get("compound")
        if compound != current_compound:
            if current_compound is not None:
                stints.append({
                    "compound": current_compound,
                    "lap_start": stint_start,
                    "lap_end": prev_lap,
                    "length": prev_lap - stint_start + 1,
                })
            current_compound = compound
            stint_start = lap
        prev_lap = lap
    if current_compound is not None:
        stints.append({
            "compound": current_compound,
            "lap_start": stint_start,
            "lap_end": prev_lap,
            "length": prev_lap - stint_start + 1,
        })

    # Pit in laps (the lap before a pit out lap)
    pit_in_laps = driver_df[driver_df["is_pit_in_lap"] == True]

    actual = {
        "driver": driver,
        "driver_name": "Piastri" if driver == 81 else "Hamilton",
        "num_stops": len(pit_out_laps),
        "pit_out_laps": pit_out_laps["lap_number"].tolist(),
        "pit_in_laps": pit_in_laps["lap_number"].tolist(),
        "stints": stints,
        "compounds_used": sorted(set(s["compound"] for s in stints)),
        "total_laps": len(driver_df),
        "actual_cumulative_time": float(driver_df["lap_duration"].sum()),
    }

    # Tyre age at each pit-in lap
    tyre_ages = []
    for _, row in pit_in_laps.iterrows():
        tyre_ages.append({
            "pit_in_lap": int(row["lap_number"]),
            "compound": row.get("compound"),
            "tyre_age": int(row["tyre_age"]) if pd.notna(row.get("tyre_age")) else None,
        })
    actual["tyre_ages_at_pit"] = tyre_ages

    return actual

# ──────────────────────────────────────────────────────────────
# 4. Extract and display
# ──────────────────────────────────────────────────────────────
report_lines = []
report_lines.append("=" * 70)
report_lines.append("PITWALL | COUNTERFACTUAL STRATEGY VALIDATION REPORT")
report_lines.append(f"Decision Lap: {DECISION_LAP}  |  Race Length: {RACE_LENGTH}")
report_lines.append("=" * 70)

for driver in [81, 44]:
    result = results[driver]
    details = extract_strategy_details(result, driver, production_df)
    actual = extract_actual_strategy(production_df, driver)
    name = details["driver_name"]

    report_lines.append("")
    report_lines.append("━" * 70)
    report_lines.append(f"  {name.upper()} (Driver {driver})")
    report_lines.append("━" * 70)

    # --- Selected strategy ---
    report_lines.append("")
    report_lines.append(f"  SELECTED COUNTERFACTUAL STRATEGY")
    report_lines.append(f"  ├── Strategy ID:            {details['strategy_id']}")
    report_lines.append(f"  ├── Total stops:            {details['num_stops']}")
    report_lines.append(f"  ├── Pit laps:               {details['pit_laps']}")

    report_lines.append(f"  ├── Stints:")
    for i, stint in enumerate(details["stints"], 1):
        report_lines.append(
            f"  │   Stint {i}: {stint['compound']:>6}  "
            f"(laps {stint['lap_start']}–{stint['lap_end']}, "
            f"{stint['length']} laps)"
        )

    report_lines.append(f"  ├── Tyre age at each pit stop:")
    for pit_info in details["tyre_ages_at_pit"]:
        report_lines.append(
            f"  │   Lap {pit_info['pit_lap']}: "
            f"age {pit_info['tyre_age_at_stop']} → {pit_info['new_compound']}"
        )

    report_lines.append(f"  ├── Projected final time:   "
                         f"{details['projected_final_cumulative_time']:.3f}s")
    report_lines.append(f"  ├── Projected final pos:    "
                         f"P{details['projected_final_position']}")
    if details['time_delta_vs_actual'] is not None:
        sign = "+" if details['time_delta_vs_actual'] > 0 else ""
        report_lines.append(f"  ├── Δ vs actual time:       "
                             f"{sign}{details['time_delta_vs_actual']:.3f}s")
    if details['positions_gained_vs_actual'] is not None:
        report_lines.append(f"  ├── Positions gained:       "
                             f"{details['positions_gained_vs_actual']}")

    # --- Constraint checks ---
    report_lines.append(f"  └── CONSTRAINT CHECKS:")
    report_lines.append(f"      ├── Compounds valid:       "
                         f"{'✓' if details['all_compounds_valid'] else '✗'}  "
                         f"{details['compounds_used']}")
    report_lines.append(f"      ├── Two-compound rule:     "
                         f"{'✓' if details['two_compound_rule_satisfied'] else '✗'}")
    report_lines.append(f"      └── Pit laps in range:     "
                         f"{'✓' if details['pit_laps_in_valid_range'] else '✗'}")

    # --- Actual strategy ---
    report_lines.append("")
    report_lines.append(f"  ACTUAL RECORDED STRATEGY")
    report_lines.append(f"  ├── Total stops:            {actual['num_stops']}")
    report_lines.append(f"  ├── Pit-in laps:            {actual['pit_in_laps']}")
    report_lines.append(f"  ├── Pit-out laps:           {actual['pit_out_laps']}")
    report_lines.append(f"  ├── Stints:")
    for i, stint in enumerate(actual["stints"], 1):
        report_lines.append(
            f"  │   Stint {i}: {stint['compound']:>6}  "
            f"(laps {stint['lap_start']}–{stint['lap_end']}, "
            f"{stint['length']} laps)"
        )
    report_lines.append(f"  ├── Tyre age at each pit-in:")
    for pit_info in actual["tyre_ages_at_pit"]:
        report_lines.append(
            f"  │   Lap {pit_info['pit_in_lap']}: "
            f"{pit_info['compound']} age {pit_info['tyre_age']}"
        )
    report_lines.append(f"  └── Actual cumulative time: {actual['actual_cumulative_time']:.3f}s")

# ──────────────────────────────────────────────────────────────
# 5. Cross-driver comparison
# ──────────────────────────────────────────────────────────────
p_details = extract_strategy_details(results[81], 81, production_df)
h_details = extract_strategy_details(results[44], 44, production_df)
p_actual = extract_actual_strategy(production_df, 81)
h_actual = extract_actual_strategy(production_df, 44)

report_lines.append("")
report_lines.append("━" * 70)
report_lines.append("  CROSS-DRIVER COMPARISON")
report_lines.append("━" * 70)

p_time = p_details["projected_final_cumulative_time"]
h_time = h_details["projected_final_cumulative_time"]
delta = p_time - h_time

report_lines.append(f"  Piastri projected:  {p_time:.3f}s  (P{p_details['projected_final_position']})")
report_lines.append(f"  Hamilton projected:  {h_time:.3f}s  (P{h_details['projected_final_position']})")
report_lines.append(f"  Piastri advantage:   {-delta:.3f}s" if delta < 0 else
                     f"  Hamilton advantage:  {delta:.3f}s")
report_lines.append(f"  Actual Piastri:     {p_actual['actual_cumulative_time']:.3f}s")
report_lines.append(f"  Actual Hamilton:    {h_actual['actual_cumulative_time']:.3f}s")
report_lines.append(f"  Actual Δ (PIA-HAM): {p_actual['actual_cumulative_time'] - h_actual['actual_cumulative_time']:.3f}s")

# ──────────────────────────────────────────────────────────────
# 6. Top-5 ranking table
# ──────────────────────────────────────────────────────────────
for driver in [81, 44]:
    name = "Piastri" if driver == 81 else "Hamilton"
    ranking = results[driver].ranking
    report_lines.append("")
    report_lines.append(f"  TOP-5 RANKED STRATEGIES – {name.upper()}")
    report_lines.append(f"  {'Rank':<5} {'ID':<12} {'Stops':<6} {'Pos':<5} {'Time (s)':<12} {'Pit Sequence'}")
    report_lines.append(f"  {'─'*5} {'─'*12} {'─'*6} {'─'*5} {'─'*12} {'─'*30}")
    for i, row in ranking.head(5).iterrows():
        pit_str = str(row.get("pit_sequence_str", row.get("pit_sequence", "")))
        report_lines.append(
            f"  {i+1:<5} {str(row['strategy_id']):<12} "
            f"{row['num_stops']:<6} "
            f"P{row['projected_final_position']:<4} "
            f"{row['projected_cumulative_time_s']:<12.3f} "
            f"{pit_str}"
        )

report_lines.append("")
report_lines.append("=" * 70)
report_lines.append("END OF VALIDATION REPORT")
report_lines.append("=" * 70)

# Print and save
report_text = "\n".join(report_lines)
print(report_text)

out_path = ROOT / "scratch" / "strategy_validation_report.txt"
with open(out_path, "w", encoding="utf-8") as f:
    f.write(report_text)
print(f"\nReport saved to: {out_path}")

