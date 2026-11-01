
"""Decision-time multi-stop strategy candidate generation."""

from typing import Optional, Set, Tuple, Dict, List

import pandas as pd


def generate_multi_stop_candidates(
    race_df: pd.DataFrame,
    target_driver: int,
    decision_lap: int,
    race_length: Optional[int] = None,
    pit_window: int = 5,
    pit_intervals: tuple = (1, 2, 3, 4, 5),
    max_stops: int = 2,
    supported_compounds: Optional[Set[str]] = None,
    min_stint_length: int = 5,
) -> pd.DataFrame:
    """
    Generate strategy candidates using information available
    up to decision_lap only.

    No actual future pit stops, compounds, lap times or weather
    observations are used.

    Candidate strategies are generated from:
    - Current driver state
    - Remaining race distance
    - Supported compounds
    - Predefined pit-window rules
    """

    if supported_compounds is None:
        supported_compounds = {
            "SOFT", "MEDIUM", "HARD", "INTERMEDIATE"
        }

    if race_df is None or race_df.empty:
        raise ValueError("race_df must contain race-lap data.")

    required = {
        "driver_number",
        "lap_number",
        "compound",
    }

    missing = required - set(race_df.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    if max_stops < 0:
        raise ValueError("max_stops cannot be negative.")

    if min_stint_length < 1:
        raise ValueError("min_stint_length must be positive.")

    # --------------------------------------------------
    # 1. Restrict information to the decision point
    # --------------------------------------------------

    history = race_df[
        race_df["lap_number"] <= decision_lap
    ].copy()

    target_laps = (
        history[
            history["driver_number"] == target_driver
        ]
        .sort_values("lap_number")
    )

    if target_laps.empty:
        raise ValueError(
            f"No target-driver history through lap {decision_lap}."
        )

    decision_rows = target_laps[
        target_laps["lap_number"] == decision_lap
    ]

    if decision_rows.empty:
        raise ValueError(
            f"Target driver has no recorded lap at "
            f"decision_lap={decision_lap}."
        )

    current = decision_rows.iloc[-1]

    current_compound = str(current["compound"]).upper()

    if race_length is None:
        raise ValueError(
            "Provide race_length explicitly. Do not infer it "
            "from future observed laps in decision-time mode."
        )

    race_length = int(race_length)

    if decision_lap >= race_length:
        raise ValueError("Decision lap must precede race end.")

    remaining_laps = race_length - decision_lap

    # Current weather only.
    current_rainfall = (
        pd.to_numeric(
            pd.Series([current.get("rainfall", 0)]),
            errors="coerce"
        ).iloc[0]
    )

    current_rainfall = (
        0.0 if pd.isna(current_rainfall)
        else float(current_rainfall)
    )

    currently_wet = (
        current_rainfall > 0
        or current_compound in {"INTERMEDIATE", "WET"}
    )

    compounds = sorted({
        str(c).upper() for c in supported_compounds
    })

    dry_compounds = [
        c for c in ["SOFT", "MEDIUM", "HARD"]
        if c in compounds
    ]

    wet_compounds = [
        c for c in ["INTERMEDIATE", "WET"]
        if c in compounds
    ]

    if not dry_compounds and not wet_compounds:
        raise ValueError("No supported compounds available.")

    # --------------------------------------------------
    # 2. Define decision-time compound pools
    # --------------------------------------------------

    if currently_wet:
        first_stop_compounds = wet_compounds + dry_compounds
    else:
        first_stop_compounds = dry_compounds

    if not first_stop_compounds:
        raise ValueError("No valid first-stop compounds.")

    # --------------------------------------------------
    # 3. Candidate creation
    # --------------------------------------------------

    candidates: List[Dict] = []
    seen = set()

    def add_candidate(
        sequence: Tuple[Tuple[int, str], ...]
    ):
        if sequence in seen:
            return

        seen.add(sequence)

        candidates.append({
            "pit_sequence": sequence,
            "pit_sequence_str": (
                " -> ".join(
                    f"{compound} lap {lap}"
                    for lap, compound in sequence
                )
                if sequence else "Stay out"
            ),
            "current_compound": current_compound,
            "num_stops": len(sequence),
            "description": (
                "Stay out"
                if not sequence
                else " -> ".join(
                    f"Pit lap {lap}, fit {compound}"
                    for lap, compound in sequence
                )
            ),
        })

    # No further stops.
    add_candidate(())

    # --------------------------------------------------
    # 4. Generate possible first-stop windows
    # --------------------------------------------------

    earliest_pit = decision_lap + min_stint_length

    latest_pit = race_length - min_stint_length

    first_pit_laps = list(
        range(
            earliest_pit,
            min(
                decision_lap + pit_window + 1,
                latest_pit + 1
            ),
        )
    )

    # Additional regularly spaced windows.
    first_pit_laps.extend(
        range(
            earliest_pit,
            latest_pit + 1,
            max(1, pit_window)
        )
    )

    first_pit_laps = sorted(set(first_pit_laps))

    for pit_lap in first_pit_laps:

        for compound in first_stop_compounds:

            add_candidate(((pit_lap, compound),))

    # --------------------------------------------------
    # 5. Generate two-stop candidates
    # --------------------------------------------------

    if max_stops >= 2:

        for first_pit in first_pit_laps:

            for first_compound in first_stop_compounds:

                earliest_second = (
                    first_pit + min_stint_length
                )

                latest_second = (
                    race_length - min_stint_length
                )

                second_pit_laps = list(
                    range(
                        earliest_second,
                        latest_second + 1,
                        max(1, pit_window)
                    )
                )

                for second_pit in second_pit_laps:

                    second_compounds = (
                        dry_compounds + wet_compounds
                    )

                    for second_compound in second_compounds:

                        add_candidate((
                            (first_pit, first_compound),
                            (second_pit, second_compound),
                        ))

    # --------------------------------------------------
    # 6. Return candidates
    # --------------------------------------------------

    result = pd.DataFrame(candidates)

    result = result.sort_values(
        ["num_stops", "pit_sequence_str"]
    ).reset_index(drop=True)

    result["strategy_id"] = [
        f"S{i:03d}"
        for i in range(1, len(result) + 1)
    ]

    return result
