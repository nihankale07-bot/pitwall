import React, { useState, useMemo } from 'react';
import {
  Play,
  Pause,
  RotateCcw,
  SkipForward,
  SkipBack,
  Sliders,
  Radio,
  Clock,
  Gauge,
  AlertCircle,
  HelpCircle,
  TrendingDown,
  Layers,
} from 'lucide-react';
import { OptimizationResponse, LapReplayRecord } from '../types';
import { getDriverMeta, getSessionMeta } from '../constants';

interface RaceReplayProps {
  data: OptimizationResponse | null;
  sessionKey: number;
  targetDriver: number;
}

export const RaceReplay: React.FC<RaceReplayProps> = ({ data, sessionKey, targetDriver }) => {
  const sessionMeta = getSessionMeta(sessionKey);
  const targetDriverMeta = getDriverMeta(targetDriver);

  // Replay table from best_replay or empty
  const lapsTable: LapReplayRecord[] = useMemo(() => {
    return data?.best_replay?.laps_table || [];
  }, [data]);

  // Max recorded lap in replay table
  const maxLap = useMemo(() => {
    if (!lapsTable.length) return data?.race_length || 52;
    return Math.max(...lapsTable.map((l) => l.lap_number));
  }, [lapsTable, data]);

  const [currentLap, setCurrentLap] = useState<number>(1);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);

  // Playback timer effect
  React.useEffect(() => {
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
      }, 1200);
    }
    return () => clearInterval(interval);
  }, [isPlaying, maxLap]);

  // Get drivers state for the active lap
  const currentLapRecords = useMemo(() => {
    if (!lapsTable.length) return [];
    return lapsTable
      .filter((l) => l.lap_number === currentLap)
      .sort((a, b) => a.position - b.position);
  }, [lapsTable, currentLap]);

  const activeTargetRecord = useMemo(() => {
    return currentLapRecords.find((l) => l.driver_number === targetDriver);
  }, [currentLapRecords, targetDriver]);

  const getCompoundBadgeClass = (compound: string) => {
    switch (compound?.toUpperCase()) {
      case 'SOFT':
        return 'tyre-soft';
      case 'MEDIUM':
        return 'tyre-medium';
      case 'HARD':
        return 'tyre-hard';
      default:
        return 'tyre-hard';
    }
  };

  return (
    <div style={{ maxWidth: '1540px', margin: '0 auto', padding: '1.25rem 2rem' }}>
      {/* Replay Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '1.25rem',
        paddingBottom: '0.75rem',
        borderBottom: '1px solid var(--border-subtle)',
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="font-mono" style={{ fontSize: '0.72rem', color: 'var(--accent-red)', textTransform: 'uppercase' }}>
              RACE REPLAY WORKSPACE • DEVELOPMENT ROADMAP
            </span>
            <span style={{ color: 'var(--border-strong)' }}>•</span>
            <span className="font-mono" style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              SESSION {sessionKey} • SILVERSTONE
            </span>
          </div>
          <h1 className="font-display" style={{ fontSize: '1.6rem', fontWeight: 700, margin: '2px 0 0 0' }}>
            LAP-BY-LAP REPLAY & RACE DYNAMICS
          </h1>
        </div>

        {/* Development badge */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '6px 14px',
          backgroundColor: 'rgba(245, 158, 11, 0.1)',
          border: '1px solid rgba(245, 158, 11, 0.3)',
          borderRadius: '4px',
          fontSize: '0.75rem',
          color: '#FBBF24',
          fontFamily: 'var(--font-mono)',
        }}>
          <Radio size={14} />
          <span>REAL REPLAY TELEMETRY LINKED (SIMULATED POSITION CHANGEOVER)</span>
        </div>
      </div>

      {/* Main Race Telemetry Grid (3 Columns) */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '320px 1fr 340px',
        gap: '1.25rem',
        minHeight: '520px',
        marginBottom: '1.25rem',
      }}>
        {/* LEFT COLUMN: TIMING TOWER */}
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
            <span className="font-display" style={{ fontWeight: 700, fontSize: '0.9rem' }}>
              TIMING TOWER
            </span>
            <span className="font-mono" style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              LAP {currentLap} / {maxLap}
            </span>
          </div>

          <div style={{ flex: 1, overflowY: 'auto' }}>
            {currentLapRecords.length > 0 ? (
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.75rem' }}>
                <thead>
                  <tr style={{
                    color: 'var(--text-muted)',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.65rem',
                    borderBottom: '1px solid var(--border-subtle)',
                  }}>
                    <th style={{ padding: '6px 10px', textAlign: 'left' }}>POS</th>
                    <th style={{ padding: '6px 8px', textAlign: 'left' }}>DRV</th>
                    <th style={{ padding: '6px 8px', textAlign: 'left' }}>GAP</th>
                    <th style={{ padding: '6px 10px', textAlign: 'right' }}>TYRE</th>
                  </tr>
                </thead>
                <tbody>
                  {currentLapRecords.map((driver) => {
                    const meta = getDriverMeta(driver.driver_number);
                    const isTarget = driver.driver_number === targetDriver;

                    return (
                      <tr
                        key={driver.driver_number}
                        style={{
                          borderBottom: '1px solid var(--border-subtle)',
                          backgroundColor: isTarget
                            ? 'rgba(225, 6, 0, 0.15)'
                            : 'transparent',
                        }}
                      >
                        <td style={{
                          padding: '6px 10px',
                          fontFamily: 'var(--font-mono)',
                          fontWeight: 800,
                          color: isTarget ? 'var(--accent-red)' : '#FFFFFF',
                        }}>
                          {driver.position}
                        </td>
                        <td style={{ padding: '6px 8px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span style={{
                              width: '3px',
                              height: '12px',
                              backgroundColor: meta.teamColor,
                              borderRadius: '1px',
                            }} />
                            <span style={{
                              fontFamily: 'var(--font-mono)',
                              fontWeight: 700,
                              color: isTarget ? '#FFFFFF' : 'var(--text-secondary)',
                            }}>
                              {meta.code}
                            </span>
                          </div>
                        </td>
                        <td style={{ padding: '6px 8px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                          {driver.position === 1
                            ? 'LEADER'
                            : driver.gap_to_leader != null
                            ? `+${driver.gap_to_leader.toFixed(2)}`
                            : 'DNF'}
                        </td>
                        <td style={{ padding: '6px 10px', textAlign: 'right' }}>
                          <span className={`tyre-badge ${getCompoundBadgeClass(driver.compound)}`} style={{ fontSize: '0.62rem', padding: '1px 5px' }}>
                            {driver.compound?.[0] || 'M'} • {driver.tyre_age}L
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            ) : (
              <div style={{ padding: '2rem 1rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                Run an optimization first to load the multi-driver replay stream.
              </div>
            )}
          </div>
        </div>

        {/* CENTRE COLUMN: CIRCUIT VISUALISATION & TELEMETRY STREAM */}
        <div style={{
          backgroundColor: 'var(--bg-secondary)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '6px',
          display: 'flex',
          flexDirection: 'column',
          position: 'relative',
          overflow: 'hidden',
        }}>
          <div style={{
            padding: '10px 16px',
            backgroundColor: 'var(--bg-card)',
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Gauge size={16} color="var(--accent-red)" />
              <span className="font-display" style={{ fontWeight: 700, fontSize: '0.9rem' }}>
                CIRCUIT MAP & SECTOR DYNAMICS
              </span>
            </div>
            <div className="font-mono" style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              SILVERSTONE • 5.891 KM
            </div>
          </div>

          {/* SVG Silverstone Visualizer Canvas */}
          <div style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '1.5rem',
            position: 'relative',
          }}>
            {/* Silverstone Track SVG */}
            <svg
              viewBox="0 0 600 400"
              style={{
                width: '100%',
                maxHeight: '340px',
                filter: 'drop-shadow(0 0 10px rgba(0,0,0,0.8))',
              }}
            >
              {/* Circuit Outline */}
              <path
                d="M 120 160 C 130 90, 220 70, 310 90 C 370 100, 430 70, 500 110 C 530 130, 540 180, 500 220 C 470 250, 480 300, 430 330 C 370 360, 330 320, 280 330 C 230 340, 190 320, 150 310 C 100 300, 80 250, 100 200 Z"
                fill="none"
                stroke="#2C2C2C"
                strokeWidth="16"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M 120 160 C 130 90, 220 70, 310 90 C 370 100, 430 70, 500 110 C 530 130, 540 180, 500 220 C 470 250, 480 300, 430 330 C 370 360, 330 320, 280 330 C 230 340, 190 320, 150 310 C 100 300, 80 250, 100 200 Z"
                fill="none"
                stroke="var(--border-strong)"
                strokeWidth="4"
                strokeLinecap="round"
                strokeLinejoin="round"
              />

              {/* Start / Finish line marker */}
              <line x1="120" y1="150" x2="120" y2="170" stroke="var(--accent-red)" strokeWidth="4" />
              <text x="70" y="165" fill="var(--accent-red)" fontSize="10" fontFamily="JetBrains Mono" fontWeight="bold">
                S/F LINE
              </text>

              {/* Sector Markers */}
              <text x="280" y="75" fill="#6B7280" fontSize="10" fontFamily="JetBrains Mono">
                SECTOR 1 (Copse / Maggotts)
              </text>
              <text x="490" y="270" fill="#6B7280" fontSize="10" fontFamily="JetBrains Mono">
                SECTOR 2 (Stowe / Vale)
              </text>
              <text x="180" y="350" fill="#6B7280" fontSize="10" fontFamily="JetBrains Mono">
                SECTOR 3 (Club / Hamilton Straight)
              </text>

              {/* Target Driver Dot simulated position */}
              <circle
                cx={200 + ((currentLap * 17) % 300)}
                cy={120 + ((currentLap * 11) % 180)}
                r="7"
                fill="var(--accent-red)"
                stroke="#FFFFFF"
                strokeWidth="2"
              />
              <text
                x={212 + ((currentLap * 17) % 300)}
                y={125 + ((currentLap * 11) % 180)}
                fill="#FFFFFF"
                fontSize="11"
                fontFamily="JetBrains Mono"
                fontWeight="bold"
              >
                #{targetDriverMeta.number} {targetDriverMeta.code}
              </text>
            </svg>

            {/* Clear Roadmap Placeholder Overlay */}
            <div style={{
              position: 'absolute',
              bottom: '12px',
              left: '16px',
              right: '16px',
              backgroundColor: 'rgba(21, 21, 21, 0.92)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '4px',
              padding: '10px 14px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              backdropFilter: 'blur(4px)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <AlertCircle size={15} color="var(--accent-red)" />
                <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                  <strong>Replay data integration planned:</strong> High-frequency 10Hz GPS coordinates and telemetry stream integration scheduled for future PITWALL engine update.
                </span>
              </div>
              <span className="font-mono" style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                DEV PLACEHOLDER
              </span>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: DRIVER TELEMETRY & STRATEGY CONTEXT */}
        <div style={{
          backgroundColor: 'var(--bg-secondary)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '6px',
          display: 'flex',
          flexDirection: 'column',
          padding: '1.25rem',
          gap: '1.25rem',
        }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span className="font-display" style={{ fontWeight: 700, fontSize: '0.9rem' }}>
                TARGET DRIVER PROFILE
              </span>
              <span style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '0.7rem',
                color: targetDriverMeta.teamColor,
                fontWeight: 700,
              }}>
                #{targetDriverMeta.number} {targetDriverMeta.code}
              </span>
            </div>

            <div style={{
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              borderLeft: `3px solid ${targetDriverMeta.teamColor}`,
              borderRadius: '4px',
              padding: '10px',
            }}>
              <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>{targetDriverMeta.name}</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                {targetDriverMeta.team}
              </div>
            </div>
          </div>

          {/* Current Lap State */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
            <div style={{ backgroundColor: 'var(--bg-card)', padding: '10px', borderRadius: '4px' }}>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>CURRENT POS</div>
              <div className="font-mono" style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--accent-red)' }}>
                {activeTargetRecord ? `P${activeTargetRecord.position}` : 'P2'}
              </div>
              <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>On Lap {currentLap}</div>
            </div>

            <div style={{ backgroundColor: 'var(--bg-card)', padding: '10px', borderRadius: '4px' }}>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>TYRE COMPOUND</div>
              <div className="font-mono" style={{ fontSize: '1.2rem', fontWeight: 700, color: '#FFFFFF', marginTop: '3px' }}>
                {activeTargetRecord?.compound || 'MEDIUM'}
              </div>
              <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                Age: {activeTargetRecord?.tyre_age || currentLap} Laps
              </div>
            </div>

            <div style={{ backgroundColor: 'var(--bg-card)', padding: '10px', borderRadius: '4px' }}>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>GAP TO LEADER</div>
              <div className="font-mono" style={{ fontSize: '1.1rem', fontWeight: 700, color: '#FFFFFF', marginTop: '3px' }}>
                {activeTargetRecord
                  ? activeTargetRecord.gap_to_leader != null
                    ? `+${activeTargetRecord.gap_to_leader.toFixed(2)}s`
                    : 'N/A'
                  : '+0.84s'}
              </div>
              <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>Time delta</div>
            </div>

            <div style={{ backgroundColor: 'var(--bg-card)', padding: '10px', borderRadius: '4px' }}>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>LAST LAP TIME</div>
              <div className="font-mono" style={{ fontSize: '1.1rem', fontWeight: 700, color: '#60A5FA', marginTop: '3px' }}>
                {activeTargetRecord ? `${activeTargetRecord.lap_duration.toFixed(3)}s` : '96.402s'}
              </div>
              <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>Observed / Sim</div>
            </div>
          </div>

          {/* Strategy Context Card */}
          <div style={{
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '4px',
            padding: '12px',
          }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>
              Optimized Pit Sequence
            </div>
            <div style={{ fontWeight: 600, fontSize: '0.85rem', color: '#FFFFFF' }}>
              {data?.recommendation?.strategy?.pit_sequence_str || 'Simulate strategy to view planned pit stops'}
            </div>
          </div>
        </div>
      </div>

      {/* BOTTOM BAR: REPLAY TIMELINE & PLAYBACK CONTROLS */}
      <div style={{
        backgroundColor: 'var(--bg-card)',
        border: '1px solid var(--border-subtle)',
        borderRadius: '6px',
        padding: '1rem 1.5rem',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
          {/* Controls */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              onClick={() => setCurrentLap(1)}
              title="Reset to Lap 1"
              style={{
                backgroundColor: 'var(--bg-secondary)',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text-secondary)',
                padding: '6px',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              <RotateCcw size={14} />
            </button>

            <button
              onClick={() => setCurrentLap((prev) => Math.max(1, prev - 1))}
              title="Previous Lap"
              style={{
                backgroundColor: 'var(--bg-secondary)',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text-secondary)',
                padding: '6px',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              <SkipBack size={14} />
            </button>

            <button
              onClick={() => setIsPlaying(!isPlaying)}
              style={{
                backgroundColor: 'var(--accent-red)',
                border: 'none',
                color: '#FFFFFF',
                padding: '8px 16px',
                borderRadius: '4px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontFamily: 'var(--font-display)',
                fontWeight: 700,
                fontSize: '0.85rem',
                cursor: 'pointer',
              }}
            >
              {isPlaying ? <Pause size={14} /> : <Play size={14} fill="#FFFFFF" />}
              <span>{isPlaying ? 'PAUSE REPLAY' : 'PLAY REPLAY'}</span>
            </button>

            <button
              onClick={() => setCurrentLap((prev) => Math.min(maxLap, prev + 1))}
              title="Next Lap"
              style={{
                backgroundColor: 'var(--bg-secondary)',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text-secondary)',
                padding: '6px',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              <SkipForward size={14} />
            </button>
          </div>

          {/* Active Lap Counter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              CURRENT TIMELINE:
            </span>
            <span className="font-mono" style={{ fontSize: '1.1rem', fontWeight: 800, color: '#FFFFFF' }}>
              LAP {currentLap} <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>/ {maxLap}</span>
            </span>
          </div>
        </div>

        {/* Timeline Slider */}
        <input
          type="range"
          min={1}
          max={maxLap}
          value={currentLap}
          onChange={(e) => setCurrentLap(parseInt(e.target.value))}
          style={{
            width: '100%',
            accentColor: 'var(--accent-red)',
            cursor: 'pointer',
          }}
        />

        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          marginTop: '4px',
          fontSize: '0.68rem',
          color: 'var(--text-muted)',
          fontFamily: 'var(--font-mono)',
        }}>
          <span>LAP 1 (Race Start)</span>
          <span>DECISION LAP (Lap {data?.decision_lap || 26})</span>
          <span>LAP {maxLap} (Chequered Flag)</span>
        </div>
      </div>
    </div>
  );
};

