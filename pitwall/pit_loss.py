"""Pit loss measurement from historical pit events."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd


@dataclass
class PitLossSummary:
    median: float
    iqr_low: float
    iqr_high: float
    iqr: float
    mean: float
    std: float
    n_stops: int
    stops_table: pd.DataFrame


def measure_pit_loss(
    session_df: pd.DataFrame,
    pace_model,
) -> Tuple[PitLossSummary, PitLossSummary]:
    """Measure pit loss from actual pit stops in the session.
    
    pit_loss = (in_lap_time + out_lap_time) - (expected clean in_lap_time + expected clean out_lap_time)
    where expected clean lap time comes from the lap fixed-effects pace model.
    
    Returns:
    (green_flag_summary, sc_vsc_summary)
    """
    df = session_df.copy()
    out_laps = df[df["is_pit_out_lap"]].copy()
    
    stops = []
    for _, out_row in out_laps.iterrows():
        d = int(out_row["driver_number"])
        out_lap = int(out_row["lap_number"])
        in_lap = out_lap - 1
        
        in_rows = df[(df["driver_number"] == d) & (df["lap_number"] == in_lap)]
        if len(in_rows) == 0:
            continue
        in_row = in_rows.iloc[0]
        
        in_time = in_row["lap_duration"]
        out_time = out_row["lap_duration"]
        
        if pd.isna(in_time) or pd.isna(out_time):
            continue
            
        in_age = int(in_row["tyre_age"]) if pd.notna(in_row["tyre_age"]) else 0
        out_age = int(out_row["tyre_age"]) if pd.notna(out_row["tyre_age"]) else 0

        exp_in = pace_model.predict_lap(
            lap_number=in_lap,
            driver_number=d,
            compound=in_row["compound"],
            tyre_age=in_age,
        )
        exp_out = pace_model.predict_lap(
            lap_number=out_lap,
            driver_number=d,
            compound=out_row["compound"],
            tyre_age=out_age,
        )
        
        loss = (in_time + out_time) - (exp_in + exp_out)
        is_sc = bool(in_row.get("is_sc_vsc_lap", False) or out_row.get("is_sc_vsc_lap", False))
        
        stops.append({
            "driver_number": d,
            "in_lap": in_lap,
            "out_lap": out_lap,
            "in_time": float(in_time),
            "out_time": float(out_time),
            "exp_in": float(exp_in),
            "exp_out": float(exp_out),
            "pit_loss": float(loss),
            "is_sc_vsc": is_sc,
            "compound_before": in_row["compound"],
            "compound_after": out_row["compound"],
        })
        
    stops_df = pd.DataFrame(stops)
    
    def summarize(sub_df: pd.DataFrame) -> PitLossSummary:
        if len(sub_df) == 0:
            return PitLossSummary(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, sub_df)
        losses = sub_df["pit_loss"]
        q25 = float(losses.quantile(0.25))
        q50 = float(losses.median())
        q75 = float(losses.quantile(0.75))
        return PitLossSummary(
            median=q50,
            iqr_low=q25,
            iqr_high=q75,
            iqr=q75 - q25,
            mean=float(losses.mean()),
            std=float(losses.std()),
            n_stops=len(sub_df),
            stops_table=sub_df,
        )
        
    green_summary = summarize(stops_df[~stops_df["is_sc_vsc"]])
    sc_summary = summarize(stops_df[stops_df["is_sc_vsc"]])
    
    return green_summary, sc_summary
