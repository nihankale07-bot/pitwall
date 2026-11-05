import React, { useState } from 'react';
import { Flag, Play, RefreshCw, AlertCircle, ArrowRight, ShieldCheck, Zap } from 'lucide-react';
import { getDriverMeta, getSessionMeta } from '../constants';

interface LandingPageProps {
  sessions: number[];
  drivers: number[];
  selectedSession: number | null;
  selectedDriver: number | null;
  loadingSessions: boolean;
  loadingDrivers: boolean;
  onSelectSession: (sessionKey: number) => void;
  onSelectDriver: (driverNumber: number) => void;
  onEnterPitwall: () => void;
  onRefresh: () => void;
  backendOnline: boolean;
  errorMessage: string | null;
}

export const LandingPage: React.FC<LandingPageProps> = ({
  sessions,
  drivers,
  selectedSession,
  selectedDriver,
  loadingSessions,
  loadingDrivers,
  onSelectSession,
  onSelectDriver,
  onEnterPitwall,
  onRefresh,
  backendOnline,
  errorMessage,
}) => {
  const [filterTeam, setFilterTeam] = useState<string>('all');

  const selectedDriverMeta = selectedDriver ? getDriverMeta(selectedDriver) : null;
  const selectedSessionMeta = selectedSession ? getSessionMeta(selectedSession) : null;

  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: 'var(--bg-primary)',
      backgroundImage: `
        radial-gradient(circle at 50% 15%, rgba(225, 6, 0, 0.08) 0%, transparent 60%),
        linear-gradient(rgba(255, 255, 255, 0.015) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 255, 255, 0.015) 1px, transparent 1px)
      `,
      backgroundSize: '100% 100%, 32px 32px, 32px 32px',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'space-between',
      padding: '2.5rem 2rem',
    }}>
      {/* Top Bar */}
      <div style={{
        maxWidth: '1280px',
        width: '100%',
        margin: '0 auto',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.8rem' }}>
          <div style={{
            width: '36px',
            height: '36px',
            backgroundColor: 'var(--accent-red)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transform: 'skewX(-14deg)',
            borderRadius: '2px',
            boxShadow: '0 0 15px rgba(225, 6, 0, 0.5)',
          }}>
            <Flag size={20} color="#ffffff" style={{ transform: 'skewX(14deg)' }} />
          </div>
          <div>
            <div className="font-display" style={{
              fontSize: '1.75rem',
              fontWeight: 700,
              letterSpacing: '0.12em',
              lineHeight: 1,
            }}>
              PIT<span style={{ color: 'var(--accent-red)' }}>WALL</span>
            </div>
            <div style={{
              fontSize: '0.68rem',
              color: 'var(--text-muted)',
              letterSpacing: '0.22em',
              textTransform: 'uppercase',
              marginTop: '3px',
              fontFamily: 'var(--font-mono)',
            }}>
              STRATEGY DECISION PLATFORM
            </div>
          </div>
        </div>

        {/* Backend Status indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button
            onClick={onRefresh}
            title="Refresh backend sessions"
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
              fontSize: '0.75rem',
              fontFamily: 'var(--font-mono)',
            }}
          >
            <RefreshCw size={13} className={loadingSessions ? 'spin' : ''} />
            SYNC SESSIONS
          </button>

          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '6px 14px',
            backgroundColor: 'var(--bg-secondary)',
            border: `1px solid ${backendOnline ? 'rgba(16, 185, 129, 0.3)' : 'rgba(225, 6, 0, 0.4)'}`,
            borderRadius: '20px',
            fontSize: '0.75rem',
            fontFamily: 'var(--font-mono)',
          }}>
            <span style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: backendOnline ? '#10B981' : '#E10600',
              boxShadow: backendOnline ? '0 0 10px #10B981' : '0 0 10px #E10600',
            }} />
            <span style={{ color: backendOnline ? '#10B981' : '#FF5A54' }}>
              {backendOnline ? 'BACKEND LINK: 127.0.0.1:8000' : 'BACKEND OFFLINE'}
            </span>
          </div>
        </div>
      </div>

      {/* Main Hero & Station Config */}
      <div style={{
        maxWidth: '1280px',
        width: '100%',
        margin: '2rem auto',
        display: 'grid',
        gridTemplateColumns: '1fr 1.1fr',
        gap: '3rem',
        alignItems: 'center',
      }}>
        {/* Left Column: Vision & Identity */}
        <div>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '5px 12px',
            backgroundColor: 'var(--accent-red-dim)',
            border: '1px solid var(--accent-red-border)',
            borderRadius: '4px',
            color: '#FF5A54',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.78rem',
            fontWeight: 600,
            letterSpacing: '0.08em',
            marginBottom: '1.25rem',
          }}>
            <Zap size={14} /> FORMULA STRATEGY INTELLIGENCE
          </div>

          <h1 className="font-display" style={{
            fontSize: '3.4rem',
            fontWeight: 700,
            lineHeight: 1.05,
            letterSpacing: '0.02em',
            marginBottom: '1.25rem',
            color: '#FFFFFF',
          }}>
            Race Intelligence.<br />
            Strategic Decisions.<br />
            <span style={{ color: 'var(--accent-red)', textShadow: '0 0 35px rgba(225, 6, 0, 0.45)' }}>
              Winning Margins.
            </span>
          </h1>

          <p style={{
            color: 'var(--text-secondary)',
            fontSize: '1.05rem',
            lineHeight: 1.6,
            marginBottom: '2rem',
            maxWidth: '520px',
          }}>
            PITWALL is an elite race engineering workspace delivering tyre degradation modeling, 
            undercut simulation, and multi-stop strategic optimization powered by real Formula telemetry.
          </p>

          {/* Quick Metrics */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: '1rem',
            maxWidth: '520px',
            paddingTop: '1.5rem',
            borderTop: '1px solid var(--border-subtle)',
          }}>
            <div>
              <div className="font-mono" style={{ fontSize: '1.5rem', fontWeight: 700, color: '#FFFFFF' }}>
                {sessions.length > 0 ? `${sessions.length} Race` : '0'}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Verified Datasets</div>
            </div>
            <div>
              <div className="font-mono" style={{ fontSize: '1.5rem', fontWeight: 700, color: '#FFFFFF' }}>
                {drivers.length > 0 ? drivers.length : 20}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Grid Drivers</div>
            </div>
            <div>
              <div className="font-mono" style={{ fontSize: '1.5rem', fontWeight: 700, color: '#10B981' }}>
                0.05s
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Degradation Delta</div>
            </div>
          </div>
        </div>

        {/* Right Column: Mission Control Setup Box */}
        <div style={{
          backgroundColor: 'var(--bg-secondary)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '8px',
          padding: '2rem',
          position: 'relative',
          boxShadow: '0 20px 40px rgba(0, 0, 0, 0.6)',
        }}>
          <div style={{
            position: 'absolute',
            top: 0,
            left: '2rem',
            right: '2rem',
            height: '2px',
            backgroundColor: 'var(--accent-red)',
          }} />

          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: '1.75rem',
          }}>
            <div>
              <div className="font-display" style={{ fontSize: '1.25rem', fontWeight: 700 }}>
                STRATEGY WORKSTATION SETUP
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Select verified race session and target driver telemetry
              </div>
            </div>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.7rem',
              color: 'var(--text-secondary)',
            }}>
              <ShieldCheck size={14} color="#10B981" /> VERIFIED API
            </div>
          </div>

          {errorMessage && (
            <div style={{
              padding: '10px 14px',
              backgroundColor: 'rgba(225, 6, 0, 0.15)',
              border: '1px solid rgba(225, 6, 0, 0.4)',
              borderRadius: '4px',
              marginBottom: '1.5rem',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              fontSize: '0.8rem',
              color: '#FF7B76',
            }}>
              <AlertCircle size={16} color="#E10600" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* STEP 1: RACE SESSION SELECTION */}
          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{
              display: 'block',
              fontSize: '0.75rem',
              fontFamily: 'var(--font-mono)',
              color: 'var(--text-secondary)',
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              marginBottom: '8px',
            }}>
              1. Available Race Session ({sessions.length})
            </label>

            {loadingSessions ? (
              <div style={{
                padding: '1rem',
                backgroundColor: 'var(--bg-card)',
                borderRadius: '6px',
                textAlign: 'center',
                color: 'var(--text-muted)',
                fontSize: '0.85rem',
              }}>
                Querying backend /sessions...
              </div>
            ) : sessions.length === 0 ? (
              <div style={{
                padding: '1rem',
                backgroundColor: 'var(--bg-card)',
                borderRadius: '6px',
                textAlign: 'center',
                color: 'var(--text-muted)',
                fontSize: '0.85rem',
              }}>
                No sessions discovered in data/processed directory.
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '8px' }}>
                {sessions.map((key) => {
                  const meta = getSessionMeta(key);
                  const isSelected = selectedSession === key;
                  return (
                    <div
                      key={key}
                      onClick={() => onSelectSession(key)}
                      style={{
                        padding: '12px 14px',
                        backgroundColor: isSelected ? 'var(--bg-card-hover)' : 'var(--bg-card)',
                        border: '1px solid',
                        borderColor: isSelected ? 'var(--accent-red)' : 'var(--border-subtle)',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span className="font-mono" style={{ fontSize: '0.8rem', color: isSelected ? 'var(--accent-red)' : 'var(--text-muted)' }}>
                          KEY #{key}
                        </span>
                        {isSelected && (
                          <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'var(--accent-red)' }} />
                        )}
                      </div>
                      <div style={{ fontWeight: 700, fontSize: '0.9rem', color: '#FFFFFF', marginTop: '4px' }}>
                        {meta.name}
                      </div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                        {meta.circuit} • {meta.defaultRaceLength} Laps
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* STEP 2: TARGET DRIVER SELECTION */}
          <div style={{ marginBottom: '2rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <label style={{
                display: 'block',
                fontSize: '0.75rem',
                fontFamily: 'var(--font-mono)',
                color: 'var(--text-secondary)',
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
              }}>
                2. Target Driver Telemetry {drivers.length > 0 ? `(${drivers.length} Available)` : ''}
              </label>

              {drivers.length > 0 && (
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                  Passing to backend as target_driver
                </div>
              )}
            </div>

            {loadingDrivers ? (
              <div style={{
                padding: '1.25rem',
                backgroundColor: 'var(--bg-card)',
                borderRadius: '6px',
                textAlign: 'center',
                color: 'var(--text-muted)',
                fontSize: '0.85rem',
              }}>
                Loading session driver grid from /sessions/{selectedSession}/drivers...
              </div>
            ) : drivers.length === 0 ? (
              <div style={{
                padding: '1.25rem',
                backgroundColor: 'var(--bg-card)',
                borderRadius: '6px',
                textAlign: 'center',
                color: 'var(--text-muted)',
                fontSize: '0.85rem',
              }}>
                {selectedSession ? 'No drivers found for this session.' : 'Select a session first to load drivers.'}
              </div>
            ) : (
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(4, 1fr)',
                gap: '8px',
                maxHeight: '220px',
                overflowY: 'auto',
                paddingRight: '4px',
              }}>
                {drivers.map((drvNum) => {
                  const meta = getDriverMeta(drvNum);
                  const isSelected = selectedDriver === drvNum;
                  return (
                    <div
                      key={drvNum}
                      onClick={() => onSelectDriver(drvNum)}
                      style={{
                        padding: '8px 10px',
                        backgroundColor: isSelected ? 'var(--bg-card-hover)' : 'var(--bg-card)',
                        border: '1px solid',
                        borderColor: isSelected ? 'var(--accent-red)' : 'var(--border-subtle)',
                        borderLeft: `3px solid ${meta.teamColor}`,
                        borderRadius: '4px',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
                        <span className="font-mono" style={{
                          fontWeight: 800,
                          fontSize: '1rem',
                          color: isSelected ? '#FFFFFF' : '#D1D5DB',
                        }}>
                          {meta.number}
                        </span>
                        <span style={{ fontSize: '0.72rem', fontWeight: 700, color: meta.teamColor }}>
                          {meta.code}
                        </span>
                      </div>
                      <div style={{
                        fontSize: '0.72rem',
                        color: 'var(--text-secondary)',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        marginTop: '2px',
                      }}>
                        {meta.name.split(' ').pop()}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* STEP 3: ACTION BUTTON */}
          <div>
            <button
              onClick={onEnterPitwall}
              disabled={!selectedSession || !selectedDriver}
              style={{
                width: '100%',
                padding: '14px 20px',
                backgroundColor: (!selectedSession || !selectedDriver) ? 'var(--bg-card)' : 'var(--accent-red)',
                color: (!selectedSession || !selectedDriver) ? 'var(--text-muted)' : '#FFFFFF',
                border: 'none',
                borderRadius: '6px',
                fontFamily: 'var(--font-display)',
                fontWeight: 700,
                fontSize: '1.05rem',
                letterSpacing: '0.1em',
                cursor: (!selectedSession || !selectedDriver) ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '10px',
                transition: 'all 0.2s ease',
                boxShadow: (!selectedSession || !selectedDriver) ? 'none' : '0 0 20px rgba(225, 6, 0, 0.4)',
              }}
            >
              <span>ENTER THE PIT WALL</span>
              <ArrowRight size={18} />
            </button>

            {selectedSessionMeta && selectedDriverMeta && (
              <div style={{
                textAlign: 'center',
                marginTop: '10px',
                fontSize: '0.75rem',
                color: 'var(--text-muted)',
                fontFamily: 'var(--font-mono)',
              }}>
                Targeting: {selectedDriverMeta.name} (#{selectedDriverMeta.number}) • {selectedSessionMeta.name}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Footer Branding */}
      <div style={{
        maxWidth: '1280px',
        width: '100%',
        margin: '0 auto',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingTop: '1.5rem',
        borderTop: '1px solid var(--border-subtle)',
        fontSize: '0.75rem',
        color: 'var(--text-muted)',
        fontFamily: 'var(--font-mono)',
      }}>
        <div>PITWALL STRATEGY INTELLIGENCE PLATFORM • v0.1.0-PRODUCTION</div>
        <div>CONNECTED TO FASTAPI ENGINE (127.0.0.1:8000)</div>
      </div>
    </div>
  );
};

