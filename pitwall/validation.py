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
    """Test B: Identity test (the key one).
    
    For each finisher with a real mid-race stop, and for decision laps D in {10, 20, 26, 35}
    that precede their real stop, simulate the target with their REAL action (the real pit lap
    and real new compound), then compare to history:
    - error in target's total remaining time (simulated - actual), in seconds;
    - error in final position.
    
    Pass target: median abs time error <= 8 s and >= 80% within 1 position.
    """
    if decision_laps is None:
        decision_laps = [10, 20, 26, 35]

    finishers = get_finishers(session_df)
    results = []

    # Find real pit stops for each finisher
    # In our data, pit in-lap has is_pit_in_lap == True, and the next lap is is_pit_out_lap == True with new compound
    for d in finishers:
        d_laps = session_df[session_df["driver_number"] == d].sort_values("lap_number")
        
        # Identify all real pit in-laps
        pit_in_laps = d_laps[d_laps["is_pit_in_lap"]]
        
        for _, pit_row in pit_in_laps.iterrows():
            real_pit_lap = int(pit_row["lap_number"])
            # The compound after pit is on the next lap
            next_laps = d_laps[d_laps["lap_number"] == real_pit_lap + 1]
            if len(next_laps) == 0:
                continue
            real_new_compound = next_laps["compound"].iloc[0]

            for d_lap in decision_laps:
                if d_lap < real_pit_lap:
                    # Run simulation with real action: Pit(lap=real_pit_lap, compound=real_new_compound)
                    action = Pit(lap=real_pit_lap, compound=real_new_compound)
                    res = replay(
                        session_df=session_df,
                        target_driver=d,
                        decision_lap=d_lap,
                        action=action,
                        pace_model=pace_model,
                        pit_loss=pit_loss,
                    )
                    
                    # Remaining race error: total_time_delta_vs_actual
                    time_err = res.summary["total_time_delta_vs_actual"]
                    sim_pos = res.summary["final_position"]
                    actual_pos = int(d_laps[d_laps["lap_number"] == session_df["lap_number"].max()]["position"].iloc[0])
                    pos_err = sim_pos - actual_pos if sim_pos is not None else None

                    results.append({
                        "driver": d,
                        "decision_lap": d_lap,
                        "real_pit_lap": real_pit_lap,
                        "real_new_compound": real_new_compound,
                        "time_error_s": time_err,
                        "abs_time_error_s": abs(time_err) if time_err is not None else None,
                        "sim_final_pos": sim_pos,
                        "actual_final_pos": actual_pos,
                        "pos_error": pos_err,
                        "abs_pos_error": abs(pos_err) if pos_err is not None else None,
                    })

    res_df = pd.DataFrame(results)
    if len(res_df) == 0:
        return TestResult(
            name="Identity Test (Test B)",
            passed=False,
            details={"rows": []},
            message="No valid candidate scenarios found",
        )

    median_abs_time_err = float(res_df["abs_time_error_s"].median())
    p90_abs_time_err = float(res_df["abs_time_error_s"].quantile(0.90))
    pos_within_1_rate = float((res_df["abs_pos_error"] <= 1).mean())

    passed = (median_abs_time_err <= 8.0) and (pos_within_1_rate >= 0.80)

    return TestResult(
        name="Identity Test (Test B)",
        passed=passed,
        details={
            "n_scenarios": len(res_df),
            "median_abs_time_error_s": median_abs_time_err,
            "p90_abs_time_error_s": p90_abs_time_err,
            "pos_within_1_rate": pos_within_1_rate,
            "table": res_df.to_dict(orient="records"),
        },
        message=f"Median abs error: {median_abs_time_err:.2f}s (target <= 8s), Within 1 pos: {pos_within_1_rate*100:.1f}% (target >= 80%)",
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
