import React, { useState } from 'react';
import {
  Sliders,
  Play,
  RotateCcw,
  Sparkles,
  ArrowRight,
  TrendingUp,
  AlertCircle,
  HelpCircle,
} from 'lucide-react';
import { OptimizationResponse, StrategyItem, OptimizeRequest } from '../types';
import { getDriverMeta, getSessionMeta } from '../constants';

interface WhatIfLabProps {
  sessionKey: number;
  targetDriver: number;
  baselineResult: OptimizationResponse | null;
  onSimulateAlternative: (params: OptimizeRequest) => Promise<OptimizationResponse | null>;
}

export const WhatIfLab: React.FC<WhatIfLabProps> = ({
  sessionKey,
  targetDriver,
  baselineResult,
  onSimulateAlternative,
}) => {
  const sessionMeta = getSessionMeta(sessionKey);
  const driverMeta = getDriverMeta(targetDriver);

  // What-If test variables
  const [altDecisionLap, setAltDecisionLap] = useState<number>(24);
  const [altPitLoss, setAltPitLoss] = useState<number>(20.0);
  const [altMaxStops, setAltMaxStops] = useState<number>(1);
  const [altTrackMode, setAltTrackMode] = useState<'causal' | 'replay'>('causal');

  const [loading, setLoading] = useState<boolean>(false);
  const [comparisonResult, setComparisonResult] = useState<OptimizationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSimulateWhatIf = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload: OptimizeRequest = {
        session_key: sessionKey,
        target_driver: targetDriver,
        decision_lap: altDecisionLap,
        race_length: sessionMeta.defaultRaceLength || 52,
        track_mode: altTrackMode,
        pit_loss: altPitLoss,
        max_stops: altMaxStops,
        max_candidates: 60,
      };

      const res = await onSimulateAlternative(payload);
      if (res) {
        setComparisonResult(res);
      }
    } catch (err: any) {
      setError(err?.message || 'Simulation failed.');
    } finally {
      setLoading(false);
    }
  };

  const originalStrategy = baselineResult?.recommendation?.strategy;
  const whatIfStrategy = comparisonResult?.recommendation?.strategy;

  return (
    <div style={{ maxWidth: '1440px', margin: '0 auto', padding: '1.5rem 2rem' }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '1.5rem',
        paddingBottom: '1rem',
        borderBottom: '1px solid var(--border-subtle)',
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="font-mono" style={{ fontSize: '0.72rem', color: 'var(--accent-red)', textTransform: 'uppercase' }}>
              PITWALL STRATEGIC SANDBOX
            </span>
            <span style={{ color: 'var(--border-strong)' }}>•</span>
            <span className="font-mono" style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              COUNTERFACTUAL HYPOTHESIS TESTING
            </span>
          </div>
          <h1 className="font-display" style={{ fontSize: '1.6rem', fontWeight: 700, margin: '2px 0 0 0' }}>
            WHAT-IF STRATEGY SIMULATION LAB
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Evaluate counterfactual scenarios (e.g. early pit stop undercut, differing pit lane loss deltas, or aggressive 1-stop targets).
          </p>
        </div>

        <div style={{
          padding: '6px 14px',
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '4px',
          fontFamily: 'var(--font-mono)',
          fontSize: '0.75rem',
          color: 'var(--text-secondary)',
        }}>
          DRIVER: #{driverMeta.number} {driverMeta.code} ({driverMeta.name})
        </div>
      </div>

      {/* Main Grid: Config on left, Side-by-side comparison on right */}
      <div style={{ display: 'grid', gridTemplateColumns: '380px 1fr', gap: '1.75rem' }}>
        {/* Scenario Setup Card */}
        <div style={{
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '6px',
          padding: '1.5rem',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '1.25rem' }}>
            <Sliders size={16} color="var(--accent-red)" />
            <span className="font-display" style={{ fontWeight: 700, fontSize: '1rem' }}>
              HYPOTHESIS CONTROLS
            </span>
          </div>

          {error && (
            <div style={{
              padding: '8px 12px',
              backgroundColor: 'rgba(225, 6, 0, 0.15)',
              border: '1px solid rgba(225, 6, 0, 0.4)',
              borderRadius: '4px',
              fontSize: '0.75rem',
              color: '#FF7B76',
              marginBottom: '1rem',
            }}>
              {error}
            </div>
          )}

          {/* Decision Lap test */}
          <div style={{ marginBottom: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
              <label style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                CALL PIT STOP AT LAP
              </label>
              <span className="font-mono" style={{ fontSize: '0.75rem', color: 'var(--accent-red)' }}>
                Lap {altDecisionLap}
              </span>
            </div>
            <input
              type="range"
              min={10}
              max={45}
              value={altDecisionLap}
              onChange={(e) => setAltDecisionLap(parseInt(e.target.value))}
              style={{ width: '100%', accentColor: 'var(--accent-red)' }}
            />
            <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '4px' }}>
              Simulates triggering strategic undercut or overcut earlier or later.
            </div>
          </div>

          {/* Pit Loss Delta test */}
          <div style={{ marginBottom: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
              <label style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                PIT LANE DELTA (s)
              </label>
              <span className="font-mono" style={{ fontSize: '0.75rem', color: '#60A5FA' }}>
                {altPitLoss.toFixed(1)}s
              </span>
            </div>
            <input
              type="range"
              min={15}
              max={30}
              step={0.5}
              value={altPitLoss}
              onChange={(e) => setAltPitLoss(parseFloat(e.target.value))}
              style={{ width: '100%', accentColor: '#60A5FA' }}
            />
            <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '4px' }}>
              Simulates pit under VSC / Safety Car (approx 14-16s) vs Green Flag (22.0s).
            </div>
          </div>

          {/* Stops limitation */}
          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{
              display: 'block',
              fontSize: '0.75rem',
              fontFamily: 'var(--font-mono)',
              color: 'var(--text-secondary)',
              marginBottom: '6px',
            }}>
              MAXIMUM PIT STOPS TARGET
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '6px' }}>
              {[1, 2, 3].map((stops) => (
                <button
                  key={stops}
                  type="button"
                  onClick={() => setAltMaxStops(stops)}
                  style={{
                    padding: '8px',
                    borderRadius: '4px',
                    border: '1px solid',
                    borderColor: altMaxStops === stops ? 'var(--accent-red)' : 'var(--border-subtle)',
                    backgroundColor: altMaxStops === stops ? 'var(--accent-red-dim)' : 'var(--bg-secondary)',
                    color: altMaxStops === stops ? '#FFFFFF' : 'var(--text-muted)',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.8rem',
                    cursor: 'pointer',
                  }}
                >
                  {stops} Stop{stops > 1 ? 's' : ''}
                </button>
              ))}
            </div>
          </div>

          <button
            onClick={handleSimulateWhatIf}
            disabled={loading}
            style={{
              width: '100%',
              padding: '12px',
              backgroundColor: loading ? 'var(--bg-surface)' : 'var(--accent-red)',
              color: loading ? 'var(--text-muted)' : '#FFFFFF',
              border: 'none',
              borderRadius: '4px',
              fontFamily: 'var(--font-display)',
              fontWeight: 700,
              fontSize: '0.95rem',
              cursor: loading ? 'wait' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
            }}
          >
            {loading ? (
              <span>SIMULATING HYPOTHESIS...</span>
            ) : (
              <>
                <Sparkles size={16} />
                <span>COMPUTE WHAT-IF SCENARIO</span>
              </>
            )}
          </button>
        </div>

        {/* Side-by-side Strategy Delta View */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>
            {/* Baseline Strategy Card */}
            <div style={{
              backgroundColor: 'var(--bg-secondary)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '6px',
              padding: '1.25rem',
            }}>
              <div style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '0.7rem',
                color: 'var(--text-muted)',
                textTransform: 'uppercase',
                marginBottom: '4px',
              }}>
                BASE SCENARIO (ORIGINAL)
              </div>
              <div className="font-display" style={{ fontSize: '1.3rem', fontWeight: 700, marginBottom: '1rem' }}>
                {originalStrategy ? originalStrategy.description : 'Standard Base Strategy'}
              </div>

              {originalStrategy ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px', backgroundColor: 'var(--bg-card)', borderRadius: '4px' }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Projected Position:</span>
                    <span className="font-mono" style={{ fontWeight: 800, color: 'var(--accent-red)' }}>
                      P{originalStrategy.projected_final_position}
                    </span>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px', backgroundColor: 'var(--bg-card)', borderRadius: '4px' }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Cumulative Time:</span>
                    <span className="font-mono" style={{ fontWeight: 700 }}>
                      {originalStrategy.projected_cumulative_time_s.toFixed(2)}s
                    </span>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px', backgroundColor: 'var(--bg-card)', borderRadius: '4px' }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Stops / Sequence:</span>
                    <span className="font-mono" style={{ fontSize: '0.75rem' }}>
                      {originalStrategy.pit_sequence_str}
                    </span>
                  </div>
                </div>
              ) : (
                <div style={{ padding: '2rem 1rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                  No initial strategy executed yet. Run an optimization first.
                </div>
              )}
            </div>

            {/* What-If Alternative Card */}
            <div style={{
              backgroundColor: 'var(--bg-card)',
              border: '1px solid',
              borderColor: comparisonResult ? 'var(--accent-red)' : 'var(--border-subtle)',
              borderRadius: '6px',
              padding: '1.25rem',
              boxShadow: comparisonResult ? '0 0 25px rgba(225, 6, 0, 0.15)' : 'none',
            }}>
              <div style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '0.7rem',
                color: 'var(--accent-red)',
                textTransform: 'uppercase',
                marginBottom: '4px',
              }}>
                WHAT-IF SIMULATION OUTCOME
              </div>
              <div className="font-display" style={{ fontSize: '1.3rem', fontWeight: 700, marginBottom: '1rem' }}>
                {whatIfStrategy ? whatIfStrategy.description : 'Pending Hypothesis Run'}
              </div>

              {whatIfStrategy ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px', backgroundColor: 'var(--bg-secondary)', borderRadius: '4px' }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Projected Position:</span>
                    <span className="font-mono" style={{ fontWeight: 800, color: 'var(--accent-red)' }}>
                      P{whatIfStrategy.projected_final_position}
                    </span>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px', backgroundColor: 'var(--bg-secondary)', borderRadius: '4px' }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Cumulative Time:</span>
                    <span className="font-mono" style={{ fontWeight: 700 }}>
                      {whatIfStrategy.projected_cumulative_time_s.toFixed(2)}s
                    </span>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px', backgroundColor: 'var(--bg-secondary)', borderRadius: '4px' }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Stops / Sequence:</span>
                    <span className="font-mono" style={{ fontSize: '0.75rem' }}>
                      {whatIfStrategy.pit_sequence_str}
                    </span>
                  </div>
                </div>
              ) : (
                <div style={{ padding: '2rem 1rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                  Adjust controls on the left and click "COMPUTE WHAT-IF SCENARIO" to measure time delta.
                </div>
              )}
            </div>
          </div>

          {/* Comparison Delta Delta Bar */}
          {originalStrategy && whatIfStrategy && (
            <div style={{
              backgroundColor: 'var(--bg-secondary)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '6px',
              padding: '1.25rem',
            }}>
              <div className="font-display" style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '8px' }}>
                STRATEGIC DELTA ANALYSIS
              </div>
              <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                {whatIfStrategy.projected_cumulative_time_s < originalStrategy.projected_cumulative_time_s ? (
                  <span style={{ color: '#10B981', fontWeight: 600 }}>
                    ▲ HYPOTHESIS IS FASTER: Saves{' '}
                    {(originalStrategy.projected_cumulative_time_s - whatIfStrategy.projected_cumulative_time_s).toFixed(2)}s
                    over the race distance.
                  </span>
                ) : (
                  <span style={{ color: '#EF4444', fontWeight: 600 }}>
                    ▼ HYPOTHESIS IS SLOWER: Loses{' '}
                    {(whatIfStrategy.projected_cumulative_time_s - originalStrategy.projected_cumulative_time_s).toFixed(2)}s
                    compared to the original recommendation.
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

