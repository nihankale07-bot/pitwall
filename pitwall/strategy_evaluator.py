
"""Evaluate target strategies against probabilistic rival scenarios."""

import numpy as np
import pandas as pd


def evaluate_strategies_against_rivals(
    own_replay_results,
    rival_scenario_results,
    rival_state,
    session_df,
    target_driver,
    decision_lap,
    n_scenarios=1000,
    random_state=42,
):
    """
    Evaluate target strategies against sampled rival strategies.

    All target strategies are evaluated against exactly the same
    sampled rival scenarios using common random numbers.

    Important assumptions:
    - Rival state represents information available at decision_lap.
    - Rival projected times were generated using causal forecasts.
    - Current gaps are held constant when estimating rival finish times.
    """

    # --------------------------------------------------------
    # 1. INPUT VALIDATION
    # --------------------------------------------------------

    required_rival = {
        "driver_number",
        "strategy_id",
        "strategy_probability",
        "projected_future_time_s",
    }

    required_state = {
        "driver_number",
        "position",
        "gap_to_target_s",
    }

    required_session = {
        "driver_number",
        "lap_number",
        "lap_duration",
        "position",
    }

    missing = required_rival - set(rival_scenario_results.columns)
    if missing:
        raise ValueError(
            f"Missing rival scenario columns: {sorted(missing)}"
        )

    missing = required_state - set(rival_state.columns)
    if missing:
        raise ValueError(
            f"Missing rival state columns: {sorted(missing)}"
        )

    missing = required_session - set(session_df.columns)
    if missing:
        raise ValueError(
            f"Missing session columns: {sorted(missing)}"
        )

    if n_scenarios < 1:
        raise ValueError("n_scenarios must be positive.")

    target_driver = int(target_driver)
    decision_lap = int(decision_lap)

    if not own_replay_results:
        raise ValueError("No target replay results were supplied.")

    # --------------------------------------------------------
    # 2. TARGET DECISION-TIME STATE
    # --------------------------------------------------------

    # Only observations available at the decision point.
    target_rows = session_df[
        (session_df["driver_number"] == target_driver)
        & (session_df["lap_number"] <= decision_lap)
    ].sort_values("lap_number")

    if target_rows.empty:
        raise ValueError("Target driver has no recorded laps.")

    decision_rows = target_rows[
        target_rows["lap_number"] == decision_lap
    ]

    if decision_rows.empty:
        raise ValueError(
            f"Target driver has no recorded lap at decision_lap={decision_lap}."
        )

    target_elapsed = pd.to_numeric(
        target_rows["lap_duration"],
        errors="coerce",
    ).sum()

    target_position = decision_rows.iloc[-1]["position"]

    if pd.isna(target_position):
        raise ValueError(
            "Target position is missing at the decision lap."
        )

    target_position = int(target_position)

    # --------------------------------------------------------
    # 3. PREPARE RIVAL STATE
    # --------------------------------------------------------

    states = rival_state[
        (rival_state["driver_number"] != target_driver)
        & rival_state["gap_to_target_s"].notna()
        & rival_state["position"].notna()
    ].copy()

    states["driver_number"] = states["driver_number"].astype(int)

    states["position"] = pd.to_numeric(
        states["position"], errors="coerce"
    )

    states["gap_to_target_s"] = pd.to_numeric(
        states["gap_to_target_s"], errors="coerce"
    )

    states = states.dropna(
        subset=["position", "gap_to_target_s"]
    )

    if states.empty:
        raise ValueError("No rivals have usable gaps.")

    # Negative gap = rival ahead.
    # Positive gap = rival behind.
    states["signed_gap_s"] = np.where(
        states["position"] < target_position,
        -states["gap_to_target_s"].abs(),
        states["gap_to_target_s"].abs(),
    )

    # Avoid duplicate rival states.
    if states["driver_number"].duplicated().any():
        raise ValueError(
            "rival_state contains duplicate driver entries."
        )

    # --------------------------------------------------------
    # 4. SAMPLE RIVAL SCENARIOS ONCE
    # --------------------------------------------------------

    rng = np.random.default_rng(random_state)

    rival_drivers = []
    rival_finish_times = []
    sampled_strategy_ids = {}

    for _, state in states.iterrows():

        driver = int(state["driver_number"])

        group = rival_scenario_results[
            rival_scenario_results["driver_number"] == driver
        ].copy()

        if group.empty:
            continue

        probabilities = pd.to_numeric(
            group["strategy_probability"],
            errors="coerce",
        ).to_numpy(dtype=float, copy=True)

        future_times = pd.to_numeric(
            group["projected_future_time_s"],
            errors="coerce",
        ).to_numpy(dtype=float, copy=True)

        if (
            not np.isfinite(probabilities).all()
            or (probabilities < 0).any()
            or probabilities.sum() <= 0
        ):
            raise ValueError(
                f"Invalid strategy probabilities for driver {driver}."
            )

        if (
            not np.isfinite(future_times).all()
            or (future_times < 0).any()
        ):
            raise ValueError(
                f"Invalid projected future times for driver {driver}."
            )

        probabilities /= probabilities.sum()

        # Sample this rival's future strategies exactly once.
        sampled_indices = rng.choice(
            len(group),
            size=n_scenarios,
            replace=True,
            p=probabilities,
        )

        sampled_times = future_times[sampled_indices]

        sampled_strategy_ids[driver] = (
            group["strategy_id"]
            .to_numpy()[sampled_indices]
        )

        # Approximate rival finish time:
        # target elapsed time + signed current gap + rival future time.
        finish_times = (
            target_elapsed
            + float(state["signed_gap_s"])
            + sampled_times
        )

        rival_drivers.append(driver)
        rival_finish_times.append(finish_times)

    if not rival_finish_times:
        raise ValueError("No rival scenarios could be sampled.")

    # Shape: scenarios x rivals.
    # This exact matrix is reused for every target strategy.
    rival_finish_times = np.column_stack(rival_finish_times)

    # --------------------------------------------------------
    # 5. EVALUATE EVERY TARGET STRATEGY
    # --------------------------------------------------------

    records = []

    for strategy_id, replay_result in own_replay_results.items():

        summary = replay_result.summary

        if not isinstance(summary, dict):
            summary = dict(summary)

        # Verify the replay belongs to this decision point.
        if summary.get("target_driver") != target_driver:
            raise ValueError(
                f"Target driver mismatch in strategy {strategy_id}."
            )

        if summary.get("decision_lap") != decision_lap:
            raise ValueError(
                f"Decision lap mismatch in strategy {strategy_id}."
            )

        own_finish_time = summary.get(
            "final_cumulative_time"
        )

        if own_finish_time is None:
            raise ValueError(
                f"Missing final_cumulative_time for {strategy_id}."
            )

        own_finish_time = float(own_finish_time)

        if not np.isfinite(own_finish_time):
            raise ValueError(
                f"Invalid projected finish time for {strategy_id}."
            )

        # Position is calculated against the same rival matrix
        # for every strategy.
        #
        # Ties are conservatively counted against the target.
        positions = (
            1 + (rival_finish_times <= own_finish_time).sum(axis=1)
        )

        records.append({

            "strategy_id": strategy_id,

            "projected_finish_time_s": own_finish_time,

            "win_probability": np.mean(positions == 1),

            "podium_probability": np.mean(positions <= 3),

            "top5_probability": np.mean(positions <= 5),

            "expected_finish_position": np.mean(positions),

            "median_finish_position": np.median(positions),

            "worst_decile_position": np.quantile(
                positions, 0.90
            ),

            "scenarios_evaluated": n_scenarios,

            "rivals_included": len(rival_drivers),

        })

    # --------------------------------------------------------
    # 6. RANK STRATEGIES
    # --------------------------------------------------------

    evaluation = pd.DataFrame(records)

    evaluation = evaluation.sort_values(
        [
            "win_probability",
            "expected_finish_position",
            "projected_finish_time_s",
        ],
        ascending=[False, True, True],
    ).reset_index(drop=True)

    evaluation.insert(
        0,
        "strategy_rank",
        np.arange(1, len(evaluation) + 1),
    )

    return evaluation
