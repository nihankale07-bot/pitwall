
from typing import Optional, Set

import pandas as pd

from pitwall.data import load_race
from pitwall.pace_model import PaceModel
from pitwall.optimizer import optimize_strategy


# ============================================================
# PITWALL PRODUCTION CONFIGURATION
# ============================================================

DEFAULT_PIT_LOSS = 22.0
DEFAULT_MAX_STOPS = 2
DEFAULT_MAX_CANDIDATES = 95

CALIBRATED_DEGRADATION = {
    "SOFT": 0.05,
    "MEDIUM": 0.18,
    "HARD": 0.00,
    "INTERMEDIATE": 0.25,  # Provisional degradation – derived from session 9558 analysis (≈0.25 s/lap).
}

REFERENCE_AGE = 25

SUPPORTED_COMPOUNDS = {"SOFT", "MEDIUM", "HARD"}


# ============================================================
# PACE MODEL INITIALIZATION
# ============================================================

def build_pace_model(
    session_df: pd.DataFrame,
    decision_lap: int,
    track_mode: str,
) -> PaceModel:
    """
    Build the pace model using information available at the
    strategy decision time when operating in causal mode.
    """

    if track_mode == "causal":
        training_df = session_df[
            session_df["lap_number"] <= decision_lap
        ].copy()

    elif track_mode == "replay":
        training_df = session_df.copy()

    else:
        raise ValueError(
            "track_mode must be 'causal' or 'replay'."
        )

    if training_df.empty:
        raise ValueError("No training data available.")

    pace_model = PaceModel(
        reference_compound="MEDIUM"
    ).fit(training_df)

    # Preserve predictions at the reference tyre age
    for compound, new_slope in CALIBRATED_DEGRADATION.items():

        old_slope = pace_model.compound_age_slopes.get(
            compound, 0.0
        )

        old_effect = pace_model.compound_effects.get(
            compound, 0.0
        )

        pace_model.compound_effects[compound] = (
            old_effect
            + (old_slope - new_slope) * REFERENCE_AGE
        )

    pace_model.compound_age_slopes = (
        CALIBRATED_DEGRADATION.copy()
    )

    return pace_model


# ============================================================
# MAIN SIMULATOR SERVICE
# ============================================================

def run_strategy_optimization(
    session_key: int,
    target_driver: int,
    decision_lap: int,
    race_length: Optional[int] = None,
    track_mode: str = "causal",
    pit_loss: float = DEFAULT_PIT_LOSS,
    max_stops: int = DEFAULT_MAX_STOPS,
    max_candidates: int = DEFAULT_MAX_CANDIDATES,
    data_dir: Optional[str] = None,
    supported_compounds: Optional[Set[str]] = None,
) -> dict:
    """
    Run PITWALL strategy optimization without notebook execution.

    Returns a dictionary containing:
    - Selected driver and race information
    - Recommended strategy
    - Strategy ranking
    - Best replay summary
    - Projected lap-by-lap results
    """

    # --------------------------------------------------------
    # 1. LOAD SESSION & RESOLVE RACE LENGTH
    # --------------------------------------------------------

    if track_mode not in {"causal", "replay"}:
        raise ValueError(
            "track_mode must be 'causal' or 'replay'."
        )

    if pit_loss < 0:
        raise ValueError("pit_loss cannot be negative.")

    session_df = load_race(
        session_key=session_key,
        data_dir=data_dir,
    )

    if race_length is None:
        race_length = int(session_df["lap_number"].max())

    if race_length <= 1:
        raise ValueError("race_length must be greater than 1.")

    if not 1 <= decision_lap < race_length:
        raise ValueError(
            "decision_lap must be between 1 and race_length - 1."
        )

    if target_driver not in session_df["driver_number"].unique():
        raise ValueError(
            f"Driver {target_driver} does not exist in session "
            f"{session_key}."
        )

    driver_history = session_df[
        (session_df["driver_number"] == target_driver)
        & (session_df["lap_number"] <= decision_lap)
    ]

    if driver_history.empty:
        raise ValueError(
            "No driver history available at the selected decision lap."
        )

    if decision_lap not in driver_history["lap_number"].values:
        raise ValueError(
            f"Driver {target_driver} has no recorded lap "
            f"at decision lap {decision_lap}."
        )

    # --------------------------------------------------------
    # 3. BUILD PACE MODEL
    # --------------------------------------------------------

    pace_model = build_pace_model(
        session_df=session_df,
        decision_lap=decision_lap,
        track_mode=track_mode,
    )

    # --------------------------------------------------------
    # 4. RUN OPTIMIZER
    # --------------------------------------------------------

    result = optimize_strategy(
        session_df=session_df,
        target_driver=target_driver,
        decision_lap=decision_lap,
        race_length=race_length,
        pace_model=pace_model,
        pit_loss=pit_loss,
        track_mode=track_mode,
        max_stops=max_stops,
        max_candidates=max_candidates,
        supported_compounds=(
            supported_compounds or SUPPORTED_COMPOUNDS
        ),
    )

    # --------------------------------------------------------
    # 5. EXTRACT RESULTS
    # --------------------------------------------------------

    ranking = (
        result.ranking
        .astype(object)
        .where(pd.notna(result.ranking), None)
        .to_dict(orient="records")
    )

    best_replay = result.best_replay

    laps_table = (
        best_replay.laps_table
        .astype(object)
        .where(pd.notna(best_replay.laps_table), None)
        .to_dict(orient="records")
    )

    # --------------------------------------------------------
    # 6. PROJECTED FULL-GRID CLASSIFICATION
    # --------------------------------------------------------
    if best_replay.classification is not None and not best_replay.classification.empty:
        class_df = best_replay.classification
    else:
        class_df = best_replay.laps_table[
            best_replay.laps_table["lap_number"] == race_length
        ].sort_values("position")

    projected_classification = (
        class_df.astype(object)
        .where(pd.notna(class_df), None)
        .to_dict(orient="records")
    )

    return {
        "session_key": session_key,
        "target_driver": target_driver,
        "decision_lap": decision_lap,
        "race_length": race_length,
        "track_mode": track_mode,

        "model": {
            "type": "PITWALL PaceModel",
            "reference_age": REFERENCE_AGE,
            "degradation": CALIBRATED_DEGRADATION,
            "r_squared": pace_model.rsquared,
        },

        "recommendation": {
            "strategy_id": result.best_strategy_id,
            "strategy": ranking[0],
            "interpretation": result.interpretation,
            "objective": result.objective,
        },

        "ranking": ranking,

        "best_replay": {
            "summary": best_replay.summary,
            "laps_table": laps_table,
        },

        "projected_classification": projected_classification,
    }
