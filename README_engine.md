# PITWALL Replay Engine & Lap Fixed-Effects Pace Model

## Design Overview
PITWALL provides an interactive race-strategy counterfactual replay engine for Formula 1 races (Silverstone 2024, session 9558).

The engine replaces the flawed confounding pace table from notebook 08 with a mathematically sound **lap fixed-effects pace model** and an empirical **pit-loss measurement system**.

```
Session Data (race_state, laps, stints)
       │
       ▼
 [ pitwall.data ] ── Deduplicate, clean, detect in/out laps, filter SC/VSC & outliers
       │
       ├────────────────────────────────────────┐
       ▼                                        ▼
 [ pitwall.pace_model ]                 [ pitwall.pit_loss ]
 Lap Fixed Effects OLS                  Empirical Pit Loss
 Absorbs track evolution & wetness      In-lap + Out-lap delta
       │                                        │
       └───────────────────┬────────────────────┘
                           ▼
                 [ pitwall.engine ]
                 Counterfactual Replay
                 - Target simulated via pace model
                 - Rivals replay actual history
                           │
                           ▼
                [ pitwall.validation ]
                Acceptance Tests A, B, C, D
```

## Key Modules
- **`pitwall/data.py`**:
  - `load_race(session_key=9558)`: Loads session data, deduplicates lap records, computes cumulative times, flags pit in-laps and pit out-laps, filters SC/VSC laps (field median >= 1.25x rolling field median), flags gross outliers (> 1.3x field median), and generates boolean mask `is_clean_lap`.
  - `get_finishers(df)`: Detects drivers who completed the full race distance (52 laps).
  - `get_driver_laps(df, driver_number)`: Returns driver-specific laps table.

- **`pitwall/pace_model.py`**:
  - Fits OLS with cluster-robust standard errors grouped by driver:
    $$\text{lap\_duration} \sim C(\text{lap\_number}) + C(\text{driver\_number}) + C(\text{compound}) + C(\text{compound}):\text{tyre\_age}$$
  - Reference compound: `MEDIUM`.
  - Absorbs all field-wide temporal effects (weather, track wetness, drying line, fuel burn) into $C(\text{lap\_number})$.
  - Identifies compound delta strictly from multi-compound overlapping laps.
  - Supports `replay` mode (using known future field track evolution) and experimental `causal` mode (persisting decision lap state).

- **`pitwall/pit_loss.py`**:
  - Measures empirical pit loss from real stops:
    $$\text{pit\_loss} = (t_{\text{in}} + t_{\text{out}}) - (\hat{t}_{\text{clean, in}} + \hat{t}_{\text{clean, out}})$$
  - Returns median, IQR, mean, and std for green-flag stops.

- **`pitwall/engine.py`**:
  - `replay(session_df, target_driver, decision_lap, action, pace_model, pit_loss, track_mode)`:
    - Simulates the target driver forward under `Stay()` or `Pit(lap, compound)`.
    - Rivals replay their actual recorded historical lap times.
    - Accurately tracks cumulative time and lap-by-lap classification.
    - Detects non-finishers (e.g. driver 63 Russell, who retired on lap 34), marks `ground_truth_available=False`, and refuses to claim ungrounded final positions.

- **`pitwall/validation.py`**:
  - Suite of 4 formal acceptance tests:
    - **Test A (Plumbing)**: Passthrough reproduces actual classification and times exactly.
    - **Test B (Identity)**: Simulating real pit action from prior decision laps against historical ground truth.
    - **Test C (Sanity-Bound)**: Pit lap shift of $\pm 1..3$ laps changes outcome by $< 15$ s; no candidate $> 45$ s divergence.
    - **Test D (Support)**: Refuses counterfactual compound if overlapping clean laps $< 8$.

## Assumptions & Known Limitations
1. **Rivals do not react**: Rivals replay their historical lap times and pit stops regardless of target driver actions.
2. **Replay track-state mode**: Replay mode uses field lap fixed effects from actual history (track evolution as it really happened).
3. **No dirty air / overtaking model**: Position is determined strictly by cumulative elapsed time ranking.
4. **No safety car simulation**: Future safety cars / red flags are not stochastically generated.
5. **Single-stop simulation in Test B**: In races with 2 stops (e.g. Silverstone dry $\to$ wet $\to$ dry), simulating a single `Pit(lap=27, INTERMEDIATE)` action projects that the driver remains on that compound until lap 52 unless a subsequent stop is scheduled. This explains why Test B error over the full 52 laps is higher (~37 s) when evaluating early stops without modeling the second dry transition.

## Running Tests
Run pytest from the repository root:
```bash
pytest -q
```
