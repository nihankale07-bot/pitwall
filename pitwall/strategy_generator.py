"""Procedural multi-stop strategy candidate generation."""

from typing import Dict, List, Optional, Set, Tuple, Union
import numpy as np
import pandas as pd


def generate_multi_stop_candidates(
    race_df: pd.DataFrame,
    target_driver: int,
    decision_lap: int,
    race_length: int = 52,
    pit_window: int = 5,
    pit_intervals: tuple = (1, 2, 3, 4, 5),
    max_stops: int = 2,
    supported_compounds: Optional[Set[str]] = None,
) -> pd.DataFrame:
    """Generate multi-stop strategy candidates as a table.
    
    Output table columns:
    - strategy_id: "S001", "S002", ...
    - pit_sequence: tuple of (lap, compound) tuples, e.g. ((27, 'INTERMEDIATE'), (38, 'SOFT'))
    - pit_sequence_str: human-readable, e.g. "INTER lap 27 -> SOFT lap 38"
    - is_baseline: True if this is the real historical sequence for this driver
    - baseline_distance: Manhattan/lag distance from real sequence (0 for baseline)
    - current_compound: driver's compound at decision_lap
    - num_stops: 1 or 2
    - description: human-readable narrative
    
    Design assumptions & heuristics:
    - Weather heuristic for two-stop: If currently wet at decision lap, first stop prefers WET compounds
      (INTERMEDIATE), and second stop assumes drying by lap 38-40 preferring DRY compounds (SOFT, MEDIUM, HARD).
      [EXPERIMENTAL]: This assumption reflects typical wet-to-dry transitions.
    - Aggressive filtering keeps candidate count < 100 while guaranteeing the real baseline is included.
    """
    if supported_compounds is None:
        supported_compounds = {"SOFT", "MEDIUM", "HARD", "INTERMEDIATE"}

    target_laps = race_df[race_df["driver_number"] == target_driver].sort_values("lap_number")
    curr_row = target_laps[target_laps["lap_number"] == decision_lap].iloc[0]
    curr_compound = curr_row["compound"]
    curr_rainfall = curr_row.get("rainfall", 0)
    is_currently_wet = (curr_rainfall > 0) or (curr_compound == "INTERMEDIATE")

    # Extract target driver's real future pit sequence after decision_lap
    real_pits = target_laps[target_laps["is_pit_in_lap"] & (target_laps["lap_number"] > decision_lap)]
    real_sequence: List[Tuple[int, str]] = []
    for _, r in real_pits.iterrows():
        p_lap = int(r["lap_number"])
        next_lap_rows = target_laps[target_laps["lap_number"] == p_lap + 1]
        next_comp = next_lap_rows["compound"].iloc[0] if len(next_lap_rows) > 0 else "UNKNOWN"
        real_sequence.append((p_lap, next_comp))

    real_seq_tuple = tuple(real_sequence)

    candidates: List[Dict] = []
    seen_sequences = set()

    # Define compound priority
    dry_compounds = [c for c in ["SOFT", "MEDIUM", "HARD"] if c in supported_compounds]
    wet_compounds = [c for c in ["INTERMEDIATE"] if c in supported_compounds]

    # Helper to add candidate
    def add_candidate(seq: Tuple[Tuple[int, str], ...], desc_suffix: str = ""):
        if seq in seen_sequences:
            return
        seen_sequences.add(seq)
        
        # Calculate baseline distance
        # Manhattan distance in pit laps + compound mismatch penalty
        is_base = (seq == real_seq_tuple)
        dist = 0
        if is_base:
            dist = 0
        elif len(real_seq_tuple) == 0:
            dist = 50 + len(seq) * 10
        else:
            # Compare stops
            min_len = min(len(seq), len(real_seq_tuple))
            for i in range(min_len):
                dist += abs(seq[i][0] - real_seq_tuple[i][0])
                if seq[i][1] != real_seq_tuple[i][1]:
                    dist += 15  # compound mismatch penalty
            dist += abs(len(seq) - len(real_seq_tuple)) * 30

        # String representation
        parts = [f"{comp} lap {lap}" for (lap, comp) in seq]
        seq_str = " -> ".join(parts) if parts else "Stay out"
        
        candidates.append({
            "pit_sequence": seq,
            "pit_sequence_str": seq_str,
            "is_baseline": is_base,
            "baseline_distance": dist,
            "current_compound": curr_compound,
            "num_stops": len(seq),
            "description": f"{seq_str} {desc_suffix}".strip(),
        })

    # Always ensure the real sequence is included
    if len(real_seq_tuple) > 0:
        add_candidate(real_seq_tuple, "(baseline, distance=0)")

    # A. Single-pit candidates (k=1)
    p1_min = decision_lap + 1
    p1_max = min(decision_lap + pit_window + 5, race_length - 1)
    
    p1_candidates = sorted(list(set(range(p1_min, min(p1_max + 1, race_length)))))
    if len(real_seq_tuple) > 0:
        for (real_p, _) in real_seq_tuple:
            for offset in range(-2, 3):
                lp = real_p + offset
                if decision_lap < lp < race_length:
                    p1_candidates.append(lp)
    p1_candidates = sorted(list(set(p1_candidates)))

    if curr_compound == "INTERMEDIATE":
        # On intermediates, car can either change to fresh inters or transition back to dry slicks
        c1_pool = dry_compounds + wet_compounds
    elif is_currently_wet:
        c1_pool = wet_compounds
    else:
        c1_pool = dry_compounds + wet_compounds

    c1_pool = [c for c in c1_pool if c != curr_compound]

    for p1 in p1_candidates:
        for c1 in c1_pool:
            add_candidate(((p1, c1),), "")

    # B. Two-pit candidates (k=2, if max_stops >= 2)
    if max_stops >= 2:
        # Determine plausible second pit laps
        # In this race, dry transition happens laps 37-40
        for p1 in p1_candidates:
            for c1 in c1_pool:
                # Plausible p2: at least 3 laps after p1
                p2_candidates = []
                # Around lap 38-40 if wet-to-dry
                if c1 == "INTERMEDIATE":
                    for p2 in [37, 38, 39, 40]:
                        if p2 >= p1 + 3 and p2 < race_length:
                            p2_candidates.append(p2)
                else:
                    for p2_off in [10, 15, 20]:
                        p2 = p1 + p2_off
                        if p2 < race_length:
                            p2_candidates.append(p2)

                # Also if real sequence has a second stop, include shifts around real_p2
                if len(real_seq_tuple) >= 2:
                    real_p2 = real_seq_tuple[1][0]
                    for offset in [-1, 0, 1]:
                        p2 = real_p2 + offset
                        if p2 >= p1 + 3 and p2 < race_length:
                            p2_candidates.append(p2)

                p2_candidates = sorted(list(set(p2_candidates)))

                # Second compound pool
                c2_pool = dry_compounds if c1 == "INTERMEDIATE" else (dry_compounds + wet_compounds)
                c2_pool = [c for c in c2_pool if c != c1]

                for p2 in p2_candidates:
                    for c2 in c2_pool:
                        add_candidate(((p1, c1), (p2, c2)), "")

    # Convert to DataFrame
    df_cands = pd.DataFrame(candidates)
    
    # Sort by baseline_distance ascending
    df_cands = df_cands.sort_values(["baseline_distance", "num_stops"]).reset_index(drop=True)
    
    # Assign strategy_id
    df_cands["strategy_id"] = [f"S{i+1:03d}" for i in range(len(df_cands))]

    # Cap to top 99 if needed (ensuring baseline is always retained)
    if len(df_cands) > 95:
        # Keep top 90 plus baseline
        is_base = df_cands["is_baseline"]
        top_candidates = df_cands.iloc[:90]
        if not is_base.iloc[:90].any():
            base_row = df_cands[is_base]
            top_candidates = pd.concat([top_candidates, base_row])
        df_cands = top_candidates.reset_index(drop=True)
        df_cands["strategy_id"] = [f"S{i+1:03d}" for i in range(len(df_cands))]

    return df_cands
