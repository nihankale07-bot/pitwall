import React from 'react';
import {
  Activity,
  Flag,
  Cpu,
  Clock,
  Compass,
  Zap,
  TrendingUp,
  AlertCircle,
  ShieldCheck,
  ChevronRight,
  Database,
  Sliders,
} from 'lucide-react';
import { OptimizationResponse, ActiveWorkspace } from '../types';
import { getDriverMeta, getSessionMeta } from '../constants';

interface RaceControlDashboardProps {
  sessionKey: number;
  targetDriver: number;
  recentResult: OptimizationResponse | null;
  onNavigate: (ws: ActiveWorkspace) => void;
  backendOnline: boolean;
}

export const RaceControlDashboard: React.FC<RaceControlDashboardProps> = ({
  sessionKey,
  targetDriver,
  recentResult,
  onNavigate,
  backendOnline,
}) => {
  const sessionMeta = getSessionMeta(sessionKey);
  const driverMeta = getDriverMeta(targetDriver);

  return (
    <div style={{ maxWidth: '1440px', margin: '0 auto', padding: '1.5rem 2rem' }}>
      {/* Top Banner Overview */}
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
              PITWALL MISSION CONTROL WORKSTATION
            </span>
            <span style={{ color: 'var(--border-strong)' }}>•</span>
            <span className="font-mono" style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              LIVE FASTAPI TELEMETRY LINK
            </span>
          </div>
          <h1 className="font-display" style={{ fontSize: '1.8rem', fontWeight: 700, margin: '2px 0 0 0' }}>
            RACE CONTROL DASHBOARD
          </h1>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            onClick={() => onNavigate('strategy')}
            style={{
              backgroundColor: 'var(--accent-red)',
              color: '#FFFFFF',
              border: 'none',
              borderRadius: '4px',
              padding: '8px 16px',
              fontSize: '0.82rem',
              fontFamily: 'var(--font-display)',
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              boxShadow: '0 0 15px rgba(225, 6, 0, 0.4)',
            }}
          >
            <Cpu size={15} />
            <span>CONFIGURE STRATEGY OPTIMIZATION</span>
          </button>
        </div>
      </div>

      {/* Grid: 4 Metric Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1.25rem', marginBottom: '1.5rem' }}>
        {/* Race Session */}
        <div style={{
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '6px',
          padding: '1.25rem',
          position: 'relative',
        }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase' }}>
            ACTIVE GRAND PRIX SESSION
          </div>
          <div className="font-display" style={{ fontSize: '1.3rem', fontWeight: 700, margin: '6px 0 2px 0' }}>
            {sessionMeta.name}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
            {sessionMeta.circuit} • {sessionMeta.defaultRaceLength} Laps
          </div>
        </div>

        {/* Target Driver Profile */}
        <div style={{
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-subtle)',
          borderLeft: `4px solid ${driverMeta.teamColor}`,
          borderRadius: '6px',
          padding: '1.25rem',
        }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase' }}>
            TARGET DRIVER TELEMETRY
          </div>
          <div className="font-display" style={{ fontSize: '1.3rem', fontWeight: 700, margin: '6px 0 2px 0' }}>
            #{driverMeta.number} {driverMeta.name}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
            {driverMeta.team} ({driverMeta.code})
          </div>
        </div>

        {/* Degradation Model Specs */}
        <div style={{
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '6px',
          padding: '1.25rem',
        }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase' }}>
            CALIBRATED PACE DEGRADATION
          </div>
          <div className="font-mono" style={{ fontSize: '1.3rem', fontWeight: 800, color: '#10B981', margin: '6px 0 2px 0' }}>
            S: +0.05s | M: +0.18s
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            H: 0.00s (Hard reference compound)
          </div>
        </div>

        {/* Fast API Status */}
        <div style={{
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '6px',
          padding: '1.25rem',
        }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase' }}>
            BACKEND CONNECTION
          </div>
          <div className="font-mono" style={{ fontSize: '1.2rem', fontWeight: 700, color: backendOnline ? '#10B981' : '#EF4444', margin: '6px 0 2px 0' }}>
            {backendOnline ? 'CONNECTED (PORT 8000)' : 'API DISCONNECTED'}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Sub-3s Response Latency
          </div>
        </div>
      </div>

      {/* Mid Section: Strategy Engine Status & Recent Results Preview */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>
        {/* Left: Strategy Intelligence Highlight */}
        <div style={{
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '6px',
          padding: '1.5rem',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Cpu size={18} color="var(--accent-red)" />
              <span className="font-display" style={{ fontWeight: 700, fontSize: '1.1rem' }}>
                LATEST STRATEGY RECOMMENDATION
              </span>
            </div>
            {recentResult && (
              <span className="font-mono" style={{ fontSize: '0.72rem', color: 'var(--accent-red)' }}>
                STRATEGY ID: #{recentResult.recommendation.strategy_id}
              </span>
            )}
          </div>

          {recentResult ? (
            <div>
              <div style={{
                backgroundColor: 'var(--bg-secondary)',
                borderRadius: '6px',
                padding: '1.25rem',
                borderLeft: '4px solid var(--accent-red)',
                marginBottom: '1rem',
              }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>
                  OPTIMAL PIT SEQUENCE
                </div>
                <div className="font-display" style={{ fontSize: '1.4rem', fontWeight: 700, color: '#FFFFFF' }}>
                  {recentResult.recommendation.strategy.description}
                </div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '6px' }}>
                  {recentResult.recommendation.interpretation}
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', marginBottom: '1rem' }}>
                <div style={{ backgroundColor: 'var(--bg-secondary)', padding: '10px', borderRadius: '4px' }}>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>PROJECTED POSITION</div>
                  <div className="font-mono" style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--accent-red)' }}>
                    P{recentResult.recommendation.strategy.projected_final_position}
                  </div>
                  <div style={{ fontSize: '0.68rem', color: (recentResult.recommendation.strategy.positions_gained_vs_actual ?? 0) >= 0 ? '#10B981' : '#EF4444' }}>
                    {(recentResult.recommendation.strategy.positions_gained_vs_actual ?? 0) >= 0 ? '+' : ''}
                    {recentResult.recommendation.strategy.positions_gained_vs_actual ?? 0} positions
                  </div>
                </div>

                <div style={{ backgroundColor: 'var(--bg-secondary)', padding: '10px', borderRadius: '4px' }}>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>CUMULATIVE TIME</div>
                  <div className="font-mono" style={{ fontSize: '1.3rem', fontWeight: 700, marginTop: '4px' }}>
                    {recentResult.recommendation.strategy.projected_cumulative_time_s.toFixed(2)}s
                  </div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                    Full race distance
                  </div>
                </div>

                <div style={{ backgroundColor: 'var(--bg-secondary)', padding: '10px', borderRadius: '4px' }}>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>RANKING POOL</div>
                  <div className="font-mono" style={{ fontSize: '1.6rem', fontWeight: 800, color: '#60A5FA' }}>
                    {recentResult.ranking.length}
                  </div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                    Evaluated candidates
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '10px' }}>
                <button
                  onClick={() => onNavigate('results')}
                  style={{
                    backgroundColor: 'var(--accent-red)',
                    color: '#FFFFFF',
                    border: 'none',
                    borderRadius: '4px',
                    padding: '8px 14px',
                    fontSize: '0.78rem',
                    fontFamily: 'var(--font-mono)',
                    fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >
                  OPEN DETAILED RESULTS TABLE →
                </button>
                <button
                  onClick={() => onNavigate('replay')}
                  style={{
                    backgroundColor: 'var(--bg-secondary)',
                    border: '1px solid var(--border-subtle)',
                    color: 'var(--text-secondary)',
                    borderRadius: '4px',
                    padding: '8px 14px',
                    fontSize: '0.78rem',
                    fontFamily: 'var(--font-mono)',
                    cursor: 'pointer',
                  }}
                >
                  LOAD INTO RACE REPLAY
                </button>
              </div>
            </div>
          ) : (
            <div style={{
              padding: '2.5rem 1.5rem',
              textAlign: 'center',
              backgroundColor: 'var(--bg-secondary)',
              borderRadius: '4px',
            }}>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '1rem' }}>
                No active optimization run for this session yet. Launch the Strategy Optimizer to evaluate candidate pit sequences.
              </p>
              <button
                onClick={() => onNavigate('strategy')}
                style={{
                  backgroundColor: 'var(--accent-red)',
                  color: '#FFFFFF',
                  border: 'none',
                  borderRadius: '4px',
                  padding: '8px 16px',
                  fontSize: '0.8rem',
                  fontFamily: 'var(--font-display)',
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                LAUNCH STRATEGY OPTIMIZER
              </button>
            </div>
          )}
        </div>

        {/* Right: Technical Engineering Notes & Data Integrity */}
        <div style={{
          backgroundColor: 'var(--bg-secondary)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '6px',
          padding: '1.5rem',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '1rem' }}>
              <ShieldCheck size={18} color="#10B981" />
              <span className="font-display" style={{ fontWeight: 700, fontSize: '1rem' }}>
                DATA INTEGRITY & ARCHITECTURE
              </span>
            </div>

            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: '1rem' }}>
              PITWALL operates strictly on verified Formula session datasets loaded directly by FastAPI through parquet tables in <code>data/processed/</code>.
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{
                padding: '8px 10px',
                backgroundColor: 'var(--bg-card)',
                borderRadius: '4px',
                fontSize: '0.75rem',
                borderLeft: '3px solid #10B981',
              }}>
                <strong style={{ color: '#FFFFFF' }}>Causal Mode: </strong>
                Only trains degradation slopes on laps recorded up to decision lap.
              </div>
              <div style={{
                padding: '8px 10px',
                backgroundColor: 'var(--bg-card)',
                borderRadius: '4px',
                fontSize: '0.75rem',
                borderLeft: '3px solid #60A5FA',
              }}>
                <strong style={{ color: '#FFFFFF' }}>Replay Mode: </strong>
                Evaluates candidate pit timings against full-race verified rival pace.
              </div>
            </div>
          </div>

          <div style={{
            marginTop: '1.5rem',
            paddingTop: '1rem',
            borderTop: '1px solid var(--border-subtle)',
            fontSize: '0.72rem',
            color: 'var(--text-muted)',
            fontFamily: 'var(--font-mono)',
          }}>
            VERIFIED ENGINE: pitwall-core v0.1.0 • Pydantic V2
          </div>
        </div>
      </div>
    </div>
  );
};

