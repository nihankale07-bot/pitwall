"""Strategy search and ranking for PITWALL.

Important: replay() currently holds rival future lap times fixed at their observed
values. Results are therefore counterfactual rankings for a historical replay,
not a validated live-race win-probability forecast.

Leakage prevention
------------------
When a PaceModel is supplied, `optimize_strategy` fits it exclusively on clean
laps up to and including `decision_lap` (observations after that lap are not
visible at decision time).  Future target-driver predictions use `track_mode=
"causal"` so the lap-specific fixed effect is frozen at the decision-lap value.
Rival drivers always use their actual recorded trajectories regardless of mode.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from pitwall.engine import ReplayResult, Strategy, Stay, replay
from pitwall.strategy_generator import generate_multi_stop_candidates


def _fit_on_history(
    pace_model: Any,
    session_df: pd.DataFrame,
    decision_lap: int,
) -> Any:
    """Return a *new* fitted PaceModel using only observations ≤ decision_lap.

    The input ``pace_model`` object is used as a template (its hyper-parameters
    are preserved) but it is **never mutated**.  A fresh instance with the same
    ``reference_compound`` is fitted on the restricted clean-lap subset.
    """
    from pitwall.pace_model import PaceModel

    # Only clean laps that were observable at the decision point
    if "is_clean_lap" not in session_df.columns:
        raise ValueError(
            "session_df must contain 'is_clean_lap' (produced by load_race()). "
            "Cannot fit pace model without it."
        )
    history = session_df.loc[
        (session_df["lap_number"] <= decision_lap)
        & session_df["is_clean_lap"].fillna(False)
    ].copy()

    if history.empty:
        raise ValueError(
            f"No clean laps available up to decision_lap={decision_lap}."
        )

    ref = getattr(pace_model, "reference_compound", "MEDIUM")
    return PaceModel(reference_compound=ref).fit(history)


@dataclass
class OptimizationResult:
    """Ranked candidate strategies and the best available replay."""
    target_driver: int
    decision_lap: int
    ranking: pd.DataFrame
    best_strategy_id: str
    best_replay: ReplayResult
    replay_results: Dict[str, ReplayResult]
    objective: str = "projected_final_position_then_cumulative_time"
    interpretation: str = (
        "Historical counterfactual ranking. Rival future pace is replayed from observed data; "
        "this is not yet a live-race forecast."
    )


def optimize_strategy(
    session_df: pd.DataFrame,
    target_driver: int,
    decision_lap: int,
    race_length: int,
    pace_model: Any = None,
    pit_loss: float = 22.0,
    track_mode: str = "causal",
    max_stops: int = 2,
    max_candidates: Optional[int] = 95,
    supported_compounds: Optional[set] = None,
) -> OptimizationResult:
    """Generate, replay, and rank feasible candidate pit strategies.

    Ranking prioritizes projected final position, then projected cumulative
    time, then fewer stops. This is a transparent baseline objective; it does
    not claim to maximize win probability under uncertainty.

    Leakage prevention
    ------------------
    If a ``pace_model`` is supplied it is **re-fitted** here on clean laps with
    ``lap_number <= decision_lap`` before any replay is executed.  Future
    target-driver predictions use ``track_mode`` (default ``"causal"``) so the
    decision-lap effect is frozen and no post-decision observations influence
    the model.
    """
    if session_df is None or session_df.empty:
        raise ValueError("session_df must contain race-lap data.")
    required = {"driver_number", "lap_number", "lap_duration", "compound", "tyre_age"}
    missing = required - set(session_df.columns)
    if missing:
        raise ValueError(f"session_df is missing required columns: {sorted(missing)}")

    if not isinstance(race_length, int) or race_length <= 1:
      raise ValueError("race_length must be supplied as a valid integer.")

    if not 1 <= int(decision_lap) < race_length:
      raise ValueError("decision_lap must be between 1 and race_length - 1.")
    if target_driver not in set(session_df["driver_number"].unique()):
        raise ValueError(f"target_driver {target_driver} is not present in session_df.")

    # ------------------------------------------------------------------
    # Leakage prevention: re-fit the pace model on clean historical laps
    # only (lap_number <= decision_lap).  The full session_df is still
    # forwarded to replay() so rivals keep their actual future trajectories.
    # ------------------------------------------------------------------
    if pace_model is not None:
        pace_model = _fit_on_history(pace_model, session_df, decision_lap)

    candidates = generate_multi_stop_candidates(
        race_df=session_df,
        target_driver=target_driver,
        decision_lap=decision_lap,
        race_length=race_length,
        max_stops=max_stops,
        supported_compounds=supported_compounds,
    )
    if candidates.empty:
        raise RuntimeError("No candidate strategies were generated.")

    if max_candidates is not None and len(candidates) > max_candidates:
        # Keep the no-stop option and historical baseline where possible, then
        # take a deterministic sample of remaining candidates.
        keep = candidates[candidates["pit_sequence"].map(len) == 0]
        keep = keep.drop_duplicates(subset=["pit_sequence"])
        rest = candidates[~candidates["pit_sequence"].isin(keep["pit_sequence"])]
        room = max(0, max_candidates - len(keep))
        if room and len(rest) > room:
            take_idx = np.linspace(0, len(rest) - 1, room, dtype=int)
            rest = rest.iloc[take_idx]
        candidates = pd.concat([keep, rest], ignore_index=True).head(max_candidates).reset_index(drop=True)

    replay_results: Dict[str, ReplayResult] = {}
    rows = []
    for _, candidate in candidates.iterrows():
        strategy_id = str(candidate["strategy_id"])
        sequence = tuple((int(lap), str(compound)) for lap, compound in candidate["pit_sequence"])
        strategy = Strategy(
            pit_sequence=sequence,
            description=str(candidate.get("description", candidate.get("pit_sequence_str", ""))),
        ) if sequence else Stay()

        result = replay(
            session_df=session_df,
            target_driver=target_driver,
            decision_lap=decision_lap,
            strategy=strategy,
            pace_model=pace_model,
            pit_loss=pit_loss,
            track_mode=track_mode,
            race_length=race_length,
        )
        replay_results[strategy_id] = result
        summary = result.summary
        rows.append({
            "strategy_id": strategy_id,
            "pit_sequence": sequence,
            "pit_sequence_str": candidate.get("pit_sequence_str", "Stay out"),
            "is_baseline": len(sequence) == 0,
            "num_stops": len(sequence),
            "projected_final_position": summary.get("final_position"),
            "projected_cumulative_time_s": summary.get("final_cumulative_time"),
            "time_delta_vs_actual_s": summary.get("total_time_delta_vs_actual"),
            "positions_gained_vs_actual": summary.get("positions_gained_vs_actual"),
            "ground_truth_available": bool(summary.get("ground_truth_available", False)),
            "description": candidate.get("description", ""),
        })

    ranking = pd.DataFrame(rows)
    # A missing projected position/time should never silently win the ranking.
    ranking["_position_sort"] = pd.to_numeric(
        ranking["projected_final_position"], errors="coerce"
    ).fillna(np.inf)
    ranking["_time_sort"] = pd.to_numeric(
        ranking["projected_cumulative_time_s"], errors="coerce"
    ).fillna(np.inf)
    ranking = ranking.sort_values(
        ["_position_sort", "_time_sort", "num_stops", "strategy_id"],
        ascending=[True, True, True, True],
        kind="stable",
    ).drop(columns=["_position_sort", "_time_sort"]).reset_index(drop=True)

    if ranking.empty or not np.isfinite(
        pd.to_numeric(ranking["projected_final_position"], errors="coerce").min()
    ):
        raise RuntimeError(
            "No candidate produced a projected final position. Check the replay inputs and pace model."
        )

    best_strategy_id = str(ranking.iloc[0]["strategy_id"])
    return OptimizationResult(
        target_driver=int(target_driver),
        decision_lap=int(decision_lap),
        ranking=ranking,
        best_strategy_id=best_strategy_id,
        best_replay=replay_results[best_strategy_id],
        replay_results=replay_results,
    )
