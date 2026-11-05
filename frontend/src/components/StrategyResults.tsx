import React, { useState } from 'react';
import {
  Trophy,
  Clock,
  ArrowUpDown,
  Filter,
  CheckCircle2,
  ChevronRight,
  TrendingUp,
  BarChart2,
  Layers,
  ArrowLeft,
} from 'lucide-react';
import { OptimizationResponse, StrategyItem } from '../types';
import { getDriverMeta, getSessionMeta } from '../constants';

interface StrategyResultsProps {
  data: OptimizationResponse;
  onBackToConfig: () => void;
  onOpenReplay: () => void;
  onSelectForWhatIf: (strategy: StrategyItem) => void;
}

export const StrategyResults: React.FC<StrategyResultsProps> = ({
  data,
  onBackToConfig,
  onOpenReplay,
  onSelectForWhatIf,
}) => {
  const { session_key, target_driver, decision_lap, race_length, recommendation, ranking } = data;
  const driverMeta = getDriverMeta(target_driver);
  const sessionMeta = getSessionMeta(session_key);

  const [selectedStrategyId, setSelectedStrategyId] = useState<string>(recommendation.strategy_id);
  const [filterStops, setFilterStops] = useState<number | 'all'>('all');
  const [sortBy, setSortBy] = useState<'position' | 'time' | 'stops'>('position');

  // Filter and sort strategies
  const filteredStrategies = ranking
    .filter((s) => (filterStops === 'all' ? true : s.num_stops === filterStops))
    .sort((a, b) => {
      if (sortBy === 'position') {
        if (a.projected_final_position !== b.projected_final_position) {
          return a.projected_final_position - b.projected_final_position;
        }
        return a.projected_cumulative_time_s - b.projected_cumulative_time_s;
      }
      if (sortBy === 'time') {
        return a.projected_cumulative_time_s - b.projected_cumulative_time_s;
      }
      return a.num_stops - b.num_stops;
    });

  const selectedStrategy = ranking.find((s) => s.strategy_id === selectedStrategyId) || recommendation.strategy;

  const getCompoundBadgeClass = (compound: string) => {
    switch (compound.toUpperCase()) {
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
    <div style={{ maxWidth: '1440px', margin: '0 auto', padding: '1.5rem 2rem' }}>
      {/* Top Banner Navigation */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '1.5rem',
        paddingBottom: '1rem',
        borderBottom: '1px solid var(--border-subtle)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button
            onClick={onBackToConfig}
            style={{
              background: 'transparent',
              border: '1px solid var(--border-subtle)',
              color: 'var(--text-secondary)',
              padding: '6px 12px',
              borderRadius: '4px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              cursor: 'pointer',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.75rem',
            }}
          >
            <ArrowLeft size={14} /> BACK TO CONTROLS
          </button>

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className="font-mono" style={{ fontSize: '0.72rem', color: 'var(--accent-red)', textTransform: 'uppercase' }}>
                OPTIMIZATION RESULTS
              </span>
              <span style={{ color: 'var(--border-strong)' }}>•</span>
              <span className="font-mono" style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                {ranking.length} CANDIDATES EVALUATED
              </span>
            </div>
            <h1 className="font-display" style={{ fontSize: '1.6rem', fontWeight: 700, margin: '2px 0 0 0' }}>
              STRATEGIC SCENARIOS & RANKINGS
            </h1>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button
            onClick={() => onSelectForWhatIf(selectedStrategy)}
            style={{
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-strong)',
              color: '#FFFFFF',
              borderRadius: '4px',
              padding: '8px 16px',
              fontSize: '0.8rem',
              fontFamily: 'var(--font-mono)',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <span>TEST IN WHAT-IF LAB</span>
            <ChevronRight size={14} />
          </button>

          <button
            onClick={onOpenReplay}
            style={{
              backgroundColor: 'var(--accent-red)',
              border: 'none',
              color: '#FFFFFF',
              borderRadius: '4px',
              padding: '8px 16px',
              fontSize: '0.8rem',
              fontFamily: 'var(--font-display)',
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              boxShadow: '0 0 15px rgba(225, 6, 0, 0.4)',
            }}
          >
            <span>INSPECT REPLAY LAPS</span>
            <ChevronRight size={14} />
          </button>
        </div>
      </div>

      {/* RECOMMENDED STRATEGY HERO BOX */}
      <div style={{
        backgroundColor: 'var(--bg-card)',
        border: '1px solid var(--accent-red)',
        borderRadius: '6px',
        padding: '1.5rem',
        marginBottom: '1.75rem',
        boxShadow: '0 0 30px rgba(225, 6, 0, 0.12)',
        position: 'relative',
      }}>
        <div style={{
          position: 'absolute',
          top: '-10px',
          left: '20px',
          backgroundColor: 'var(--accent-red)',
          color: '#FFFFFF',
          padding: '2px 10px',
          borderRadius: '2px',
          fontSize: '0.68rem',
          fontFamily: 'var(--font-mono)',
          fontWeight: 700,
          letterSpacing: '0.08em',
        }}>
          OFFICIAL RECOMMENDED STRATEGY ({recommendation.strategy_id})
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '2rem', marginTop: '0.5rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '0.5rem' }}>
              <div style={{
                fontFamily: 'var(--font-display)',
                fontSize: '1.8rem',
                fontWeight: 700,
                color: '#FFFFFF',
              }}>
                {recommendation.strategy.description}
              </div>
            </div>

            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              marginBottom: '1rem',
              flexWrap: 'wrap',
            }}>
              <span className="tyre-badge tyre-soft" style={{ fontSize: '0.75rem' }}>
                {recommendation.strategy.num_stops} PIT STOP{recommendation.strategy.num_stops !== 1 ? 'S' : ''}
              </span>

              {recommendation.strategy.pit_sequence.map((stop, idx) => (
                <span key={idx} className={`tyre-badge ${getCompoundBadgeClass(stop[1])}`}>
                  STOP {idx + 1}: LAP {stop[0]} ({stop[1]})
                </span>
              ))}

              {recommendation.strategy.pit_sequence.length === 0 && (
                <span className="tyre-badge tyre-hard">NO PIT STOPS (STAY OUT)</span>
              )}
            </div>

            <div style={{
              backgroundColor: 'var(--bg-secondary)',
              padding: '10px 14px',
              borderRadius: '4px',
              fontSize: '0.78rem',
              color: 'var(--text-secondary)',
              lineHeight: 1.5,
            }}>
              <span style={{ color: '#FFFFFF', fontWeight: 600 }}>Pace Interpretation: </span>
              {recommendation.interpretation}
            </div>
          </div>

          {/* Right Metrics Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px' }}>
            <div style={{ backgroundColor: 'var(--bg-secondary)', padding: '12px', borderRadius: '4px', textAlign: 'center' }}>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>PROJECTED FINISH</div>
              <div className="font-mono" style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--accent-red)', margin: '4px 0' }}>
                P{recommendation.strategy.projected_final_position}
              </div>
              <div style={{
                fontSize: '0.72rem',
                color: (recommendation.strategy.positions_gained_vs_actual ?? 0) >= 0 ? '#10B981' : '#EF4444',
                fontWeight: 600,
              }}>
                {(recommendation.strategy.positions_gained_vs_actual ?? 0) >= 0 ? '+' : ''}
                {recommendation.strategy.positions_gained_vs_actual ?? 0} POSITIONS
              </div>
            </div>

            <div style={{ backgroundColor: 'var(--bg-secondary)', padding: '12px', borderRadius: '4px', textAlign: 'center' }}>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>PROJECTED RACE TIME</div>
              <div className="font-mono" style={{ fontSize: '1.25rem', fontWeight: 700, color: '#FFFFFF', margin: '8px 0' }}>
                {recommendation.strategy.projected_cumulative_time_s.toFixed(2)}s
              </div>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                Cumulative seconds
              </div>
            </div>

            <div style={{ backgroundColor: 'var(--bg-secondary)', padding: '12px', borderRadius: '4px', textAlign: 'center' }}>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>ACTUAL RACE DELTA</div>
              <div className="font-mono" style={{ fontSize: '1.25rem', fontWeight: 700, color: '#60A5FA', margin: '8px 0' }}>
                {recommendation.strategy.time_delta_vs_actual_s > 0 ? '+' : ''}
                {recommendation.strategy.time_delta_vs_actual_s.toFixed(1)}s
              </div>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                vs Recorded finish
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* STRATEGY COMPARISON VISUALIZER (BAR COMPARISON OF TOP 6 STRATEGIES) */}
      <div style={{
        backgroundColor: 'var(--bg-secondary)',
        border: '1px solid var(--border-subtle)',
        borderRadius: '6px',
        padding: '1.25rem',
        marginBottom: '1.75rem',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <BarChart2 size={18} color="var(--accent-red)" />
            <span className="font-display" style={{ fontWeight: 700, fontSize: '1rem' }}>
              TOP CANDIDATE TIME DELTA VISUAL COMPARISON
            </span>
          </div>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            LOWER BAR = FASTER RACE TIME (SECONDS)
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '10px' }}>
          {ranking.slice(0, 6).map((strat, idx) => {
            const isRec = strat.strategy_id === recommendation.strategy_id;
            const isSel = strat.strategy_id === selectedStrategyId;
            const minTime = ranking[0].projected_cumulative_time_s;
            const diffFromBest = strat.projected_cumulative_time_s - minTime;

            return (
              <div
                key={strat.strategy_id}
                onClick={() => setSelectedStrategyId(strat.strategy_id)}
                style={{
                  backgroundColor: isSel ? 'var(--bg-card-hover)' : 'var(--bg-card)',
                  border: '1px solid',
                  borderColor: isRec ? 'var(--accent-red)' : isSel ? 'var(--border-strong)' : 'var(--border-subtle)',
                  borderRadius: '4px',
                  padding: '10px',
                  cursor: 'pointer',
                  position: 'relative',
                  transition: 'all 0.15s ease',
                }}
              >
                {isRec && (
                  <div style={{
                    position: 'absolute',
                    top: '-7px',
                    right: '8px',
                    backgroundColor: 'var(--accent-red)',
                    color: '#FFFFFF',
                    fontSize: '0.58rem',
                    padding: '1px 5px',
                    borderRadius: '2px',
                    fontFamily: 'var(--font-mono)',
                    fontWeight: 700,
                  }}>
                    RECOMMENDED
                  </div>
                )}

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '6px' }}>
                  <span className="font-mono" style={{ fontWeight: 700, fontSize: '0.8rem', color: isRec ? 'var(--accent-red)' : '#FFFFFF' }}>
                    #{strat.strategy_id}
                  </span>
                  <span className="font-mono" style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--accent-red)' }}>
                    P{strat.projected_final_position}
                  </span>
                </div>

                <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginBottom: '8px', height: '28px', overflow: 'hidden' }}>
                  {strat.pit_sequence_str}
                </div>

                {/* Relative Delta Bar */}
                <div style={{ backgroundColor: 'var(--bg-primary)', height: '6px', borderRadius: '3px', overflow: 'hidden', marginBottom: '6px' }}>
                  <div style={{
                    width: `${Math.min(100, Math.max(10, 100 - diffFromBest * 1.5))}%`,
                    height: '100%',
                    backgroundColor: isRec ? 'var(--accent-red)' : '#60A5FA',
                  }} />
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', fontFamily: 'var(--font-mono)' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Delta</span>
                  <span style={{ color: diffFromBest === 0 ? '#10B981' : '#FBBF24' }}>
                    {diffFromBest === 0 ? 'FASTEST' : `+${diffFromBest.toFixed(1)}s`}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* STRATEGY RANKINGS TABLE */}
      <div style={{
        backgroundColor: 'var(--bg-card)',
        border: '1px solid var(--border-subtle)',
        borderRadius: '6px',
        overflow: 'hidden',
      }}>
        {/* Table Filters & Controls */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '1rem 1.25rem',
          borderBottom: '1px solid var(--border-subtle)',
          backgroundColor: 'var(--bg-secondary)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Layers size={16} color="var(--accent-red)" />
            <span className="font-display" style={{ fontWeight: 700, fontSize: '0.95rem' }}>
              COMPLETE STRATEGY RANKINGS ({filteredStrategies.length})
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            {/* Filter by Stops */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                STOPS:
              </span>
              {[
                { val: 'all', label: 'All' },
                { val: 0, label: '0 Stop' },
                { val: 1, label: '1 Stop' },
                { val: 2, label: '2 Stops' },
              ].map((opt) => (
                <button
                  key={String(opt.val)}
                  onClick={() => setFilterStops(opt.val as any)}
                  style={{
                    padding: '3px 8px',
                    borderRadius: '3px',
                    border: '1px solid',
                    borderColor: filterStops === opt.val ? 'var(--accent-red)' : 'var(--border-subtle)',
                    backgroundColor: filterStops === opt.val ? 'var(--accent-red-dim)' : 'transparent',
                    color: filterStops === opt.val ? '#FFFFFF' : 'var(--text-muted)',
                    fontSize: '0.7rem',
                    fontFamily: 'var(--font-mono)',
                    cursor: 'pointer',
                  }}
                >
                  {opt.label}
                </button>
              ))}
            </div>

            {/* Sort Toggle */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                SORT:
              </span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                style={{
                  backgroundColor: 'var(--bg-card)',
                  color: '#FFFFFF',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '3px',
                  padding: '4px 8px',
                  fontSize: '0.72rem',
                  fontFamily: 'var(--font-mono)',
                }}
              >
                <option value="position">Projected Position</option>
                <option value="time">Cumulative Time</option>
                <option value="stops">Number of Stops</option>
              </select>
            </div>
          </div>
        </div>

        {/* Table Content */}
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.8rem' }}>
            <thead>
              <tr style={{
                backgroundColor: 'var(--bg-secondary)',
                color: 'var(--text-muted)',
                fontFamily: 'var(--font-mono)',
                fontSize: '0.7rem',
                borderBottom: '1px solid var(--border-subtle)',
              }}>
                <th style={{ padding: '10px 14px' }}>RANK</th>
                <th style={{ padding: '10px 14px' }}>STRATEGY ID</th>
                <th style={{ padding: '10px 14px' }}>PIT SEQUENCE</th>
                <th style={{ padding: '10px 14px' }}>STOPS</th>
                <th style={{ padding: '10px 14px' }}>PROJECTED POS</th>
                <th style={{ padding: '10px 14px' }}>CUMULATIVE TIME</th>
                <th style={{ padding: '10px 14px' }}>POS DELTA</th>
                <th style={{ padding: '10px 14px' }}>TIME DELTA</th>
                <th style={{ padding: '10px 14px' }}>ACTION</th>
              </tr>
            </thead>
            <tbody>
              {filteredStrategies.map((item, idx) => {
                const isRecommended = item.strategy_id === recommendation.strategy_id;
                const isSelected = item.strategy_id === selectedStrategyId;

                return (
                  <tr
                    key={item.strategy_id}
                    onClick={() => setSelectedStrategyId(item.strategy_id)}
                    style={{
                      borderBottom: '1px solid var(--border-subtle)',
                      backgroundColor: isRecommended
                        ? 'rgba(225, 6, 0, 0.08)'
                        : isSelected
                        ? 'var(--bg-card-hover)'
                        : idx % 2 === 0
                        ? 'var(--bg-card)'
                        : 'var(--bg-secondary)',
                      cursor: 'pointer',
                      transition: 'background-color 0.1s ease',
                    }}
                  >
                    <td style={{ padding: '10px 14px', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        {isRecommended && (
                          <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'var(--accent-red)' }} />
                        )}
                        <span>{idx + 1}</span>
                      </div>
                    </td>
                    <td style={{ padding: '10px 14px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: isRecommended ? 'var(--accent-red)' : '#FFFFFF' }}>
                      {item.strategy_id} {isRecommended && '(REC)'}
                    </td>
                    <td style={{ padding: '10px 14px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        {item.pit_sequence.length === 0 ? (
                          <span style={{ color: 'var(--text-muted)' }}>Stay out</span>
                        ) : (
                          item.pit_sequence.map((stop, sIdx) => (
                            <span key={sIdx} className={`tyre-badge ${getCompoundBadgeClass(stop[1])}`}>
                              L{stop[0]} {stop[1]}
                            </span>
                          ))
                        )}
                      </div>
                    </td>
                    <td style={{ padding: '10px 14px', fontFamily: 'var(--font-mono)' }}>
                      {item.num_stops}
                    </td>
                    <td style={{ padding: '10px 14px', fontFamily: 'var(--font-mono)', fontWeight: 800, color: 'var(--accent-red)' }}>
                      P{item.projected_final_position}
                    </td>
                    <td style={{ padding: '10px 14px', fontFamily: 'var(--font-mono)' }}>
                      {item.projected_cumulative_time_s.toFixed(2)}s
                    </td>
                    <td style={{
                      padding: '10px 14px',
                      fontFamily: 'var(--font-mono)',
                      fontWeight: 600,
                      color: (item.positions_gained_vs_actual ?? 0) >= 0 ? '#10B981' : '#EF4444',
                    }}>
                      {(item.positions_gained_vs_actual ?? 0) >= 0 ? '+' : ''}{item.positions_gained_vs_actual ?? 0}
                    </td>
                    <td style={{ padding: '10px 14px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                      {item.time_delta_vs_actual_s > 0 ? '+' : ''}{item.time_delta_vs_actual_s.toFixed(1)}s
                    </td>
                    <td style={{ padding: '10px 14px' }}>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectForWhatIf(item);
                        }}
                        style={{
                          background: 'transparent',
                          border: '1px solid var(--border-subtle)',
                          color: 'var(--text-secondary)',
                          padding: '3px 8px',
                          borderRadius: '3px',
                          fontSize: '0.68rem',
                          fontFamily: 'var(--font-mono)',
                          cursor: 'pointer',
                        }}
                      >
                        SIMULATE
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

