#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
weather_validation.py

Diagnostic script for the PITWALL repository.

What it does
------------
1. Loads the processed parquet files for session 9558.
2. Inspects and prints the column schemas (no assumptions about column names).
3. Computes the *actual* cumulative race times for Oscar Piastri (driver 81)
   and Lewis Hamilton (driver 44).
4. Re‑creates the production counter‑factual prediction for each driver
   using the real optimizer / replay code (decision lap 26).
5. Performs an as‑of join between lap start timestamps and weather
   observations, exposing the lag and any missing records.
6. Runs a leakage‑safe forward validation that does **not** rely on the
   categorical lap‑number fixed effects for unseen laps.  The validation
   compares three models:
      a) the original fixed‑effects `PaceModel` (trained on the training set
         only – predictions are limited to lap numbers seen during training),
      b) a simple weather‑aware linear model (lap_duration ~ rainfall +
         tyre_age + C(compound)),
      c) a baseline predictor that always returns the median training lap
         duration.
   Errors are reported separately for dry and wet laps.
7. Prints the signatures of `PaceModel`, `optimize_strategy` and
   `engine.replay` so the developer can verify they match the library.
8. Writes three artefacts in the `scratch` folder:
      * weather_validation_report.txt – narrative with all results.
      * weather_validation_laps.csv   – actual vs. predicted lap‑by‑lap data.
      * weather_alignment.csv        – timestamp‑aware weather join.

The script never modifies production code, never changes pit‑loss logic, and
does not push or commit anything.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import statsmodels.formula.api as smf
import statsmodels.api as sm

# ----------------------------------------------------------------------
# Helper utilities
# ----------------------------------------------------------------------
def print_header(msg: str) -> None:
    print(f"\n=== {msg} ===")

def schema(df: pd.DataFrame) -> str:
    return ", ".join([f"{c}({dt})" for c, dt in zip(df.columns, df.dtypes)])

def asof_join_laps_weather(
    laps: pd.DataFrame,
    weather: pd.DataFrame
) -> pd.DataFrame:
    """
    Join each lap with the most recent weather observation.
    Preserve laps with missing timestamps instead of dropping them.
    """

    laps = laps.copy()
    weather = weather.copy()

    # Preserve original row order and identity.
    laps["_original_row"] = np.arange(len(laps))

    # Normalize timestamps to UTC.
    laps["date_start"] = pd.to_datetime(
        laps["date_start"], utc=True, errors="coerce"
    )
    weather["date"] = pd.to_datetime(
        weather["date"], utc=True, errors="coerce"
    )

    missing_timestamp_count = laps["date_start"].isna().sum()
    missing_weather_timestamp_count = weather["date"].isna().sum()

    if missing_timestamp_count:
        print(
            f"WARNING: {missing_timestamp_count} lap(s) have "
            "missing timestamps. Preserving these rows."
        )

    if missing_weather_timestamp_count:
        print(
            f"WARNING: Excluding {missing_weather_timestamp_count} "
            "weather observation(s) with missing timestamps."
        )

    # Separate timestamp-valid and timestamp-missing laps.
    valid_laps = laps[laps["date_start"].notna()].copy()
    invalid_laps = laps[laps["date_start"].isna()].copy()

    valid_weather = weather[weather["date"].notna()].copy()

    weather_columns = [
        "date",
        "rainfall",
        "track_temperature",
        "air_temperature",
    ]

    # Perform timestamp-based alignment only where timestamps exist.
    if not valid_laps.empty and not valid_weather.empty:
        valid_laps = valid_laps.sort_values("date_start")
        valid_weather = valid_weather[weather_columns].sort_values("date")

        valid_merged = pd.merge_asof(
            valid_laps,
            valid_weather,
            left_on="date_start",
            right_on="date",
            direction="backward",
            tolerance=pd.Timedelta("65s"),
        )
    else:
        valid_merged = valid_laps.copy()
        for column in weather_columns:
            if column != "date":
                valid_merged[column] = np.nan
        valid_merged["date"] = pd.NaT

    # Preserve incomplete lap records with empty weather fields.
    for column in weather_columns:
        if column != "date":
            invalid_laps[column] = np.nan

    invalid_laps["date"] = pd.NaT

    # Recombine without losing any original lap rows.
    merged = pd.concat(
        [valid_merged, invalid_laps],
        ignore_index=True,
    )

    merged = merged.sort_values("_original_row").reset_index(drop=True)

    merged.rename(
        columns={"date": "weather_timestamp"},
        inplace=True,
    )

    # Restore datetime dtypes after recombining valid and invalid rows.
    merged["date_start"] = pd.to_datetime(
       merged["date_start"], utc=True, errors="coerce"
    )

    
    merged["weather_timestamp"] = pd.to_datetime(
       merged["weather_timestamp"], utc=True, errors="coerce"
    )

# Calculate weather observation lag safely.
    merged["weather_lag_seconds"] = (
       merged["date_start"] - merged["weather_timestamp"]
    ).dt.total_seconds()

    merged["timestamp_missing"] = merged["date_start"].isna()
    merged["missing_weather"] = merged["weather_timestamp"].isna()

    print(f"Lap rows preserved: {len(merged)} / {len(laps)}")
    print(f"Missing lap timestamps: {merged['timestamp_missing'].sum()}")
    print(f"Unmatched weather observations: {merged['missing_weather'].sum()}")

    return merged

# ----------------------------------------------------------------------
# 1. Load parquet files and inspect schemas
# ----------------------------------------------------------------------
ROOT = Path("C:/Users/Nihan/.vscode/pitwall")
PROC = ROOT / "data" / "processed" / "9558"

print_header("Loading parquet files")
laps = pd.read_parquet(PROC / "laps.parquet")
stints = pd.read_parquet(PROC / "stints.parquet")
tyre = pd.read_parquet(PROC / "tyre_features.parquet")
weather = pd.read_parquet(PROC / "weather.parquet")

print("laps columns    :", schema(laps))
print("stints columns  :", schema(stints))
print("tyre columns    :", schema(tyre))
print("weather columns :", schema(weather))

# ----------------------------------------------------------------------
# 2. Build a unified lap table (compound, tyre_age, timestamps)
# ----------------------------------------------------------------------
print_header("Deriving per‑lap compound from stints (with data‑quality handling)")
# Discover lap start/end columns
lap_start_col = None
lap_end_col = None
for col in stints.columns:
    if "lap" in col.lower() and "start" in col.lower():
        lap_start_col = col
    if "lap" in col.lower() and "end" in col.lower():
        lap_end_col = col
if not lap_start_col or not lap_end_col:
    raise RuntimeError("stints.parquet does not contain identifiable lap_start/lap_end columns")

# Collect compound assignments, track incomplete stints for warnings
incomplete_stints = []
compound_rows = []
for idx, row in stints.iterrows():
    start = row[lap_start_col]
    end = row[lap_end_col]
    if pd.isna(start) or pd.isna(end):
        incomplete_stints.append({
            "index": idx,
            "driver_number": row.get("driver_number"),
            "lap_start": start,
            "lap_end": end,
            "compound": row.get("compound"),
        })
        # Skip this stint for compound mapping
        continue
    # Convert to int (they should be whole numbers)
    start_int = int(start)
    end_int = int(end)
    for lap in range(start_int, end_int + 1):
        compound_rows.append({
            "driver_number": row["driver_number"],
            "lap_number": lap,
            "compound": row["compound"]
        })
compound_df = pd.DataFrame(compound_rows)

# Verify that every lap for Piastri (81) and Hamilton (44) receives exactly one compound
def _check_assignments(comp_df, driver_num):
    driver_laps = laps[laps["driver_number"] == driver_num]["lap_number"].unique()
    assigned_laps = comp_df[comp_df["driver_number"] == driver_num]["lap_number"].unique()
    missing = set(driver_laps) - set(assigned_laps)
    dup_counts = comp_df[comp_df["driver_number"] == driver_num]["lap_number"].value_counts()
    duplicates = dup_counts[dup_counts > 1].index.tolist()
    return missing, duplicates

piastri_missing, piastri_dups = _check_assignments(compound_df, 81)
hamilton_missing, hamilton_dups = _check_assignments(compound_df, 44)

data_quality_warnings = []
if piastri_missing:
    data_quality_warnings.append(f"Piastri missing compound for laps: {sorted(piastri_missing)}")
if piastri_dups:
    data_quality_warnings.append(f"Piastri duplicate compound assignments for laps: {sorted(piastri_dups)}")
if hamilton_missing:
    data_quality_warnings.append(f"Hamilton missing compound for laps: {sorted(hamilton_missing)}")
if hamilton_dups:
    data_quality_warnings.append(f"Hamilton duplicate compound assignments for laps: {sorted(hamilton_dups)}")

# Merge laps with tyre age and compound
merged = laps.merge(
    tyre[["driver_number", "lap_number", "tyre_age"]].copy(),
    on=["driver_number", "lap_number"],
    how="left",
)
merged = merged.merge(compound_df, on=["driver_number", "lap_number"], how="left")

# Ensure timestamps are datetime
if not pd.api.types.is_datetime64_any_dtype(merged["date_start"].dtype):
    merged["date_start"] = pd.to_datetime(merged["date_start"], utc=True, errors="coerce")
if not pd.api.types.is_datetime64_any_dtype(weather["date"].dtype):
    weather["date"] = pd.to_datetime(weather["date"], utc=True, errors="coerce")

# ----------------------------------------------------------------------
# 3. Actual race totals for drivers 81 and 44
# ----------------------------------------------------------------------
print_header("Computing actual race totals")

def driver_actuals(num: int) -> pd.DataFrame:
    df = merged[merged["driver_number"] == num].copy()
    df = df.sort_values("lap_number")
    return df[["lap_number", "lap_duration", "compound", "tyre_age", "is_pit_out_lap"]]

piastri_actual = driver_actuals(81)
hamilton_actual = driver_actuals(44)

def total_time(df: pd.DataFrame) -> float:
    return float(df["lap_duration"].sum())

piastri_total = total_time(piastri_actual)
hamilton_total = total_time(hamilton_actual)

print(f"Piastri actual total time: {piastri_total:.3f} s (laps={len(piastri_actual)})")
print(f"Hamilton actual total time: {hamilton_total:.3f} s (laps={len(hamilton_actual)})")

# ----------------------------------------------------------------------
# 4. Re‑create production counter‑factual predictions
# ----------------------------------------------------------------------
print_header("Fitting the production PaceModel and running optimizer")
# Make repository importable
sys.path.append(str(ROOT))
from pitwall.pace_model import PaceModel
from pitwall.optimizer import optimize_strategy

from pitwall.data import load_race

# Load the canonical production training dataset
production_df = load_race(session_key=9558)

# Verify required production features
required_columns = [
    "is_clean_lap",
    "is_pit_in_lap",
    "is_pit_out_lap",
    "is_sc_vsc_lap",
    "is_gross_outlier",
    "lap_duration",
    "compound",
    "tyre_age",
    "driver_number",
    "lap_number",
]

missing = [col for col in required_columns if col not in production_df.columns]

if missing:
    raise ValueError(
        f"Production dataset missing required columns: {missing}"
    )

print("\n=== Production training data ===")

for driver in [81, 44]:
    driver_df = production_df[
        production_df["driver_number"] == driver
    ]

    clean_count = int(driver_df["is_clean_lap"].fillna(False).sum())
    excluded_count = len(driver_df) - clean_count

    print(
        f"Driver {driver}: "
        f"{clean_count} clean laps, "
        f"{excluded_count} excluded laps"
    )

pace = PaceModel()
# NOTE: The optimizer re-fits the model internally on laps <= decision_lap,
# so this pre-fit is only used to establish the reference_compound template.
# We still call fit() here to verify the production_df passes model fitting.
pace = pace.fit(production_df)  # full-race fit for verification only

# Helper to run optimizer for a driver (decision lap 26)
#
# IMPORTANT: optimize_strategy() must receive production_df (the canonical
# DataFrame from load_race()) so that is_clean_lap is present.  The optimizer
# uses that flag to fit the PaceModel on clean historical laps only.
# `merged` (the weather-enriched table) does NOT carry is_clean_lap and must
# NOT be passed here.

def run_counterfactual(driver_num: int, decision_lap: int = 26):
    # Validate that production_df carries is_clean_lap before dispatching.
    if "is_clean_lap" not in production_df.columns:
        raise RuntimeError(
            "production_df is missing is_clean_lap; cannot run leakage-safe optimizer."
        )

    result = optimize_strategy(
        session_df=production_df,     # canonical df with is_clean_lap
        target_driver=driver_num,
        decision_lap=decision_lap,
        race_length=52,
        pace_model=PaceModel(),       # fresh unfitted instance; optimizer re-fits on history
        pit_loss=22.0,
        track_mode="causal",          # freeze lap effect at decision_lap for future laps
        max_stops=2,
        max_candidates=None,          # let optimizer generate all candidates
    )
    # Best replay according to the optimizer's ranking
    best = result.best_replay
    # Simulated laps for the target driver (future laps only)
    sim = best.laps_table.copy()
    sim = sim[sim["lap_number"] > decision_lap].sort_values("lap_number")
    # Keep columns of interest, falling back gracefully if any are absent
    cols = ["lap_number", "lap_duration", "compound", "tyre_age", "is_pit_out_lap"]
    sim = sim[[c for c in cols if c in sim.columns]]
    return sim, best.summary

piastri_sim, piastri_summary = run_counterfactual(81)
hamilton_sim, hamilton_summary = run_counterfactual(44)

# ----------------------------------------------------------------------
# 5. Weather alignment using the enriched lap table
# ----------------------------------------------------------------------
print_header("Aligning weather observations to enriched laps")

# IMPORTANT: Use merged, not raw laps.
weather_aligned = asof_join_laps_weather(merged, weather)

weather_alignment_path = ROOT / "scratch" / "weather_alignment.csv"
weather_aligned.to_csv(weather_alignment_path, index=False)

# ----------------------------------------------------------------------
# 6. Forward validation
# ----------------------------------------------------------------------
print_header("Forward validation (train laps 1-20, test laps 21-35)")

validation_df = weather_aligned.copy()

# Exclude incomplete observations from model fitting/scoring only.
required = [
    "lap_duration",
    "lap_number",
    "driver_number",
    "compound",
    "tyre_age",
]

validation_df = validation_df.dropna(subset=required)

train = validation_df[
    (validation_df["lap_number"] <= 20)
].copy()

test = validation_df[
    (validation_df["lap_number"] > 20)
    & (validation_df["lap_number"] <= 35)
].copy()

# Require valid weather observations for weather-aware comparison.
weather_train = train.dropna(subset=["rainfall"]).copy()
weather_test = test.dropna(subset=["rainfall"]).copy()

print(f"Training observations: {len(train)}")
print(f"Testing observations: {len(test)}")
print(f"Weather training observations: {len(weather_train)}")
print(f"Weather testing observations: {len(weather_test)}")

print("Training compounds:", sorted(train["compound"].unique()))
print("Testing compounds:", sorted(test["compound"].unique()))

if train.empty or test.empty:
    raise ValueError("Insufficient observations for forward validation.")

# a) Extrapolatable pace model.
# Categorical lap-number effects cannot predict unseen future laps.
base_formula = (
    "lap_duration ~ lap_number + C(driver_number) "
    "+ C(compound) + tyre_age "
    "+ C(compound):tyre_age"
)
import patsy

y_design, X_design = patsy.dmatrices(
    base_formula,
    data=train,
    return_type="dataframe"
)

matrix_rank = np.linalg.matrix_rank(
    X_design.to_numpy(dtype=float)
)

print("\n=== Base model identifiability ===")
print("Design matrix shape:", X_design.shape)
print("Matrix rank:", matrix_rank)
print("Rank deficiency:", X_design.shape[1] - matrix_rank)
base_res = smf.ols(
    base_formula,
    data=train,
).fit()

base_pred = base_res.predict(test)

# b) Weather-aware model.
weather_formula = (
    "lap_duration ~ lap_number + rainfall "
    "+ tyre_age + C(compound)"
)

if weather_train.empty or weather_test.empty:
    raise ValueError(
        "Insufficient timestamp-aligned weather observations "
        "for weather-aware validation."
    )

weather_res = smf.ols(
    weather_formula,
    data=weather_train,
).fit()

weather_pred = weather_res.predict(weather_test)

# c) Median baseline.
median_lap = train["lap_duration"].median()

baseline_pred = np.full(len(test), median_lap)

def mae_series(actual, predicted):
    return float(np.mean(np.abs(
        np.asarray(actual) - np.asarray(predicted)
    )))

def rmse_series(actual, predicted):
    return float(np.sqrt(np.mean(
        (np.asarray(actual) - np.asarray(predicted)) ** 2
    )))

def calculate_metrics(actual, predicted):
    if len(actual) == 0:
        return {"MAE": float("nan"), "RMSE": float("nan")}

    errors = np.asarray(actual) - np.asarray(predicted)

    return {
        "MAE": float(np.mean(np.abs(errors))),
        "RMSE": float(np.sqrt(np.mean(errors ** 2)))
    }

wet_mask = test["rainfall"].fillna(0) > 0

validation = {
    "base": {
        "all": calculate_metrics(test["lap_duration"], base_pred),
        "wet": calculate_metrics(
            test.loc[wet_mask, "lap_duration"],
            base_pred[wet_mask.to_numpy()],
        ),
        "dry": calculate_metrics(
            test.loc[~wet_mask, "lap_duration"],
            base_pred[(~wet_mask).to_numpy()],
        ),
    },
    "weather_aware": {
        "all": calculate_metrics(
            weather_test["lap_duration"], weather_pred
        ),
        "wet": calculate_metrics(
            weather_test.loc[
                weather_test["rainfall"] > 0, "lap_duration"
            ],
            weather_pred[
                (weather_test["rainfall"] > 0).to_numpy()
            ],
        ),
        "dry": calculate_metrics(
            weather_test.loc[
                weather_test["rainfall"] == 0, "lap_duration"
            ],
            weather_pred[
                (weather_test["rainfall"] == 0).to_numpy()
            ],
        ),
    },
    "baseline": {
        "all": calculate_metrics(
            test["lap_duration"], baseline_pred
        ),
        "wet": calculate_metrics(
            test.loc[wet_mask, "lap_duration"],
            baseline_pred[wet_mask.to_numpy()],
        ),
        "dry": calculate_metrics(
            test.loc[~wet_mask, "lap_duration"],
            baseline_pred[(~wet_mask).to_numpy()],
        ),
    },
}

# Check whether rainfall varies independently of lap number.
rainfall_by_lap = validation_df.groupby("lap_number")[
    "rainfall"
].nunique()

print(
    "Lap numbers with within-lap rainfall variation:",
    int((rainfall_by_lap > 1).sum())
)

# Check identifiability of rainfall when lap dummies are present (full model)
rank_df = validation_df[["lap_number", "rainfall"]].copy()

rank_df["lap_number"] = pd.to_numeric(
    rank_df["lap_number"], errors="coerce"
)
rank_df["rainfall"] = pd.to_numeric(
    rank_df["rainfall"], errors="coerce"
)

rank_df = rank_df.dropna()

full_X = pd.get_dummies(
    rank_df,
    columns=["lap_number"],
    drop_first=False,
    dtype=float,
)

full_rank = np.linalg.matrix_rank(
    full_X.to_numpy(dtype=float)
)

print("Weather identifiability matrix rank:", full_rank)
print("Weather identifiability matrix columns:", full_X.shape[1])

# ----------------------------------------------------------------------
# 7. Write report and lap‑by‑lap comparison CSV
# ----------------------------------------------------------------------
report_path = ROOT / "scratch" / "weather_validation_report.txt"
lap_csv_path = ROOT / "scratch" / "weather_validation_laps.csv"

with open(report_path, "w", encoding="utf-8") as f:
    f.write("=== PITWALL – Weather Validation Report ===\n\n")
    f.write("1. ACTUAL RACE TOTALS\n")
    f.write(f"   Piastri (81) – laps: {len(piastri_actual)}, total time: {piastri_total:.3f}s\n")
    f.write(f"   Hamilton (44) – laps: {len(hamilton_actual)}, total time: {hamilton_total:.3f}s\n\n")
    f.write("2. COUNTERFACTUAL SIMULATIONS (decision lap 26)\n")
    f.write(f"   Piastri simulated total: {piastri_summary.get('final_cumulative_time'):.3f}s\n")
    f.write(f"   Hamilton simulated total: {hamilton_summary.get('final_cumulative_time'):.3f}s\n\n")
    f.write("3. TIME DIFFERENCES\n")
    f.write(f"   Δ_actual (Piastri – Hamilton) = {piastri_total - hamilton_total:.3f}s\n")
    f.write(f"   Δ_counter (Piastri – Hamilton) = {piastri_summary.get('final_cumulative_time') - hamilton_summary.get('final_cumulative_time'):.3f}s\n")
    f.write(f"   Improvement vs. Piastri actual = {piastri_total - piastri_summary.get('final_cumulative_time'):.3f}s\n")
    f.write(f"   Improvement vs. Hamilton actual = {hamilton_total - piastri_summary.get('final_cumulative_time'):.3f}s\n\n")
    # Data‑quality warnings for incomplete stints / compound mapping issues
    if data_quality_warnings:
        f.write("   Data‑quality warnings:\n")
        for w in data_quality_warnings:
            f.write(f"     - {w}\n")
    else:
        f.write("   No data‑quality warnings.\n")
    f.write("\n")
    f.write("4. WEATHER‑LAP ALIGNMENT SUMMARY\n")
    missing = weather_aligned["missing_weather"].sum()
    max_lag = weather_aligned["weather_lag_seconds"].max()
    min_lag = weather_aligned["weather_lag_seconds"].min()
    f.write(f"   Missing weather rows: {missing}\n")
    f.write(f"   Lag seconds – min: {min_lag:.2f}, max: {max_lag:.2f}\n\n")
    f.write("5. FORWARD VALIDATION (train 1‑20 → test 21‑35)\n")
    f.write("   Model               | MAE_all | RMSE_all | MAE_wet | RMSE_wet | MAE_dry | RMSE_dry\n")
    f.write("   --------------------+---------+----------+---------+----------+----------+----------\n")
    for name, stats in validation.items():
      all_metrics = stats["all"]
      wet_metrics = stats["wet"]
      dry_metrics = stats["dry"]

    def fmt(metric, key):
        value = metric.get(key, float("nan"))
        return f"{value:.3f}" if np.isfinite(value) else "N/A"

    f.write(
        f"   {name:<20} | "
        f"{fmt(all_metrics, 'MAE'):>7} | "
        f"{fmt(all_metrics, 'RMSE'):>8} | "
        f"{fmt(wet_metrics, 'MAE'):>7} | "
        f"{fmt(wet_metrics, 'RMSE'):>8} | "
        f"{fmt(dry_metrics, 'MAE'):>7} | "
        f"{fmt(dry_metrics, 'RMSE'):>8}\n"
    )
    f.write("\n")
    f.write("6. RAINFALL IDENTIFIABILITY (full model with lap dummies)\n")
    f.write(f"   Design matrix rank (lap dummies + rainfall): {full_rank}\n")
    if full_rank < full_X.shape[1]:
        f.write("   WARNING: rainfall is collinear with lap‑number dummies; coefficient not uniquely identifiable.\n")
    else:
        f.write("   Rainfall is identifiable (full rank).\n")
    f.write("\n")
    f.write("7. SIGNATURES OF KEY CLASSES / FUNCTIONS\n")
    from inspect import signature
    f.write(f"   PaceModel.__init__: {signature(PaceModel.__init__)}\n")
    f.write(f"   PaceModel.fit:    {signature(PaceModel.fit)}\n")
    f.write(f"   PaceModel.predict_lap: {signature(PaceModel.predict_lap)}\n")
    f.write(f"   optimize_strategy: {signature(optimize_strategy)}\n")
    import pitwall.engine as engine_mod
    f.write(f"   engine.replay signature: {signature(engine_mod.replay)}\n")
    f.write("\n=== END OF REPORT ===\n")

# Identify linear dependencies in the design matrix.
_, singular_values, vh = np.linalg.svd(
    X_design.to_numpy(dtype=float),
    full_matrices=False
)

print("\n=== Rank-deficiency diagnosis ===")

for i, vector in enumerate(vh[-2:], start=1):
    print(f"\nDependency {i}:")

    contributions = sorted(
        zip(X_design.columns, vector),
        key=lambda item: abs(item[1]),
        reverse=True
    )

    for column, coefficient in contributions:
        if abs(coefficient) > 0.15:
            print(f"  {column}: {coefficient:.4f}")

# Lap‑by‑lap comparison CSV (actual vs. simulated for both drivers)

def build_comparison(actual_df, simulated_df, driver_name):
    cmp = actual_df.merge(
        simulated_df,
        on="lap_number",
        suffixes=("_actual", "_predicted"),
        how="outer",
        indicator=True,
    )
    cmp["driver"] = driver_name
    return cmp

piastri_cmp = build_comparison(piastri_actual, piastri_sim, "Piastri")
hamilton_cmp = build_comparison(hamilton_actual, hamilton_sim, "Hamilton")
all_cmp = pd.concat([piastri_cmp, hamilton_cmp], ignore_index=True)
all_cmp.to_csv(lap_csv_path, index=False)

print("\n=== WEATHER VALIDATION SCRIPT CREATED ===")
print(f"Report:   {report_path}")
print(f"Laps CSV: {lap_csv_path}")
print(f"Weather alignment CSV: {weather_alignment_path}\n")

