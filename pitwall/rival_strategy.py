
import itertools
import numpy as np
import pandas as pd


DRY_COMPOUNDS = ["SOFT", "MEDIUM", "HARD"]
WET_COMPOUNDS = ["INTERMEDIATE", "WET"]


def generate_rival_strategies(
    rival_state: pd.DataFrame,
    decision_lap: int,
    race_end_lap: int,
    supported_compounds=None,
    max_stops: int = 2,
    pit_window_step: int = 3,
    min_stint_length: int = 5,
    max_candidates_per_rival: int = 100,
    allowed_compounds_by_driver=None,
):
    """
    Generate plausible future rival strategies.

    No future race information is used.

    allowed_compounds_by_driver:
        Optional dictionary mapping driver numbers to
        compounds allowed for that driver's future scenarios.

        Example:
        {4: ["SOFT", "MEDIUM", "HARD"]}
    """

    if supported_compounds is None:
        supported_compounds = DRY_COMPOUNDS

    supported_compounds = [
        str(c).upper() for c in supported_compounds
    ]

    if decision_lap >= race_end_lap:
        raise ValueError("Decision lap must be before race end.")

    if max_stops < 0:
        raise ValueError("max_stops cannot be negative.")

    if min_stint_length < 1:
        raise ValueError("min_stint_length must be positive.")

    required = {
        "driver_number",
        "compound",
        "tyre_age",
        "pit_stops_observed",
    }

    missing = required - set(rival_state.columns)

    if missing:
        raise ValueError(
            f"Missing columns: {sorted(missing)}"
        )

    # Candidate pit laps.
    pit_laps = list(
        range(
            decision_lap,
            race_end_lap,
            pit_window_step,
        )
    )

    if race_end_lap - 1 not in pit_laps:
        pit_laps.append(race_end_lap - 1)

    pit_laps = sorted(set(pit_laps))

    all_records = []

    for _, rival in rival_state.iterrows():

        driver = int(rival["driver_number"])

        current_compound = rival["compound"]
        tyre_age = rival["tyre_age"]

        if pd.isna(current_compound) or pd.isna(tyre_age):
            continue

        current_compound = str(current_compound).upper()

        if allowed_compounds_by_driver is not None:
            compounds = allowed_compounds_by_driver.get(
                driver, supported_compounds
            )
        else:
            compounds = supported_compounds

        compounds = [
            str(c).upper() for c in compounds
            if str(c).upper() in supported_compounds
        ]

        if not compounds:
            continue

        observed_stops = (
            0 if pd.isna(rival["pit_stops_observed"])
            else int(rival["pit_stops_observed"])
        )

        # Prefer changing compound at a stop.
        first_stop_compounds = [
            c for c in compounds
            if c != current_compound
        ]

        if not first_stop_compounds:
            first_stop_compounds = compounds.copy()

        records = []

        # No further stops.
        records.append(((), ()))

        # One additional stop.
        if max_stops >= 1:

            for pit_lap in pit_laps:

                remaining_laps = race_end_lap - pit_lap

                if remaining_laps < min_stint_length:
                    continue

                for compound in first_stop_compounds:

                    records.append((
                        (pit_lap,),
                        (compound,),
                    ))

        # Two additional stops.
        if max_stops >= 2:

            for first_pit, second_pit in itertools.combinations(
                pit_laps, 2
            ):

                first_stint = second_pit - first_pit
                final_stint = race_end_lap - second_pit

                if first_stint < min_stint_length:
                    continue

                if final_stint < min_stint_length:
                    continue

                for first_compound, second_compound in itertools.product(
                    first_stop_compounds, compounds
                ):

                    records.append((
                        (first_pit, second_pit),
                        (first_compound, second_compound),
                    ))

        # Balanced selection across stop counts.
        selected = []

        for stop_count in range(max_stops + 1):

            group = [
                record for record in records
                if len(record[0]) == stop_count
            ]

            remaining_slots = (
                max_candidates_per_rival - len(selected)
            )

            if remaining_slots <= 0:
                break

            if len(group) <= remaining_slots:
                selected.extend(group)
            else:
                indices = np.linspace(
                    0,
                    len(group) - 1,
                    remaining_slots,
                    dtype=int,
                )
                selected.extend(
                    [group[i] for i in indices]
                )

        for index, (future_pits, future_compounds) in enumerate(
            selected, start=1
        ):

            all_records.append({
                "strategy_id": f"D{driver}_S{index:03d}",
                "driver_number": driver,
                "current_compound": current_compound,
                "current_tyre_age": float(tyre_age),
                "observed_stops": observed_stops,
                "additional_stops": len(future_pits),
                "total_projected_stops": (
                    observed_stops + len(future_pits)
                ),
                "pit_laps": future_pits,
                "compounds_after_stops": future_compounds,
                "decision_lap": decision_lap,
                "race_end_lap": race_end_lap,
            })

    return pd.DataFrame(all_records)
