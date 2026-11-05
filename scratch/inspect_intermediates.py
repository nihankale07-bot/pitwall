from pitwall.data import load_race
import pandas as pd
import numpy as np
import statsmodels.formula.api as smf

df = load_race(9558)
print("Loaded session 9558, total rows:", len(df))
print("Columns:", df.columns.tolist())
print("Compounds present in session 9558:", df["compound"].value_counts().to_dict())

inter_df = df[df["compound"] == "INTERMEDIATE"].copy()
print(f"Total intermediate rows: {len(inter_df)}")
print(f"Clean intermediate rows: {len(inter_df[inter_df['is_clean_lap']])}")
print(f"Drivers running intermediate: {inter_df['driver_number'].unique().tolist()}")
print(f"Lap numbers range on intermediate: {inter_df['lap_number'].min()} to {inter_df['lap_number'].max()}")

# Inspect clean laps by compound
print("\nClean laps by compound:")
print(df[df["is_clean_lap"]]["compound"].value_counts().to_dict())

# Let's inspect the fitted pace model on session 9558
from pitwall.pace_model import PaceModel
pm = PaceModel(reference_compound="MEDIUM").fit(df)
print("\nPaceModel fitted coefficients for compounds and age slopes:")
print("compound_effects:", pm.compound_effects)
print("compound_age_slopes:", pm.compound_age_slopes)
print("rsquared:", pm.rsquared)

# Now check intermediate tyre age slope when fitting PaceModel on clean laps
# Let's also check if decision_lap=26 has any clean intermediate laps
clean_d26 = df[(df["lap_number"] <= 26) & (df["is_clean_lap"])]
print("\nClean laps up to lap 26 by compound:")
print(clean_d26["compound"].value_counts().to_dict())

# Check intermediate stints details across drivers
print("\nIntermediate stint length and tyre_age stats:")
for d, grp in inter_df.groupby("driver_number"):
    print(f"Driver {d}: laps {grp['lap_number'].min()}-{grp['lap_number'].max()}, tyre_age {grp['tyre_age'].min()}-{grp['tyre_age'].max()}, clean laps: {grp['is_clean_lap'].sum()}")

# Regression of lap_duration on intermediate:
clean_inter = df[(df["compound"] == "INTERMEDIATE") & (df["is_clean_lap"])].copy()
if len(clean_inter) > 10:
    # Model with lap fixed effects and driver fixed effects
    res_with_lap = smf.ols("lap_duration ~ C(lap_number) + C(driver_number) + tyre_age", data=clean_inter).fit()
    print("\nRegression with lap and driver fixed effects on clean INTERMEDIATE laps:")
    print(f"tyre_age slope: {res_with_lap.params.get('tyre_age'):.4f}, p-val: {res_with_lap.pvalues.get('tyre_age'):.4e}")

    # Model without lap fixed effect (raw tyre age degradation across stint)
    res_raw = smf.ols("lap_duration ~ C(driver_number) + tyre_age", data=clean_inter).fit()
    print("\nRegression with driver fixed effects only (raw stint degradation) on clean INTERMEDIATE laps:")
    print(f"tyre_age slope: {res_raw.params.get('tyre_age'):.4f}, p-val: {res_raw.pvalues.get('tyre_age'):.4e}")
