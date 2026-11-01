
import numpy as np
import pandas as pd


def simulate_rival_scenarios(
    rival_state: pd.DataFrame,
    rival_strategy_probs: pd.DataFrame,
    pace_model,
    decision_lap: int,
    race_end_lap: int,
    pit_loss: float = 22.0,
):
    """
    Simulate each rival's possible future strategy.

    Uses causal pace predictions only. No actual future lap times
    or future race conditions are used.

    Convention:
    A pit_lap value represents the last completed lap before
    pitting. For example, pit_lap=26 means the stop occurs
    on lap 27.

    Returns:
        scenario_results: one row per rival strategy
        rival_summary: probability-weighted summary per rival
    """

    required_state = {
        "driver_number",
        "compound",
        "tyre_age",
    }

    required_strategies = {
        "strategy_id",
        "driver_number",
        "pit_laps",
        "compounds_after_stops",
        "strategy_probability",
    }

    missing_state = required_state - set(rival_state.columns)
    missing_strategies = required_strategies - set(
        rival_strategy_probs.columns
    )

    if missing_state:
        raise ValueError(
            f"Missing rival-state columns: {sorted(missing_state)}"
        )

    if missing_strategies:
        raise ValueError(
            f"Missing strategy columns: {sorted(missing_strategies)}"
        )

    if decision_lap >= race_end_lap:
        raise ValueError("Decision lap must be before race end.")

    if pit_loss < 0:
        raise ValueError("Pit loss cannot be negative.")

    state_lookup = (
        rival_state
        .set_index("driver_number")
        .to_dict("index")
    )

    results = []

    for _, strategy in rival_strategy_probs.iterrows():

        driver = int(strategy["driver_number"])

        if driver not in state_lookup:
            continue

        state = state_lookup[driver]

        current_compound = state["compound"]
        current_tyre_age = state["tyre_age"]

        if pd.isna(current_compound) or pd.isna(current_tyre_age):
            continue

        current_compound = str(current_compound).upper()
        tyre_age = int(current_tyre_age)

        pit_laps = tuple(strategy["pit_laps"])
        new_compounds = tuple(strategy["compounds_after_stops"])

        if len(pit_laps) != len(new_compounds):
            raise ValueError(
                f"Pit schedule and compound sequence mismatch "
                f"for {strategy['strategy_id']}."
            )

        if tuple(sorted(pit_laps)) != pit_laps:
            raise ValueError(
                f"Pit laps must be chronological: "
                f"{strategy['strategy_id']}."
            )

        if any(
            pit_lap < decision_lap or pit_lap >= race_end_lap
            for pit_lap in pit_laps
        ):
            raise ValueError(
                f"Invalid future pit lap in {strategy['strategy_id']}."
            )

        # Map each pit stop to the lap immediately after the
        # last completed lap in pit_laps.
        pit_schedule = {
            int(pit_lap) + 1: compound
            for pit_lap, compound in zip(pit_laps, new_compounds)
        }

        compound = current_compound
        projected_time = 0.0
        projected_pit_loss = 0.0
        projected_laps = []

        for lap in range(decision_lap + 1, race_end_lap + 1):

            # Apply the new compound when the car returns from the pits.
            if lap in pit_schedule:
                compound = str(pit_schedule[lap]).upper()
                tyre_age = 0

                projected_pit_loss += pit_loss

            tyre_age += 1

            lap_time = pace_model.predict_lap(
                lap_number=lap,
                driver_number=driver,
                compound=compound,
                tyre_age=tyre_age,
                mode="causal",
                decision_lap=decision_lap,
            )

            # Pit loss is added to the first lap on the new tyres.
            if lap in pit_schedule:
                lap_time += pit_loss

            projected_time += lap_time

            projected_laps.append({
                "lap_number": lap,
                "compound": compound,
                "tyre_age": tyre_age,
                "predicted_lap_time": lap_time,
            })

        results.append({
            "strategy_id": strategy["strategy_id"],
            "driver_number": driver,
            "additional_stops": len(pit_laps),
            "pit_laps": pit_laps,
            "compounds_after_stops": new_compounds,
            "strategy_probability": float(
                strategy["strategy_probability"]
            ),
            "projected_future_time_s": projected_time,
            "projected_pit_loss_s": projected_pit_loss,
            "projected_total_time_s": projected_time,
            "projected_laps": projected_laps,
        })

    scenario_results = pd.DataFrame(results)

    if scenario_results.empty:
        raise ValueError("No rival scenarios could be simulated.")

    # Probability-weighted expected remaining time per rival.
    summary_records = []

    for driver, group in scenario_results.groupby("driver_number"):

        probabilities = group["strategy_probability"].to_numpy()
        times = group["projected_future_time_s"].to_numpy()

        probability_total = probabilities.sum()

        if probability_total <= 0:
            raise ValueError(
                f"Invalid probabilities for driver {driver}."
            )

        probabilities = probabilities / probability_total

        expected_time = np.sum(probabilities * times)

        most_likely_idx = group[
            "strategy_probability"
        ].idxmax()

        summary_records.append({
            "driver_number": driver,
            "scenario_count": len(group),
            "expected_future_time_s": expected_time,
            "best_case_time_s": times.min(),
            "worst_case_time_s": times.max(),
            "most_likely_strategy": scenario_results.loc[
                most_likely_idx, "strategy_id"
            ],
        })

    rival_summary = pd.DataFrame(summary_records)

    return scenario_results, rival_summary
