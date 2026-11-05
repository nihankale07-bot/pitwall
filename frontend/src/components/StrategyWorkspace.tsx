import React, { useState } from 'react';
import {
  Play,
  RotateCcw,
  Sliders,
  AlertTriangle,
  Info,
  Clock,
  Layers,
  Gauge,
  Sparkles,
} from 'lucide-react';
import { OptimizeRequest, OptimizationResponse } from '../types';
import { getDriverMeta, getSessionMeta } from '../constants';

interface StrategyWorkspaceProps {
  sessionKey: number;
  targetDriver: number;
  onRunOptimization: (params: OptimizeRequest) => Promise<void>;
  loading: boolean;
  result: OptimizationResponse | null;
  error: string | null;
  onViewResults: () => void;
}

export const StrategyWorkspace: React.FC<StrategyWorkspaceProps> = ({
  sessionKey,
  targetDriver,
  onRunOptimization,
  loading,
  result,
  error,
  onViewResults,
}) => {
  const sessionMeta = getSessionMeta(sessionKey);
  const driverMeta = getDriverMeta(targetDriver);

  // Optimizer control parameters with sensible defaults consistent with backend
  const [decisionLap, setDecisionLap] = useState<number>(26);
  const [raceLength, setRaceLength] = useState<number>(sessionMeta.defaultRaceLength || 52);
  const [trackMode, setTrackMode] = useState<'causal' | 'replay'>('causal');
  const [pitLoss, setPitLoss] = useState<number>(22.0);
  const [maxStops, setMaxStops] = useState<number>(2);
  const [maxCandidates, setMaxCandidates] = useState<number>(95);

  const [validationError, setValidationError] = useState<string | null>(null);

  const handleRun = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    // Frontend validations before dispatching to backend
    if (raceLength <= 1) {
      setValidationError('Race length must be greater than 1 lap.');
      return;
    }
    if (decisionLap < 1 || decisionLap >= raceLength) {
      setValidationError(`Decision lap must be between 1 and ${raceLength - 1}.`);
      return;
    }
    if (pitLoss < 0) {
      setValidationError('Pit loss cannot be negative.');
      return;
    }
    if (maxStops < 0 || maxStops > 4) {
      setValidationError('Maximum stops should be between 0 and 4.');
      return;
    }
    if (maxCandidates < 1) {
      setValidationError('Maximum strategy candidates must be at least 1.');
      return;
    }

    const payload: OptimizeRequest = {
      session_key: sessionKey,
      target_driver: targetDriver,
      decision_lap: Number(decisionLap),
      race_length: Number(raceLength),
      track_mode: trackMode,
      pit_loss: Number(pitLoss),
      max_stops: Number(maxStops),
      max_candidates: Number(maxCandidates),
    };

    await onRunOptimization(payload);
  };

  const resetDefaults = () => {
    setDecisionLap(26);
    setRaceLength(52);
    setTrackMode('causal');
    setPitLoss(22.0);
    setMaxStops(2);
    setMaxCandidates(95);
    setValidationError(null);
  };

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '1.5rem 2rem' }}>
      {/* Workspace Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: '1.5rem',
        borderBottom: '1px solid var(--border-subtle)',
        paddingBottom: '1rem',
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="font-mono" style={{ fontSize: '0.75rem', color: 'var(--accent-red)', textTransform: 'uppercase' }}>
              PITWALL OPTIMIZER MODULE
            </span>
            <span style={{ color: 'var(--border-strong)' }}>•</span>
            <span className="font-mono" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              ENDPOINT: POST /optimize
            </span>
          </div>
          <h1 className="font-display" style={{ fontSize: '1.8rem', fontWeight: 700, marginTop: '4px' }}>
            STRATEGY OPTIMISATION ENGINE
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Simulate tyre degradation slopes, pit-stop windows, and projected finishing orders under causal or replay scenarios.
          </p>
        </div>

        {/* Selected Driver Banner */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          padding: '8px 16px',
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-subtle)',
          borderLeft: `4px solid ${driverMeta.teamColor}`,
          borderRadius: '4px',
        }}>
          <div>
            <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Optimizing For
            </div>
            <div style={{ fontWeight: 700, fontSize: '1rem' }}>
              {driverMeta.name} (#{driverMeta.number})
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
              {driverMeta.team} • {sessionMeta.name}
            </div>
          </div>
        </div>
      </div>

      {/* Main Grid: Controls on Left, Model Info & Live Output on Right */}
      <div style={{ display: 'grid', gridTemplateColumns: '460px 1fr', gap: '1.75rem' }}>
        {/* Controls Card */}
        <div style={{
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '6px',
          padding: '1.5rem',
          position: 'relative',
        }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '1.25rem',
            paddingBottom: '0.75rem',
            borderBottom: '1px solid var(--border-subtle)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Sliders size={18} color="var(--accent-red)" />
              <span className="font-display" style={{ fontWeight: 700, fontSize: '1.05rem' }}>
                OPTIMIZATION PARAMETERS
              </span>
            </div>
            <button
              onClick={resetDefaults}
              title="Reset parameters to calibrated defaults"
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                fontSize: '0.72rem',
                fontFamily: 'var(--font-mono)',
              }}
            >
              <RotateCcw size={12} /> DEFAULTS
            </button>
          </div>

          {(validationError || error) && (
            <div style={{
              padding: '10px 14px',
              backgroundColor: 'rgba(225, 6, 0, 0.15)',
              border: '1px solid rgba(225, 6, 0, 0.4)',
              borderRadius: '4px',
              marginBottom: '1.25rem',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              fontSize: '0.8rem',
              color: '#FF7B76',
            }}>
              <AlertTriangle size={16} color="#E10600" />
              <span>{validationError || error}</span>
            </div>
          )}

          <form onSubmit={handleRun}>
            {/* Simulation Mode Toggle */}
            <div style={{ marginBottom: '1.25rem' }}>
              <label style={{
                display: 'flex',
                justifyContent: 'space-between',
                fontSize: '0.75rem',
                fontFamily: 'var(--font-mono)',
                color: 'var(--text-secondary)',
                marginBottom: '6px',
              }}>
                <span>TRACK MODE (SIMULATION)</span>
                <span style={{ color: 'var(--text-muted)' }}>backend: track_mode</span>
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                <button
                  type="button"
                  onClick={() => setTrackMode('causal')}
                  style={{
                    padding: '9px 12px',
                    backgroundColor: trackMode === 'causal' ? 'var(--accent-red-dim)' : 'var(--bg-secondary)',
                    border: '1px solid',
                    borderColor: trackMode === 'causal' ? 'var(--accent-red)' : 'var(--border-subtle)',
                    borderRadius: '4px',
                    color: trackMode === 'causal' ? '#FFFFFF' : 'var(--text-secondary)',
                    fontWeight: 600,
                    fontSize: '0.85rem',
                    cursor: 'pointer',
                    textAlign: 'left',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{
                      width: '6px',
                      height: '6px',
                      borderRadius: '50%',
                      backgroundColor: trackMode === 'causal' ? 'var(--accent-red)' : 'var(--text-muted)',
                    }} />
                    <span>Causal Mode</span>
                  </div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                    Train only up to decision lap
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => setTrackMode('replay')}
                  style={{
                    padding: '9px 12px',
                    backgroundColor: trackMode === 'replay' ? 'var(--accent-red-dim)' : 'var(--bg-secondary)',
                    border: '1px solid',
                    borderColor: trackMode === 'replay' ? 'var(--accent-red)' : 'var(--border-subtle)',
                    borderRadius: '4px',
                    color: trackMode === 'replay' ? '#FFFFFF' : 'var(--text-secondary)',
                    fontWeight: 600,
                    fontSize: '0.85rem',
                    cursor: 'pointer',
                    textAlign: 'left',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{
                      width: '6px',
                      height: '6px',
                      borderRadius: '50%',
                      backgroundColor: trackMode === 'replay' ? 'var(--accent-red)' : 'var(--text-muted)',
                    }} />
                    <span>Replay Mode</span>
                  </div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                    Full session pace reference
                  </div>
                </button>
              </div>
            </div>

            {/* Decision Lap & Race Length */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.25rem' }}>
              <div>
                <label style={{
                  display: 'block',
                  fontSize: '0.75rem',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--text-secondary)',
                  marginBottom: '6px',
                }}>
                  DECISION LAP (Current: {decisionLap})
                </label>
                <input
                  type="number"
                  min={1}
                  max={raceLength - 1}
                  value={decisionLap}
                  onChange={(e) => setDecisionLap(parseInt(e.target.value) || 1)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    backgroundColor: 'var(--bg-secondary)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '4px',
                    color: '#FFFFFF',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.9rem',
                  }}
                />
                <input
                  type="range"
                  min={1}
                  max={raceLength - 1}
                  value={decisionLap}
                  onChange={(e) => setDecisionLap(parseInt(e.target.value) || 1)}
                  style={{ width: '100%', marginTop: '6px', accentColor: 'var(--accent-red)' }}
                />
              </div>

              <div>
                <label style={{
                  display: 'block',
                  fontSize: '0.75rem',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--text-secondary)',
                  marginBottom: '6px',
                }}>
                  RACE LENGTH (LAPS)
                </label>
                <input
                  type="number"
                  min={2}
                  max={100}
                  value={raceLength}
                  onChange={(e) => setRaceLength(parseInt(e.target.value) || 52)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    backgroundColor: 'var(--bg-secondary)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '4px',
                    color: '#FFFFFF',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.9rem',
                  }}
                />
                <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '4px', fontFamily: 'var(--font-mono)' }}>
                  Silverstone reference: 52
                </div>
              </div>
            </div>

            {/* Pit Loss & Max Stops */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.25rem' }}>
              <div>
                <label style={{
                  display: 'block',
                  fontSize: '0.75rem',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--text-secondary)',
                  marginBottom: '6px',
                }}>
                  PIT LOSS DELTA (s)
                </label>
                <input
                  type="number"
                  step="0.5"
                  min={10}
                  max={50}
                  value={pitLoss}
                  onChange={(e) => setPitLoss(parseFloat(e.target.value) || 22.0)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    backgroundColor: 'var(--bg-secondary)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '4px',
                    color: '#FFFFFF',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.9rem',
                  }}
                />
                <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '4px', fontFamily: 'var(--font-mono)' }}>
                  Pit lane transit time (22.0s)
                </div>
              </div>

              <div>
                <label style={{
                  display: 'block',
                  fontSize: '0.75rem',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--text-secondary)',
                  marginBottom: '6px',
                }}>
                  MAXIMUM PIT STOPS
                </label>
                <select
                  value={maxStops}
                  onChange={(e) => setMaxStops(parseInt(e.target.value))}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    backgroundColor: 'var(--bg-secondary)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '4px',
                    color: '#FFFFFF',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.9rem',
                  }}
                >
                  <option value={1}>1 Stop (Conservative)</option>
                  <option value={2}>2 Stops (Standard)</option>
                  <option value={3}>3 Stops (Aggressive)</option>
                </select>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '4px', fontFamily: 'var(--font-mono)' }}>
                  Limits combinatorial trees
                </div>
              </div>
            </div>

            {/* Max Candidates */}
            <div style={{ marginBottom: '1.75rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <label style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                  MAX STRATEGY CANDIDATES
                </label>
                <span className="font-mono" style={{ fontSize: '0.75rem', color: 'var(--accent-red)' }}>
                  {maxCandidates} candidate plans
                </span>
              </div>
              <input
                type="range"
                min={10}
                max={150}
                step={5}
                value={maxCandidates}
                onChange={(e) => setMaxCandidates(parseInt(e.target.value))}
                style={{ width: '100%', accentColor: 'var(--accent-red)' }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                <span>Fast search (10)</span>
                <span>Production default (95)</span>
                <span>Exhaustive (150)</span>
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              style={{
                width: '100%',
                padding: '14px',
                backgroundColor: loading ? 'var(--bg-surface)' : 'var(--accent-red)',
                color: loading ? 'var(--text-muted)' : '#FFFFFF',
                border: 'none',
                borderRadius: '4px',
                fontFamily: 'var(--font-display)',
                fontWeight: 700,
                fontSize: '1.05rem',
                letterSpacing: '0.08em',
                cursor: loading ? 'wait' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                boxShadow: loading ? 'none' : '0 0 20px rgba(225, 6, 0, 0.4)',
                transition: 'all 0.2s ease',
              }}
            >
              {loading ? (
                <>
                  <div className="spin" style={{
                    width: '18px',
                    height: '18px',
                    border: '2px solid rgba(255,255,255,0.2)',
                    borderTopColor: '#FFFFFF',
                    borderRadius: '50%',
                  }} />
                  <span>SIMULATING CANDIDATE TREES...</span>
                </>
              ) : (
                <>
                  <Play size={18} fill="#FFFFFF" />
                  <span>RUN STRATEGY OPTIMISATION</span>
                </>
              )}
            </button>
          </form>
        </div>

        {/* Right Column: Model Specs & Latest Results Preview */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {/* Calibrated Model Specs Box */}
          <div style={{
            backgroundColor: 'var(--bg-secondary)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '6px',
            padding: '1.25rem',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Gauge size={18} color="#10B981" />
                <span className="font-display" style={{ fontWeight: 700, fontSize: '1rem' }}>
                  ACTIVE PACE MODEL SPECIFICATIONS
                </span>
              </div>
              <span className="font-mono" style={{ fontSize: '0.7rem', color: '#10B981', backgroundColor: 'rgba(16, 185, 129, 0.1)', padding: '2px 8px', borderRadius: '10px' }}>
                CALIBRATED
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px', marginBottom: '1rem' }}>
              <div style={{ backgroundColor: 'var(--bg-card)', padding: '10px', borderRadius: '4px' }}>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>COMPOUND SOFT</div>
                <div className="font-mono" style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--accent-red)' }}>
                  +0.050 s/lap
                </div>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>Degradation slope</div>
              </div>

              <div style={{ backgroundColor: 'var(--bg-card)', padding: '10px', borderRadius: '4px' }}>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>COMPOUND MEDIUM</div>
                <div className="font-mono" style={{ fontSize: '1.1rem', fontWeight: 700, color: '#F59E0B' }}>
                  +0.180 s/lap
                </div>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>Degradation slope</div>
              </div>

              <div style={{ backgroundColor: 'var(--bg-card)', padding: '10px', borderRadius: '4px' }}>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>COMPOUND HARD</div>
                <div className="font-mono" style={{ fontSize: '1.1rem', fontWeight: 700, color: '#E5E7EB' }}>
                  +0.000 s/lap
                </div>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>Zero degradation baseline</div>
              </div>

              <div style={{ backgroundColor: 'var(--bg-card)', padding: '10px', borderRadius: '4px' }}>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>REFERENCE AGE</div>
                <div className="font-mono" style={{ fontSize: '1.1rem', fontWeight: 700, color: '#60A5FA' }}>
                  25 Laps
                </div>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>Pivot tyre age</div>
              </div>
            </div>

            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              fontSize: '0.75rem',
              color: 'var(--text-muted)',
              backgroundColor: 'var(--bg-primary)',
              padding: '8px 12px',
              borderRadius: '4px',
            }}>
              <Info size={14} color="var(--accent-red)" />
              <span>
                Historical counterfactual ranking. Rival future pace is replayed from observed data; this is not yet a live-race forecast.
              </span>
            </div>
          </div>

          {/* Result Preview or Ready State */}
          {result ? (
            <div style={{
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--accent-red)',
              borderRadius: '6px',
              padding: '1.5rem',
              boxShadow: '0 0 25px rgba(225, 6, 0, 0.15)',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Sparkles size={18} color="var(--accent-red)" />
                  <span className="font-display" style={{ fontWeight: 700, fontSize: '1.1rem', color: '#FFFFFF' }}>
                    OPTIMISATION COMPLETED: #{result.recommendation.strategy_id}
                  </span>
                </div>
                <button
                  onClick={onViewResults}
                  style={{
                    backgroundColor: 'var(--accent-red)',
                    color: '#FFFFFF',
                    border: 'none',
                    borderRadius: '4px',
                    padding: '6px 14px',
                    fontSize: '0.78rem',
                    fontFamily: 'var(--font-mono)',
                    fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >
                  VIEW FULL RESULTS & RANKINGS →
                </button>
              </div>

              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(4, 1fr)',
                gap: '12px',
                marginBottom: '1.25rem',
              }}>
                <div style={{ backgroundColor: 'var(--bg-secondary)', padding: '12px', borderRadius: '4px' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>PROJECTED FINISH</div>
                  <div className="font-mono" style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--accent-red)' }}>
                    P{result.recommendation.strategy.projected_final_position}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: (result.recommendation.strategy.positions_gained_vs_actual ?? 0) >= 0 ? '#10B981' : '#EF4444' }}>
                    {(result.recommendation.strategy.positions_gained_vs_actual ?? 0) >= 0 ? '+' : ''}
                    {result.recommendation.strategy.positions_gained_vs_actual ?? 0} vs actual
                  </div>
                </div>

                <div style={{ backgroundColor: 'var(--bg-secondary)', padding: '12px', borderRadius: '4px' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>PIT STOPS</div>
                  <div className="font-mono" style={{ fontSize: '1.6rem', fontWeight: 800, color: '#FFFFFF' }}>
                    {result.recommendation.strategy.num_stops} Stop{result.recommendation.strategy.num_stops !== 1 ? 's' : ''}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                    {result.recommendation.strategy.pit_sequence_str}
                  </div>
                </div>

                <div style={{ backgroundColor: 'var(--bg-secondary)', padding: '12px', borderRadius: '4px' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>CUMULATIVE TIME</div>
                  <div className="font-mono" style={{ fontSize: '1.2rem', fontWeight: 700, color: '#FFFFFF', marginTop: '4px' }}>
                    {result.recommendation.strategy.projected_cumulative_time_s.toFixed(2)}s
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                    Total race time
                  </div>
                </div>

                <div style={{ backgroundColor: 'var(--bg-secondary)', padding: '12px', borderRadius: '4px' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>EVALUATED PLANS</div>
                  <div className="font-mono" style={{ fontSize: '1.6rem', fontWeight: 800, color: '#60A5FA' }}>
                    {result.ranking.length}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                    Candidates scored
                  </div>
                </div>
              </div>

              <div style={{
                backgroundColor: 'var(--bg-secondary)',
                padding: '10px 14px',
                borderRadius: '4px',
                fontSize: '0.8rem',
                color: 'var(--text-secondary)',
              }}>
                <strong style={{ color: '#FFFFFF' }}>Strategy Summary: </strong>
                {result.recommendation.strategy.description}
              </div>
            </div>
          ) : (
            <div style={{
              backgroundColor: 'var(--bg-card)',
              border: '1px dashed var(--border-subtle)',
              borderRadius: '6px',
              padding: '3rem 2rem',
              textAlign: 'center',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <Layers size={36} color="var(--border-strong)" style={{ marginBottom: '1rem' }} />
              <div className="font-display" style={{ fontSize: '1.1rem', fontWeight: 700, color: '#FFFFFF', marginBottom: '0.5rem' }}>
                STRATEGY OPTIMIZER READY
              </div>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', maxWidth: '420px', lineHeight: 1.5 }}>
                Configure the race parameters on the left and click "RUN STRATEGY OPTIMISATION" to generate
                counterfactual strategic rankings against the actual recorded grid telemetry.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

