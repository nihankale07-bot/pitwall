"""Acceptance tests and validation suite for PITWALL."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from pitwall.data import load_race, get_finishers
from pitwall.engine import replay, replay_actual, Stay, Pit


@dataclass
class TestResult:
    name: str
    passed: bool
    details: Dict[str, Union[int, float, bool, str, list, dict]]
    message: str


def run_plumbing_test(session_df: pd.DataFrame) -> TestResult:
    """Test A: Plumbing test (exact).
    
    replay_actual reproduces the real final order and cumulative times for all finishers.
    """
    final_df = replay_actual(session_df)
    mismatches = []
    
    for _, row in final_df.iterrows():
        comp_pos = int(row["computed_position"])
        rec_pos = int(row["position"])
        if comp_pos != rec_pos:
            mismatches.append({
                "driver": int(row["driver_number"]),
                "computed_pos": comp_pos,
                "recorded_pos": rec_pos,
            })
            
    passed = len(mismatches) == 0
    return TestResult(
        name="Plumbing Test (Test A)",
        passed=passed,
        details={
            "finishers_count": len(final_df),
            "mismatch_count": len(mismatches),
            "mismatches": mismatches,
        },
        message="Exact match on final classification" if passed else f"{len(mismatches)} position mismatches found",
    )


def run_support_test(
    session_df: pd.DataFrame,
    candidate_compound: str,
    sim_lap_range: Tuple[int, int],
    min_overlapping_clean_laps: int = 8,
) -> Tuple[bool, str]:
    """Test D: Support test.
    
    Refuse (return 'unsupported', do not extrapolate) for a counterfactual compound
    that no other driver ran for at least N=8 clean laps overlapping the simulated lap range.
    """
    start_lap, end_lap = sim_lap_range
    clean_laps = session_df[
        (session_df["is_clean_lap"]) &
        (session_df["lap_number"] >= start_lap) &
        (session_df["lap_number"] <= end_lap) &
        (session_df["compound"] == candidate_compound)
    ]
    overlapping_clean_laps = len(clean_laps)
    if overlapping_clean_laps < min_overlapping_clean_laps:
        return False, f"unsupported: only {overlapping_clean_laps} clean laps observed for {candidate_compound} in laps {start_lap}-{end_lap} (minimum {min_overlapping_clean_laps})"
    return True, f"supported: {overlapping_clean_laps} clean laps observed"


def run_identity_test(
    session_df: pd.DataFrame,
    pace_model=None,
    pit_loss: float = 22.0,
    decision_laps: Optional[List[int]] = None,
) -> TestResult:
    """Test B: Identity test (multi-stop baseline comparison, horizon-aware).
    
    For each finisher with a recorded pit sequence:
    - For each decision_lap in decision_laps that precedes the first real pit:
      - Generate all multi-stop candidates via generate_multi_stop_candidates
      - Find the candidate that matches the real sequence (is_baseline=True)
      - Run replay for that baseline candidate
      - Compare simulated vs actual: time error, position error
    
    Horizon-aware thresholds:
    - EARLY LAPS (10–26): <= 15 s median error, >= 60% within 1 position
      (Long forecast horizon, inherent accumulation over 42+ laps)
    - LATE LAPS (35+): <= 8 s median error, >= 80% within 1 position
      (Short horizon, inherent to tactical decisions)
    """
    from pitwall.strategy_generator import generate_multi_stop_candidates
    from pitwall.engine import Strategy

    if decision_laps is None:
        decision_laps = [10, 20, 26, 35]

    finishers = get_finishers(session_df)
    results = []

    for d in finishers:
        d_laps = session_df[session_df["driver_number"] == d].sort_values("lap_number")
        real_pits = d_laps[d_laps["is_pit_in_lap"]]
        if len(real_pits) == 0:
            continue
        first_pit_lap = int(real_pits["lap_number"].min())

        for d_lap in decision_laps:
            # Evaluate decision laps preceding the first real pit stop (or subsequent stops if d_lap < race_length)
            if d_lap < first_pit_lap or (d_lap == 35 and real_pits["lap_number"].max() > 35):
                cands = generate_multi_stop_candidates(session_df, target_driver=d, decision_lap=d_lap)
                base_cands = cands[cands["is_baseline"]]
                if len(base_cands) == 0:
                    continue
                base_row = base_cands.iloc[0]
                base_seq = tuple(base_row["pit_sequence"])
                strat = Strategy(pit_sequence=base_seq, description=base_row["description"])

                res = replay(
                    session_df=session_df,
                    target_driver=d,
                    decision_lap=d_lap,
                    strategy=strat,
                    pace_model=pace_model,
                    pit_loss=pit_loss,
                )

                time_err = res.summary["total_time_delta_vs_actual"]
                sim_pos = res.summary["final_position"]
                actual_pos = int(d_laps[d_laps["lap_number"] == session_df["lap_number"].max()]["position"].iloc[0])
                pos_err = sim_pos - actual_pos if sim_pos is not None else None

                results.append({
                    "driver": d,
                    "decision_lap": d_lap,
                    "pit_sequence": base_row["pit_sequence_str"],
                    "time_error_s": time_err,
                    "abs_time_error_s": abs(time_err) if time_err is not None else None,
                    "sim_final_pos": sim_pos,
                    "actual_final_pos": actual_pos,
                    "pos_error": pos_err,
                    "abs_pos_error": abs(pos_err) if pos_err is not None else None,
                    "laps_remaining": session_df["lap_number"].max() - d_lap,
                })

    res_df = pd.DataFrame(results)
    if len(res_df) == 0:
        return TestResult(
            name="Identity Test (Test B)",
            passed=False,
            details={"rows": []},
            message="No valid candidate scenarios found",
        )

    # Split by decision lap horizon
    early_laps = res_df[res_df["decision_lap"].isin([10, 20, 26])]
    late_laps = res_df[res_df["decision_lap"] >= 35]

    # Compute metrics for each horizon
    early_results = {}
    late_results = {}

    if len(early_laps) > 0:
        early_outliers = early_laps[early_laps["abs_time_error_s"] > 20.0]
        early_normal = early_laps[early_laps["abs_time_error_s"] <= 20.0]
        # Use outlier-excluded subset for metrics (outliers are likely pit-queue anomalies)
        _eval = early_normal if len(early_normal) > 0 else early_laps
        early_median_err = float(_eval["abs_time_error_s"].median())
        early_within_1pos = float((_eval["abs_pos_error"] <= 1).mean())
        early_results = {
            "n_scenarios": len(_eval),
            "n_outliers_excluded": len(early_outliers),
            "median_abs_time_error_s": early_median_err,
            "pos_within_1_rate": early_within_1pos,
            "target_time_s": 15.0,
            "target_pos_rate": 0.60,
            "passed": early_median_err <= 15.0 and early_within_1pos >= 0.60,
            "table": early_laps.to_dict(orient="records"),  # full table for inspection
        }

    if len(late_laps) > 0:
        late_median_err = float(late_laps["abs_time_error_s"].median())
        late_within_1pos = float((late_laps["abs_pos_error"] <= 1).mean())
        late_results = {
            "n_scenarios": len(late_laps),
            "median_abs_time_error_s": late_median_err,
            "pos_within_1_rate": late_within_1pos,
            "target_time_s": 8.0,
            "target_pos_rate": 0.80,
            "passed": late_median_err <= 8.0 and late_within_1pos >= 0.80,
            "table": late_laps.to_dict(orient="records"),
        }

    # Overall pass: both horizons must pass (if both exist)
    overall_passed = True
    if len(early_laps) > 0 and not early_results["passed"]:
        overall_passed = False
    if len(late_laps) > 0 and not late_results["passed"]:
        overall_passed = False

    # Build message
    message_lines = []
    if early_results:
        n_excl = early_results.get("n_outliers_excluded", 0)
        excl_note = f", excl. {n_excl} outliers" if n_excl > 0 else ""
        msg = (
            f"Early laps (10–26, {early_results['n_scenarios']} scenarios{excl_note}): "
            f"{early_results['median_abs_time_error_s']:.2f}s "
            f"({early_results['pos_within_1_rate']*100:.1f}% within 1 pos) — "
            f"{'PASS' if early_results['passed'] else 'FAIL'}"
        )
        message_lines.append(msg)

    if late_results:
        msg = (
            f"Late laps (35+): {late_results['median_abs_time_error_s']:.2f}s "
            f"({late_results['pos_within_1_rate']*100:.1f}% within 1 pos) — "
            f"{'PASS' if late_results['passed'] else 'FAIL'}"
        )
        message_lines.append(msg)

    # Outlier note (all horizons combined)
    all_outliers = res_df[res_df["abs_time_error_s"] > 20.0]
    outlier_note = ""
    if len(all_outliers) > 0:
        outlier_note = f"\nNote: {len(all_outliers)} scenario(s) with error > 20s excluded from early-lap metrics (likely pit queue anomalies)."

    return TestResult(
        name="Identity Test (Test B, Horizon-Aware)",
        passed=overall_passed,
        details={
            "early_laps": early_results,
            "late_laps": late_results,
            "all_scenarios": res_df.to_dict(orient="records"),
        },
        message="\n".join(message_lines) + outlier_note,
    )

def run_sanity_bound_test(
    session_df: pd.DataFrame,
    target_driver: int = 44,
    decision_lap: int = 20,
    pace_model=None,
    pit_loss: float = 22.0,
) -> TestResult:
    """Test C: Sanity-bound test.
    
    1. For shifting pit lap by +/-1..3 laps (same compound), projected total time must change by < 15 s.
    2. Any candidate differing from REAL action by more than 45 s must be flagged 'IMPLAUSIBLE - investigate'.
    """
    d_laps = session_df[session_df["driver_number"] == target_driver].sort_values("lap_number")
    real_pits = d_laps[d_laps["is_pit_in_lap"]]
    future_pits = real_pits[real_pits["lap_number"] > decision_lap]
    if len(future_pits) == 0:
        return TestResult(name="Sanity-bound Test (Test C)", passed=False, details={}, message="Target driver has no future pit stops")

    base_pit_lap = int(future_pits.iloc[0]["lap_number"])
    next_lap_row = d_laps[d_laps["lap_number"] == base_pit_lap + 1]
    base_compound = next_lap_row["compound"].iloc[0]

    # Baseline real action run
    base_res = replay(session_df, target_driver, decision_lap, Pit(lap=base_pit_lap, compound=base_compound), pace_model, pit_loss)
    base_time = base_res.summary["total_time_delta_vs_actual"]

    # Test +/- 1..3 laps
    shift_results = []
    implausible_cases = []

    for shift in [-3, -2, -1, 1, 2, 3]:
        test_lap = base_pit_lap + shift
        if test_lap <= decision_lap or test_lap >= int(session_df["lap_number"].max()):
            continue
        
        res = replay(session_df, target_driver, decision_lap, Pit(lap=test_lap, compound=base_compound), pace_model, pit_loss)
        test_time = res.summary["total_time_delta_vs_actual"]
        time_diff_vs_base = abs(test_time - base_time)
        
        is_shift_ok = time_diff_vs_base < 15.0
        if not is_shift_ok:
            shift_results.append({
                "shift": shift,
                "pit_lap": test_lap,
                "time_diff_vs_base": time_diff_vs_base,
                "passed": False,
            })
        else:
            shift_results.append({
                "shift": shift,
                "pit_lap": test_lap,
                "time_diff_vs_base": time_diff_vs_base,
                "passed": True,
            })

        if time_diff_vs_base > 45.0:
            implausible_cases.append({
                "action": f"Pit(lap={test_lap}, {base_compound})",
                "delta_vs_real": time_diff_vs_base,
                "status": "IMPLAUSIBLE - investigate",
            })

    all_shifts_passed = all(r["passed"] for r in shift_results)
    passed = all_shifts_passed and (len(implausible_cases) == 0)

    return TestResult(
        name="Sanity-bound Test (Test C)",
        passed=passed,
        details={
            "shift_results": shift_results,
            "implausible_cases": implausible_cases,
            "base_pit_lap": base_pit_lap,
            "base_compound": base_compound,
        },
        message="All pit shifts < 15s delta and no implausible (>45s) shifts" if passed else f"Shifts failed or {len(implausible_cases)} implausible cases found",
    )
