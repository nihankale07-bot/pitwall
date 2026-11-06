import React, { useState, useEffect, useMemo } from 'react';
import {
  Play,
  Pause,
  RotateCcw,
  SkipForward,
  SkipBack,
  ChevronDown,
  ChevronUp,
  Cpu,
  TrendingUp,
  Clock,
  Layers,
  Sparkles,
  Trophy,
  Sliders,
  ShieldCheck,
  AlertCircle,
  Radio,
} from 'lucide-react';
import { OptimizationResponse, StrategyItem, LapReplayRecord, OptimizeRequest } from '../types';
import { getDriverMeta, getSessionMeta } from '../constants';
import { SilverstoneCircuit } from './SilverstoneCircuit';

interface IntegratedWorkspaceProps {
  sessionKey: number;
  targetDriver: number;
  onRunOptimization: (params: OptimizeRequest) => Promise<void>;
  loading: boolean;
  result: OptimizationResponse | null;
  error: string | null;
}

export const IntegratedWorkspace: React.FC<IntegratedWorkspaceProps> = ({
  sessionKey,
  targetDriver,
  onRunOptimization,
  loading,
  result,
  error,
}) => {
  const sessionMeta = getSessionMeta(sessionKey);
  const driverMeta = getDriverMeta(targetDriver);

  // Simplified User Configuration: ONLY Decision Lap
  const [decisionLap, setDecisionLap] = useState<number>(26);
  const [showTechnicalDrawer, setShowTechnicalDrawer] = useState<boolean>(false);

  // Replay State
  const maxRaceLaps = sessionMeta.defaultRaceLength || 52;
  const [currentLap, setCurrentLap] = useState<number>(1);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1);
  const [highlightedDriver, setHighlightedDriver] = useState<number | null>(null);

  // Auto-set current lap to decision lap upon receiving results
  useEffect(() => {
    if (result) {
      setCurrentLap(result.decision_lap);
    }
  }, [result]);

  // Replay laps records
  const lapsTable: LapReplayRecord[] = useMemo(() => {
    return result?.best_replay?.laps_table || [];
  }, [result]);

  const maxLap = useMemo(() => {
    if (!lapsTable.length) return maxRaceLaps;
    return Math.max(...lapsTable.map((l) => l.lap_number));
  }, [lapsTable, maxRaceLaps]);

  // Playback timer
  useEffect(() => {
    let interval: any = null;
    if (isPlaying) {
      interval = setInterval(() => {
        setCurrentLap((prev) => {
          if (prev >= maxLap) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, 1000 / playbackSpeed);
    }
    return () => clearInterval(interval);
  }, [isPlaying, maxLap, playbackSpeed]);

  // Records for current lap
  const currentLapRecords = useMemo(() => {
    if (!lapsTable.length) return [];
    return lapsTable
      .filter((l) => l.lap_number === currentLap)
      .sort((a, b) => a.position - b.position);
  }, [lapsTable, currentLap]);

  // Projected final classification
  const finalClassification: LapReplayRecord[] = useMemo(() => {
    if (result?.projected_classification?.length) {
      return result.projected_classification;
    }
    if (lapsTable.length) {
      return lapsTable
        .filter((l) => l.lap_number === maxLap)
        .sort((a, b) => a.position - b.position);
    }
    return [];
  }, [result, lapsTable, maxLap]);

  // Strategies: Recommended + Top 2-3 Alternatives + Remaining
  const recommendedStrategy = result?.recommendation?.strategy;
  const alternativeStrategies = useMemo(() => {
    if (!result?.ranking) return [];
    return result.ranking
      .filter((s) => s.strategy_id !== recommendedStrategy?.strategy_id)
      .slice(0, 3);
  }, [result, recommendedStrategy]);

  const remainingStrategies = useMemo(() => {
    if (!result?.ranking) return [];
    return result.ranking
      .filter(
        (s) =>
          s.strategy_id !== recommendedStrategy?.strategy_id &&
          !alternativeStrategies.some((a) => a.strategy_id === s.strategy_id)
      );
  }, [result, recommendedStrategy, alternativeStrategies]);

  const handleRun = (e: React.FormEvent) => {
    e.preventDefault();
    onRunOptimization({
      session_key: sessionKey,
      target_driver: targetDriver,
      decision_lap: decisionLap,
    });
  };

  const getCompoundBadge = (compound: string) => {
    switch (compound?.toUpperCase()) {
      case 'SOFT':
        return 'tyre-soft';
      case 'MEDIUM':
        return 'tyre-medium';
      case 'HARD':
        return 'tyre-hard';
      case 'INTERMEDIATE':
        return 'tyre-inter';
      default:
        return 'tyre-hard';
    }
  };

  return (
    <div style={{ maxWidth: '1540px', margin: '0 auto', padding: '1.25rem 2rem' }}>
      {/* Station Header with Selected Driver Context */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '1.25rem',
        paddingBottom: '0.75rem',
        borderBottom: '1px solid var(--border-subtle)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className="font-mono" style={{ fontSize: '0.72rem', color: 'var(--accent-red)', textTransform: 'uppercase' }}>
                INTEGRATED RACE STRATEGY WORKSTATION
              </span>
              <span style={{ color: 'var(--border-strong)' }}>•</span>
              <span className="font-mono" style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                {sessionMeta.name} • {sessionMeta.circuit} ({maxRaceLaps} LAPS)
              </span>
            </div>
            <h1 className="font-display" style={{ fontSize: '1.6rem', fontWeight: 700, margin: '2px 0 0 0' }}>
              STRATEGY OPTIMISATION & REAL-TIME REPLAY
            </h1>
          </div>
        </div>

        {/* Driver Badge */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          padding: '6px 14px',
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-subtle)',
          borderLeft: `4px solid ${driverMeta.teamColor}`,
          borderRadius: '4px',
        }}>
          <div className="font-mono" style={{ fontSize: '1.2rem', fontWeight: 800, color: '#FFFFFF' }}>
            #{driverMeta.number}
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: '0.85rem' }}>{driverMeta.name}</div>
            <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>{driverMeta.team}</div>
          </div>
        </div>
      </div>

      {/* USER CONTROL CONSOLE: Simplified to Decision Lap + Run Button */}
      <div style={{
        backgroundColor: 'var(--bg-card)',
        border: '1px solid var(--border-subtle)',
        borderRadius: '6px',
        padding: '1.25rem 1.5rem',
        marginBottom: '1.5rem',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: '2rem',
      }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
            <label style={{ fontSize: '0.78rem', fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--text-secondary)' }}>
              STRATEGY DECISION LAP
            </label>
            <span className="font-mono" style={{ fontSize: '0.9rem', fontWeight: 800, color: 'var(--accent-red)' }}>
              LAP {decisionLap} <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>/ {maxRaceLaps}</span>
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <input
              type="range"
              min={1}
              max={maxRaceLaps - 1}
              value={decisionLap}
              onChange={(e) => setDecisionLap(parseInt(e.target.value) || 1)}
              style={{ flex: 1, accentColor: 'var(--accent-red)', cursor: 'pointer' }}
            />
            <div style={{ display: 'flex', gap: '4px' }}>
              <button
                type="button"
                onClick={() => setDecisionLap((prev) => Math.max(1, prev - 1))}
                style={{
                  backgroundColor: 'var(--bg-secondary)',
                  border: '1px solid var(--border-subtle)',
                  color: 'var(--text-secondary)',
                  padding: '4px 8px',
                  borderRadius: '3px',
                  fontSize: '0.75rem',
                  fontFamily: 'var(--font-mono)',
                  cursor: 'pointer',
                }}
              >
                -1
              </button>
              <button
                type="button"
                onClick={() => setDecisionLap((prev) => Math.min(maxRaceLaps - 1, prev + 1))}
                style={{
                  backgroundColor: 'var(--bg-secondary)',
                  border: '1px solid var(--border-subtle)',
                  color: 'var(--text-secondary)',
                  padding: '4px 8px',
                  borderRadius: '3px',
                  fontSize: '0.75rem',
                  fontFamily: 'var(--font-mono)',
                  cursor: 'pointer',
                }}
              >
                +1
              </button>
            </div>
          </div>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '4px', fontFamily: 'var(--font-mono)' }}>
            Simulates optimal strategy based on causal pace observations up to lap {decisionLap}.
          </div>
        </div>

        {/* Action Button */}
        <div>
          <button
            onClick={handleRun}
            disabled={loading}
            style={{
              padding: '12px 28px',
              backgroundColor: loading ? 'var(--bg-secondary)' : 'var(--accent-red)',
              color: loading ? 'var(--text-muted)' : '#FFFFFF',
              border: 'none',
              borderRadius: '4px',
              fontFamily: 'var(--font-display)',
              fontWeight: 700,
              fontSize: '1rem',
              letterSpacing: '0.06em',
              cursor: loading ? 'wait' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              boxShadow: loading ? 'none' : '0 0 20px rgba(225, 6, 0, 0.4)',
              transition: 'all 0.2s ease',
            }}
          >
            {loading ? (
              <>
                <div className="spin" style={{
                  width: '16px',
                  height: '16px',
                  border: '2px solid rgba(255,255,255,0.2)',
                  borderTopColor: '#FFFFFF',
                  borderRadius: '50%',
                }} />
                <span>SOLVING CAUSAL STRATEGY...</span>
              </>
            ) : (
              <>
                <Cpu size={18} />
                <span>RUN STRATEGY OPTIMISATION</span>
              </>
            )}
          </button>
        </div>
      </div>

      {error && (
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
          <AlertCircle size={16} color="#E10600" />
          <span>{error}</span>
        </div>
      )}

      {/* STRATEGY RESULTS SECTION (When Result Exists) */}
      {result && recommendedStrategy && (
        <div style={{ marginBottom: '1.5rem' }}>
          {/* Top row: Recommended strategy card + 2-3 Alternative cards */}
          <div style={{ display: 'grid', gridTemplateColumns: '1.3fr 1fr', gap: '1.25rem', marginBottom: '1rem' }}>
            {/* RECOMMENDED STRATEGY HERO CARD */}
            <div style={{
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--accent-red)',
              borderRadius: '6px',
              padding: '1.25rem 1.5rem',
              boxShadow: '0 0 25px rgba(225, 6, 0, 0.15)',
              position: 'relative',
            }}>
              <div style={{
                position: 'absolute',
                top: '-9px',
                left: '16px',
                backgroundColor: 'var(--accent-red)',
                color: '#FFFFFF',
                padding: '1px 8px',
                borderRadius: '2px',
                fontSize: '0.65rem',
                fontFamily: 'var(--font-mono)',
                fontWeight: 700,
              }}>
                PRIMARY STRATEGY RECOMMENDATION (#{recommendedStrategy.strategy_id})
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginTop: '4px' }}>
                <div>
                  <div className="font-display" style={{ fontSize: '1.4rem', fontWeight: 700 }}>
                    {recommendedStrategy.description}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '6px' }}>
                    <span className="tyre-badge tyre-soft">
                      {recommendedStrategy.num_stops} STOP{recommendedStrategy.num_stops !== 1 ? 'S' : ''}
                    </span>
                    {recommendedStrategy.pit_sequence.map((stop, sIdx) => (
                      <span key={sIdx} className={`tyre-badge ${getCompoundBadge(stop[1])}`}>
                        L{stop[0]} {stop[1]}
                      </span>
                    ))}
                  </div>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>PROJECTED FINISH</div>
                  <div className="font-mono" style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--accent-red)' }}>
                    P{recommendedStrategy.projected_final_position}
                  </div>
                  <div style={{
                    fontSize: '0.72rem',
                    color: (recommendedStrategy.positions_gained_vs_actual ?? 0) >= 0 ? '#10B981' : '#EF4444',
                    fontFamily: 'var(--font-mono)',
                  }}>
                    {(recommendedStrategy.positions_gained_vs_actual ?? 0) >= 0 ? '+' : ''}
                    {recommendedStrategy.positions_gained_vs_actual ?? 0} vs actual
                  </div>
                </div>
              </div>

              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: '8px',
                marginTop: '1rem',
                paddingTop: '0.75rem',
                borderTop: '1px solid var(--border-subtle)',
              }}>
                <div>
                  <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>PROJECTED RACE TIME</div>
                  <div className="font-mono" style={{ fontSize: '1rem', fontWeight: 700 }}>
                    {recommendedStrategy.projected_cumulative_time_s.toFixed(2)}s
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>DELTA VS BASELINE</div>
                  <div className="font-mono" style={{ fontSize: '1rem', fontWeight: 700, color: '#10B981' }}>
                    {recommendedStrategy.time_delta_vs_actual_s != null ? (
                      `${recommendedStrategy.time_delta_vs_actual_s > 0 ? '+' : ''}${recommendedStrategy.time_delta_vs_actual_s.toFixed(1)}s`
                    ) : (
                      'N/A (DNF/Lapped)'
                    )}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>REPLAY SIMULATION</div>
                  <div className="font-mono" style={{ fontSize: '0.85rem', color: '#60A5FA', marginTop: '2px' }}>
                    ACTIVE ON TRACK
                  </div>
                </div>
              </div>
            </div>

            {/* STRONGEST ALTERNATIVES */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase' }}>
                STRONGEST CANDIDATE ALTERNATIVES ({alternativeStrategies.length})
              </div>

              {alternativeStrategies.map((alt) => {
                const deltaToBest = alt.projected_cumulative_time_s - recommendedStrategy.projected_cumulative_time_s;
                return (
                  <div
                    key={alt.strategy_id}
                    style={{
                      backgroundColor: 'var(--bg-secondary)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: '4px',
                      padding: '8px 12px',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span className="font-mono" style={{ fontWeight: 700, fontSize: '0.78rem' }}>
                          #{alt.strategy_id}
                        </span>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                          {alt.pit_sequence_str}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                        {alt.num_stops} Stop{alt.num_stops !== 1 ? 's' : ''} • {alt.projected_cumulative_time_s.toFixed(1)}s
                      </div>
                    </div>

                    <div style={{ textAlign: 'right' }}>
                      <span className="font-mono" style={{ fontSize: '1rem', fontWeight: 800, color: '#FFFFFF' }}>
                        P{alt.projected_final_position}
                      </span>
                      <div className="font-mono" style={{ fontSize: '0.68rem', color: '#FBBF24' }}>
                        +{deltaToBest.toFixed(1)}s delta
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Optional Expandable Technical Drawer */}
          {remainingStrategies.length > 0 && (
            <div>
              <button
                onClick={() => setShowTechnicalDrawer(!showTechnicalDrawer)}
                style={{
                  background: 'transparent',
                  border: '1px solid var(--border-subtle)',
                  color: 'var(--text-secondary)',
                  padding: '6px 12px',
                  borderRadius: '4px',
                  fontSize: '0.72rem',
                  fontFamily: 'var(--font-mono)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                {showTechnicalDrawer ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                <span>
                  {showTechnicalDrawer ? 'HIDE' : 'EXPAND'} ALL {result.ranking.length} STRATEGY CANDIDATES
                </span>
              </button>

              {showTechnicalDrawer && (
                <div style={{
                  marginTop: '10px',
                  backgroundColor: 'var(--bg-secondary)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '4px',
                  maxHeight: '220px',
                  overflowY: 'auto',
                }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.75rem' }}>
                    <thead>
                      <tr style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', borderBottom: '1px solid var(--border-subtle)' }}>
                        <th style={{ padding: '6px 10px', textAlign: 'left' }}>ID</th>
                        <th style={{ padding: '6px 10px', textAlign: 'left' }}>SEQUENCE</th>
                        <th style={{ padding: '6px 10px', textAlign: 'left' }}>STOPS</th>
                        <th style={{ padding: '6px 10px', textAlign: 'right' }}>POS</th>
                        <th style={{ padding: '6px 10px', textAlign: 'right' }}>TIME</th>
                        <th style={{ padding: '6px 10px', textAlign: 'right' }}>DELTA</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.ranking.map((s) => (
                        <tr key={s.strategy_id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                          <td style={{ padding: '5px 10px', fontFamily: 'var(--font-mono)' }}>{s.strategy_id}</td>
                          <td style={{ padding: '5px 10px' }}>{s.pit_sequence_str}</td>
                          <td style={{ padding: '5px 10px' }}>{s.num_stops}</td>
                          <td style={{ padding: '5px 10px', textAlign: 'right', fontWeight: 700 }}>P{s.projected_final_position}</td>
                          <td style={{ padding: '5px 10px', textAlign: 'right', fontFamily: 'var(--font-mono)' }}>
                            {s.projected_cumulative_time_s.toFixed(1)}s
                          </td>
                          <td style={{ padding: '5px 10px', textAlign: 'right', fontFamily: 'var(--font-mono)' }}>
                            {s.time_delta_vs_actual_s != null ? (
                              `${s.time_delta_vs_actual_s > 0 ? '+' : ''}${s.time_delta_vs_actual_s.toFixed(1)}s`
                            ) : (
                              'N/A'
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* INTEGRATED RACE REPLAY & PROJECTED STANDINGS */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 360px',
        gap: '1.25rem',
        marginBottom: '1rem',
      }}>
        {/* Left: Circuit Visualisation + Scrubbable Replay Controller */}
        <div style={{
          backgroundColor: 'var(--bg-secondary)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '6px',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}>
          {/* Replay Controls Bar */}
          <div style={{
            padding: '10px 14px',
            backgroundColor: 'var(--bg-card)',
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button
                type="button"
                onClick={() => setCurrentLap(1)}
                title="Reset to Lap 1"
                style={{
                  backgroundColor: 'var(--bg-secondary)',
                  border: '1px solid var(--border-subtle)',
                  color: 'var(--text-secondary)',
                  padding: '6px',
                  borderRadius: '3px',
                  cursor: 'pointer',
                }}
              >
                <RotateCcw size={14} />
              </button>

              <button
                type="button"
                onClick={() => setCurrentLap((prev) => Math.max(1, prev - 1))}
                title="Previous Lap"
                style={{
                  backgroundColor: 'var(--bg-secondary)',
                  border: '1px solid var(--border-subtle)',
                  color: 'var(--text-secondary)',
                  padding: '6px',
                  borderRadius: '3px',
                  cursor: 'pointer',
                }}
              >
                <SkipBack size={14} />
              </button>

              <button
                type="button"
                onClick={() => setIsPlaying(!isPlaying)}
                style={{
                  backgroundColor: 'var(--accent-red)',
                  border: 'none',
                  color: '#FFFFFF',
                  padding: '6px 14px',
                  borderRadius: '3px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontFamily: 'var(--font-display)',
                  fontWeight: 700,
                  fontSize: '0.8rem',
                  cursor: 'pointer',
                }}
              >
                {isPlaying ? <Pause size={13} /> : <Play size={13} fill="#FFFFFF" />}
                <span>{isPlaying ? 'PAUSE' : 'PLAY'}</span>
              </button>

              <button
                type="button"
                onClick={() => setCurrentLap((prev) => Math.min(maxLap, prev + 1))}
                title="Next Lap"
                style={{
                  backgroundColor: 'var(--bg-secondary)',
                  border: '1px solid var(--border-subtle)',
                  color: 'var(--text-secondary)',
                  padding: '6px',
                  borderRadius: '3px',
                  cursor: 'pointer',
                }}
              >
                <SkipForward size={14} />
              </button>

              {/* Speed controls */}
              <div style={{ display: 'flex', gap: '2px', marginLeft: '6px' }}>
                {[1, 2, 4].map((speed) => (
                  <button
                    key={speed}
                    type="button"
                    onClick={() => setPlaybackSpeed(speed)}
                    style={{
                      backgroundColor: playbackSpeed === speed ? 'var(--accent-red)' : 'var(--bg-secondary)',
                      color: playbackSpeed === speed ? '#FFFFFF' : 'var(--text-muted)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: '2px',
                      padding: '2px 6px',
                      fontSize: '0.65rem',
                      fontFamily: 'var(--font-mono)',
                      cursor: 'pointer',
                    }}
                  >
                    {speed}x
                  </button>
                ))}
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span className="font-mono" style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                CURRENT LAP:
              </span>
              <span className="font-mono" style={{ fontSize: '1.1rem', fontWeight: 800, color: '#FFFFFF' }}>
                {currentLap} <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>/ {maxLap}</span>
              </span>
            </div>
          </div>

          {/* Authentic Silverstone Circuit SVG Visualiser */}
          <div style={{ flex: 1, padding: '1rem', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <SilverstoneCircuit
              currentLapRecords={currentLapRecords}
              targetDriver={targetDriver}
              currentLap={currentLap}
              maxLap={maxLap}
              highlightedDriver={highlightedDriver}
              onSelectDriver={(drv) => setHighlightedDriver(drv)}
            />
          </div>

          {/* Scrubbable Timeline Slider */}
          <div style={{ padding: '8px 16px', backgroundColor: 'var(--bg-card)', borderTop: '1px solid var(--border-subtle)' }}>
            <input
              type="range"
              min={1}
              max={maxLap}
              value={currentLap}
              onChange={(e) => setCurrentLap(parseInt(e.target.value))}
              style={{ width: '100%', accentColor: 'var(--accent-red)', cursor: 'pointer' }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
              <span>LAP 1</span>
              <span>DECISION LAP {decisionLap}</span>
              <span>CHEQUERED FLAG (LAP {maxLap})</span>
            </div>
          </div>
        </div>

        {/* Right: Projected Standings / Timing Tower Alongside Replay */}
        <div style={{
          backgroundColor: 'var(--bg-secondary)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '6px',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}>
          <div style={{
            padding: '10px 14px',
            backgroundColor: 'var(--bg-card)',
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <span className="font-display" style={{ fontWeight: 700, fontSize: '0.85rem' }}>
              {currentLap === maxLap ? 'PROJECTED RACE CLASSIFICATION' : `STANDINGS (LAP ${currentLap})`}
            </span>
            <span className="font-mono" style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
              {currentLapRecords.length} DRIVERS
            </span>
          </div>

          <div style={{ flex: 1, overflowY: 'auto', maxHeight: '460px' }}>
            {currentLapRecords.length > 0 ? (
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.72rem' }}>
                <thead>
                  <tr style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '0.62rem', borderBottom: '1px solid var(--border-subtle)' }}>
                    <th style={{ padding: '6px 8px', textAlign: 'left' }}>POS</th>
                    <th style={{ padding: '6px 8px', textAlign: 'left' }}>DRV</th>
                    <th style={{ padding: '6px 8px', textAlign: 'right' }}>GAP</th>
                    <th style={{ padding: '6px 8px', textAlign: 'right' }}>TYRE</th>
                  </tr>
                </thead>
                <tbody>
                  {currentLapRecords.map((driver) => {
                    const meta = getDriverMeta(driver.driver_number);
                    const isTarget = driver.driver_number === targetDriver;
                    const isHighlighted = highlightedDriver === driver.driver_number;

                    return (
                      <tr
                        key={driver.driver_number}
                        onMouseEnter={() => setHighlightedDriver(driver.driver_number)}
                        onMouseLeave={() => setHighlightedDriver(null)}
                        style={{
                          borderBottom: '1px solid var(--border-subtle)',
                          backgroundColor: isTarget
                            ? 'rgba(225, 6, 0, 0.18)'
                            : isHighlighted
                            ? 'var(--bg-card-hover)'
                            : 'transparent',
                          cursor: 'pointer',
                        }}
                      >
                        <td style={{ padding: '6px 8px', fontFamily: 'var(--font-mono)', fontWeight: 800, color: isTarget ? 'var(--accent-red)' : '#FFFFFF' }}>
                          {driver.position}
                        </td>
                        <td style={{ padding: '6px 8px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span style={{ width: '3px', height: '11px', backgroundColor: meta.teamColor, borderRadius: '1px' }} />
                            <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: isTarget ? '#FFFFFF' : 'var(--text-secondary)' }}>
                              {meta.code}
                            </span>
                          </div>
                        </td>
                        <td style={{ padding: '6px 8px', textAlign: 'right', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                          {driver.position === 1
                            ? 'LEADER'
                            : driver.gap_to_leader != null
                            ? `+${driver.gap_to_leader.toFixed(1)}s`
                            : 'DNF'}
                        </td>
                        <td style={{ padding: '6px 8px', textAlign: 'right' }}>
                          <span className={`tyre-badge ${getCompoundBadge(driver.compound)}`} style={{ fontSize: '0.6rem', padding: '1px 4px' }}>
                            {driver.compound?.[0] || 'M'} {driver.tyre_age}L
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            ) : (
              <div style={{ padding: '2rem 1rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.78rem' }}>
                Run optimization above to launch the integrated replay and live standings.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

