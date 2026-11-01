
import numpy as np
import pandas as pd


def build_rival_state(
    session_df: pd.DataFrame,
    target_driver: int,
    decision_lap: int,
) -> pd.DataFrame:
    """
    Build a point-in-time snapshot of every rival at a decision lap.

    Only data at or before decision_lap is used.
    Future pit stops, tyre changes and lap times are never accessed.

    Requires:
        driver_number
        lap_number
        compound
        tyre_age
        stint_number (recommended)
        position (recommended)
        lap_duration (recommended)

    Returns one row per rival.
    """

    required = {
        "driver_number",
        "lap_number",
        "compound",
        "tyre_age",
    }

    missing = required - set(session_df.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    df = session_df.copy()

    df["lap_number"] = pd.to_numeric(
        df["lap_number"], errors="coerce"
    )

    df = df.dropna(
        subset=["driver_number", "lap_number"]
    )

    # Strict point-in-time filter. No future information.
    df = df[df["lap_number"] <= decision_lap].copy()

    # Exclude drivers who have not started the race.
    active_drivers = df["driver_number"].unique()
    df = df[df["driver_number"].isin(active_drivers)].copy()

    if df.empty:
        raise ValueError(
            f"No race data available up to lap {decision_lap}."
        )

    df = df.sort_values(
        ["driver_number", "lap_number"]
    )

    # Target driver's latest observed state.
    target_rows = df[
        df["driver_number"] == target_driver
    ]

    if target_rows.empty:
        raise ValueError(
            f"Target driver {target_driver} not found "
            f"by lap {decision_lap}."
        )

    target_latest = target_rows.iloc[-1]
    target_lap = int(target_latest["lap_number"])

    # Cumulative time is only comparable at the same lap.
    target_cumulative_time = None

    if "lap_duration" in df.columns:
        target_cumulative_time = (
            pd.to_numeric(
                target_rows["lap_duration"],
                errors="coerce",
            ).sum()
        )

    rival_records = []

    for driver_number, history in df.groupby(
        "driver_number", sort=False
    ):

        if driver_number == target_driver:
            continue

        history = history.sort_values("lap_number")
        latest = history.iloc[-1]

        current_lap = int(latest["lap_number"])
        current_compound = latest["compound"]
        current_tyre_age = latest["tyre_age"]

        # Determine observed stint and pit-stop history.
        pit_stops_observed = np.nan
        current_stint_number = np.nan
        stint_start_lap = np.nan
        last_pit_lap = np.nan

        if "stint_number" in history.columns:

            stints = pd.to_numeric(
                history["stint_number"],
                errors="coerce",
            ).dropna()

            if not stints.empty:
                current_stint_number = stints.iloc[-1]

                observed_stints = stints.nunique()
                pit_stops_observed = max(
                    int(observed_stints) - 1, 0
                )

                current_stint_rows = history[
                    pd.to_numeric(
                        history["stint_number"],
                        errors="coerce",
                    ) == current_stint_number
                ]

                if not current_stint_rows.empty:
                    stint_start_lap = int(
                        current_stint_rows["lap_number"].min()
                    )

                    if stint_start_lap > 1:
                        last_pit_lap = stint_start_lap - 1

        # Stint length based only on observed laps.
        if pd.notna(stint_start_lap):
            stint_length = (
                current_lap - int(stint_start_lap) + 1
            )
        else:
            stint_length = np.nan

        # Latest observed position.
        position = (
            latest["position"]
            if "position" in history.columns
            else np.nan
        )

        # Time gap is calculated only when both drivers
        # have data through the same lap.
        gap_to_target_s = np.nan

        if (
            "lap_duration" in history.columns
            and "lap_duration" in target_rows.columns
            and current_lap == target_lap
        ):
            rival_time = pd.to_numeric(
                history["lap_duration"],
                errors="coerce",
            ).sum()

            if target_cumulative_time is not None:
                gap_to_target_s = (
                    rival_time - target_cumulative_time
                )

        rival_records.append({
            "driver_number": driver_number,
            "lap_observed": current_lap,
            "laps_behind_target": target_lap - current_lap,
            "position": position,
            "compound": current_compound,
            "tyre_age": current_tyre_age,
            "stint_number": current_stint_number,
            "pit_stops_observed": pit_stops_observed,
            "stint_start_lap": stint_start_lap,
            "stint_length": stint_length,
            "last_pit_lap": last_pit_lap,
            "gap_to_target_s": gap_to_target_s,
        })

    rival_state = pd.DataFrame(rival_records)

    if rival_state.empty:
        return rival_state

    return rival_state.sort_values(
        ["position", "driver_number"],
        na_position="last",
    ).reset_index(drop=True)
