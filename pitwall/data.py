"""Data ingestion and normalization helpers for race sessions."""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd


def load_race(
    session_key: int = 9558,
    data_dir: Optional[Path] = None,
) -> pd.DataFrame:
    """Load and return a validated tidy dataframe for the race session.
    
    Includes:
    - driver_number, lap_number, position, lap_duration, compound, tyre_age, stint_number,
      is_pit_out_lap, is_pit_in_lap, is_sc_vsc_lap, is_clean_lap, is_finisher
    """
    if data_dir is None:
        # Defaults to repository data/processed/<session_key>
        base_path = Path(__file__).resolve().parent.parent / "data" / "processed" / str(session_key)
    else:
        base_path = Path(data_dir) / str(session_key)

    race_state_file = base_path / "race_state.parquet"
    if not race_state_file.exists():
        raise FileNotFoundError(f"race_state.parquet not found at {race_state_file}")

    df = pd.read_parquet(race_state_file)

    # If traffic_features exist, merge traffic_ahead and traffic_behind
    traffic_file = base_path / "traffic_features.parquet"
    if traffic_file.exists():
        tf = pd.read_parquet(traffic_file)
        if "traffic_ahead" in tf.columns and "traffic_ahead" not in df.columns:
            df = df.merge(
                tf[["driver_number", "lap_number", "traffic_ahead", "traffic_behind"]],
                on=["driver_number", "lap_number"],
                how="left",
            )

    # Deduplicate in case of duplicate lap records
    df = df.drop_duplicates(subset=["driver_number", "lap_number"], keep="first")

    # Ensure sorting
    df = df.sort_values(["driver_number", "lap_number"]).reset_index(drop=True)

    # Identify pit out laps and pit in laps
    # An in-lap is the lap before an out-lap for the same driver
    df["is_pit_out_lap"] = df["is_pit_out_lap"].fillna(False).astype(bool)
    
    # In-lap is where the NEXT lap for this driver has is_pit_out_lap == True
    df["next_is_pit_out"] = df.groupby("driver_number")["is_pit_out_lap"].shift(-1).fillna(False)
    df["is_pit_in_lap"] = df["next_is_pit_out"].astype(bool)
    df = df.drop(columns=["next_is_pit_out"])

    # Finishers vs non-finishers
    max_race_laps = int(df["lap_number"].max())
    driver_max_laps = df.groupby("driver_number")["lap_number"].max()
    finishers = set(driver_max_laps[driver_max_laps == max_race_laps].index)
    df["is_finisher"] = df["driver_number"].isin(finishers)

    # Cumulative time and gap calculations
    # Cumulative time per driver: cumulative sum of lap_duration
    df["cum_time"] = df.groupby("driver_number")["lap_duration"].cumsum()

    # Safety car / VSC detection
    # First check race_control.parquet if available
    rc_file = base_path / "race_control.parquet"
    sc_laps = set()
    if rc_file.exists():
        try:
            rc = pd.read_parquet(rc_file)
            if "category" in rc.columns:
                sc_events = rc[
                    rc["category"].astype(str).str.contains("SAFETY|VSC", case=False, na=False) |
                    rc["message"].astype(str).str.contains("SAFETY CAR|VIRTUAL SAFETY CAR|RED FLAG", case=False, na=False)
                ]
                for lap in sc_events["lap_number"].dropna().unique():
                    sc_laps.add(int(lap))
        except Exception:
            pass

    # In addition or fallback: field median lap time >= 1.25x rolling field median
    lap_medians = df.groupby("lap_number")["lap_duration"].median()
    rolling_field_medians = lap_medians.rolling(5, min_periods=1, center=True).median()
    pace_sc_laps = set(lap_medians[lap_medians >= 1.25 * rolling_field_medians].index)
    sc_laps.update(pace_sc_laps)

    df["is_sc_vsc_lap"] = df["lap_number"].isin(sc_laps)

    # Outlier detection (> 1.3x field median for that lap)
    df["field_median_lap"] = df.groupby("lap_number")["lap_duration"].transform("median")
    df["is_gross_outlier"] = df["lap_duration"] > 1.3 * df["field_median_lap"]

    # Clean lap flag for pace model
    df["is_clean_lap"] = (
        (df["lap_number"] > 1)
        & (~df["is_pit_out_lap"])
        & (~df["is_pit_in_lap"])
        & (~df["is_sc_vsc_lap"])
        & (~df["is_gross_outlier"])
        & (df["lap_duration"].notna())
    )

    return df


def get_driver_laps(df: pd.DataFrame, driver_number: int) -> pd.DataFrame:
    """Return lap table for a specific driver."""
    return df[df["driver_number"] == driver_number].sort_values("lap_number").reset_index(drop=True)


def get_finishers(df: pd.DataFrame) -> List[int]:
    """Return list of finisher driver numbers."""
    max_race_laps = int(df["lap_number"].max())
    driver_max_laps = df.groupby("driver_number")["lap_number"].max()
    return sorted(list(driver_max_laps[driver_max_laps == max_race_laps].index))


DRIVER_METADATA: Dict[int, Dict[str, Union[int, str]]] = {
    1: {"driver_number": 1, "code": "VER", "name": "Max Verstappen", "team": "Red Bull Racing"},
    2: {"driver_number": 2, "code": "SAR", "name": "Logan Sargeant", "team": "Williams"},
    3: {"driver_number": 3, "code": "RIC", "name": "Daniel Ricciardo", "team": "RB"},
    4: {"driver_number": 4, "code": "NOR", "name": "Lando Norris", "team": "McLaren"},
    10: {"driver_number": 10, "code": "GAS", "name": "Pierre Gasly", "team": "Alpine"},
    11: {"driver_number": 11, "code": "PER", "name": "Sergio Perez", "team": "Red Bull Racing"},
    14: {"driver_number": 14, "code": "ALO", "name": "Fernando Alonso", "team": "Aston Martin"},
    16: {"driver_number": 16, "code": "LEC", "name": "Charles Leclerc", "team": "Ferrari"},
    18: {"driver_number": 18, "code": "STR", "name": "Lance Stroll", "team": "Aston Martin"},
    20: {"driver_number": 20, "code": "MAG", "name": "Kevin Magnussen", "team": "Haas"},
    22: {"driver_number": 22, "code": "TSU", "name": "Yuki Tsunoda", "team": "RB"},
    23: {"driver_number": 23, "code": "ALB", "name": "Alexander Albon", "team": "Williams"},
    24: {"driver_number": 24, "code": "ZHO", "name": "Zhou Guanyu", "team": "Kick Sauber"},
    27: {"driver_number": 27, "code": "HUL", "name": "Nico Hulkenberg", "team": "Haas"},
    31: {"driver_number": 31, "code": "OCO", "name": "Esteban Ocon", "team": "Alpine"},
    44: {"driver_number": 44, "code": "HAM", "name": "Lewis Hamilton", "team": "Mercedes-AMG"},
    55: {"driver_number": 55, "code": "SAI", "name": "Carlos Sainz", "team": "Ferrari"},
    63: {"driver_number": 63, "code": "RUS", "name": "George Russell", "team": "Mercedes-AMG"},
    77: {"driver_number": 77, "code": "BOT", "name": "Valtteri Bottas", "team": "Kick Sauber"},
    81: {"driver_number": 81, "code": "PIA", "name": "Oscar Piastri", "team": "McLaren"},
}


def resolve_driver_number(df: pd.DataFrame, identifier: Union[int, str]) -> int:
    """Resolve a driver number from driver number, code, or name using session data."""
    if isinstance(identifier, int) or (isinstance(identifier, str) and identifier.isdigit()):
        d_num = int(identifier)
        if d_num in df["driver_number"].unique():
            return d_num
        raise ValueError(f"Driver number {d_num} not present in session data.")

    clean_id = str(identifier).strip().lower()
    for d_num, meta in DRIVER_METADATA.items():
        if d_num in df["driver_number"].unique():
            if (
                meta["code"].lower() == clean_id
                or meta["name"].lower() == clean_id
                or clean_id in meta["name"].lower()
            ):
                return d_num

    raise ValueError(f"Driver identifier '{identifier}' could not be resolved from session data.")

