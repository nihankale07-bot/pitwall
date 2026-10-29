"""Lap fixed-effects pace model."""

from dataclasses import dataclass, field
from itertools import combinations
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf


@dataclass
class IdentificationReport:
    n_clean_laps: int
    n_multi_compound_laps: int
    pair_counts: Dict[str, int]
    weakly_identified_pairs: List[str]


@dataclass
class CoefficientSummary:
    param_name: str
    coef: float
    ci_lower: float
    ci_upper: float
    pvalue: float


class PaceModel:
    """Lap fixed-effects pace model.
    
    Model formula:
        lap_duration ~ C(lap_number) + C(driver_number) + C(compound) + C(compound):tyre_age
    
    Absorption:
    The lap_number fixed effect absorbs all lap-common track evolution (weather, track wetness,
    drying line, track temperature, fuel burn), allowing the compound effect to be identified
    solely from laps where different compounds ran side-by-side.
    """

    def __init__(self, reference_compound: str = "MEDIUM"):
        self.reference_compound = reference_compound
        self.fitted = False
        self.intercept: float = 0.0
        self.lap_effects: Dict[int, float] = {}
        self.driver_effects: Dict[int, float] = {}
        self.compound_effects: Dict[str, float] = {}
        self.compound_age_slopes: Dict[str, float] = {}
        self.coefficients: List[CoefficientSummary] = []
        self.identification_report: Optional[IdentificationReport] = None
        self.rsquared: float = 0.0
        self.base_driver: int = 1
        self.base_lap: int = 2

    def fit(self, df: pd.DataFrame) -> "PaceModel":
        """Fit the model on clean laps only."""
        clean_df = df[df["is_clean_lap"]].copy()

        # Categorical ordering with reference compound first
        categories = [self.reference_compound] + [
            c for c in ["HARD", "INTERMEDIATE", "MEDIUM", "SOFT"] if c != self.reference_compound
        ]
        clean_df["compound"] = pd.Categorical(clean_df["compound"], categories=categories)

        # Identification report
        compounds = ["MEDIUM", "HARD", "INTERMEDIATE", "SOFT"]
        pairs = list(combinations(compounds, 2))
        pair_counts = {}
        weak_pairs = []

        for p in pairs:
            p_name = f"{p[0]} vs {p[1]}"
            cnt = 0
            for _, grp in clean_df.groupby("lap_number"):
                pres = set(grp["compound"].unique())
                if p[0] in pres and p[1] in pres:
                    cnt += 1
            pair_counts[p_name] = cnt
            if cnt < 15:
                weak_pairs.append(p_name)

        multi_laps = int((clean_df.groupby("lap_number")["compound"].nunique() >= 2).sum())
        self.identification_report = IdentificationReport(
            n_clean_laps=len(clean_df),
            n_multi_compound_laps=multi_laps,
            pair_counts=pair_counts,
            weakly_identified_pairs=weak_pairs,
        )

        formula = "lap_duration ~ C(lap_number) + C(driver_number) + C(compound) + C(compound):tyre_age"
        mod = smf.ols(formula, data=clean_df)
        res = mod.fit(cov_type="cluster", cov_kwds={"groups": clean_df["driver_number"]})

        self.rsquared = float(res.rsquared)
        params = res.params
        conf = res.conf_int()
        pvals = res.pvalues

        # Store coefficient summary
        self.coefficients = []
        for p_name, val in params.items():
            ci = conf.loc[p_name]
            self.coefficients.append(
                CoefficientSummary(
                    param_name=p_name,
                    coef=float(val),
                    ci_lower=float(ci[0]),
                    ci_upper=float(ci[1]),
                    pvalue=float(pvals[p_name]),
                )
            )

        self.intercept = float(params.get("Intercept", 0.0))

        # Base driver and lap
        self.base_lap = int(clean_df["lap_number"].min())
        self.base_driver = int(clean_df["driver_number"].min())

        # Lap effects
        self.lap_effects = {self.base_lap: 0.0}
        for k, v in params.items():
            if k.startswith("C(lap_number)[T."):
                lap_num = int(k.replace("C(lap_number)[T.", "").replace("]", ""))
                self.lap_effects[lap_num] = float(v)

        # Lap 1 fallback
        if 1 not in self.lap_effects:
            self.lap_effects[1] = self.lap_effects.get(self.base_lap, 0.0)

        # Driver effects
        self.driver_effects = {self.base_driver: 0.0}
        for k, v in params.items():
            if k.startswith("C(driver_number)[T."):
                d_num = int(k.replace("C(driver_number)[T.", "").replace("]", ""))
                self.driver_effects[d_num] = float(v)

        # Compound effects
        self.compound_effects = {self.reference_compound: 0.0}
        for k, v in params.items():
            if k.startswith("C(compound)[T."):
                comp = k.replace("C(compound)[T.", "").replace("]", "")
                self.compound_effects[comp] = float(v)

        # Compound age slopes
        self.compound_age_slopes = {}
        for k, v in params.items():
            if ":tyre_age" in k:
                comp = k.replace("C(compound)[", "").replace("]:tyre_age", "")
                self.compound_age_slopes[comp] = float(v)

        self.fitted = True
        return self

    def predict_lap(
        self,
        lap_number: int,
        driver_number: int,
        compound: str,
        tyre_age: int,
        mode: str = "replay",
        decision_lap: Optional[int] = None,
    ) -> float:
        """Predict expected clean lap time for a driver on a lap.
        
        Modes:
        - 'replay' (default): Uses the actual field lap effect for lap_number (known future track state).
        - 'causal' (experimental): Persists the lap effect from decision_lap.
        """
        if not self.fitted:
            raise ValueError("Model must be fitted before predicting.")

        if mode == "replay":
            lap_eff = self.lap_effects.get(lap_number, self.lap_effects.get(self.base_lap, 0.0))
        elif mode == "causal":
            # Experimental causal stub: persist decision lap effect
            if decision_lap is not None and decision_lap in self.lap_effects:
                lap_eff = self.lap_effects[decision_lap]
            else:
                lap_eff = self.lap_effects.get(self.base_lap, 0.0)
        else:
            raise ValueError(f"Unknown mode: {mode}")

        driver_eff = self.driver_effects.get(driver_number, 0.0)
        compound_eff = self.compound_effects.get(compound, 0.0)
        age_slope = self.compound_age_slopes.get(compound, 0.0)

        predicted_time = self.intercept + lap_eff + driver_eff + compound_eff + (age_slope * tyre_age)
        return float(predicted_time)


def fit_pace_model(df: pd.DataFrame, reference_compound: str = "MEDIUM") -> PaceModel:
    """Convenience function to fit a PaceModel on session data."""
    return PaceModel(reference_compound=reference_compound).fit(df)

