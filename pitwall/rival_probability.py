
import numpy as np
import pandas as pd


DEFAULT_STOP_PRIORS = {
    0: 0.15,  # No additional stops
    1: 0.65,  # One additional stop
    2: 0.20,  # Two additional stops
}


def assign_rival_strategy_probabilities(
    rival_strategies: pd.DataFrame,
    stop_count_priors=None,
):
    """
    Assign provisional probabilities to generated rival strategies.

    Method:
    1. Assign a prior probability to each additional-stop count.
    2. Divide that probability equally across distinct pit schedules.
    3. Divide each schedule's probability equally across its
       available compound sequences.

    These are transparent heuristic priors, not learned probabilities.
    """

    required = {
        "strategy_id",
        "driver_number",
        "additional_stops",
        "pit_laps",
        "compounds_after_stops",
    }

    missing = required - set(rival_strategies.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    if rival_strategies.empty:
        raise ValueError("No rival strategies supplied.")

    if rival_strategies["strategy_id"].duplicated().any():
        raise ValueError("strategy_id values must be unique.")

    if stop_count_priors is None:
        stop_count_priors = DEFAULT_STOP_PRIORS

    if any(value < 0 for value in stop_count_priors.values()):
        raise ValueError("Stop-count priors cannot be negative.")

    if sum(stop_count_priors.values()) <= 0:
        raise ValueError("Stop-count priors must have a positive sum.")

    result = rival_strategies.copy()

    result["stop_count_probability"] = 0.0
    result["timing_probability_given_stops"] = 0.0
    result["compound_probability_given_timing"] = 0.0
    result["strategy_probability"] = 0.0
    result["probability_method"] = "rule_based_prior"

    for driver, driver_group in result.groupby("driver_number"):

        available_stop_counts = sorted(
            driver_group["additional_stops"].unique()
        )

        # Keep only stop counts represented in the candidate set.
        available_priors = {
            count: stop_count_priors.get(count, 0.0)
            for count in available_stop_counts
        }

        prior_total = sum(available_priors.values())

        if prior_total <= 0:
            raise ValueError(
                f"No usable stop-count prior for driver {driver}."
            )

        normalized_priors = {
            count: prior / prior_total
            for count, prior in available_priors.items()
        }

        for stop_count, stop_group in driver_group.groupby(
            "additional_stops"
        ):

            stop_probability = normalized_priors[stop_count]

            # Group candidates by their distinct future pit schedules.
            schedules = {}

            for idx, row in stop_group.iterrows():
                schedule = tuple(row["pit_laps"])
                schedules.setdefault(schedule, []).append(idx)

            number_of_schedules = len(schedules)

            if number_of_schedules == 0:
                continue

            timing_probability = 1.0 / number_of_schedules

            for schedule, indices in schedules.items():

                # Divide schedule probability across compound sequences.
                compound_sequences = {}

                for idx in indices:
                    sequence = tuple(
                        stop_group.loc[idx, "compounds_after_stops"]
                    )
                    compound_sequences.setdefault(sequence, []).append(idx)

                number_of_sequences = len(compound_sequences)

                compound_probability = 1.0 / number_of_sequences

                for sequence, sequence_indices in compound_sequences.items():

                    for idx in sequence_indices:
                        result.loc[idx, "stop_count_probability"] = (
                            stop_probability
                        )

                        result.loc[
                            idx, "timing_probability_given_stops"
                        ] = timing_probability

                        result.loc[
                            idx, "compound_probability_given_timing"
                        ] = compound_probability

                        result.loc[idx, "strategy_probability"] = (
                            stop_probability
                            * timing_probability
                            * compound_probability
                        )

    # Verify probabilities sum to one for every rival.
    probability_sums = result.groupby(
        "driver_number"
    )["strategy_probability"].sum()

    if not np.allclose(probability_sums.values, 1.0):
        raise RuntimeError(
            "Strategy probabilities do not sum to 1 for every rival."
        )

    return result
