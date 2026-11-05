import React from 'react';
import { Flag, Activity, Radio, Cpu } from 'lucide-react';
import { getDriverMeta, getSessionMeta } from '../constants';
import { ActiveWorkspace } from '../types';

interface NavbarProps {
  sessionKey: number | null;
  driverNumber: number | null;
  currentWorkspace: ActiveWorkspace;
  onSelectWorkspace: (ws: ActiveWorkspace) => void;
  onExitToLanding: () => void;
  backendOnline: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  sessionKey,
  driverNumber,
  currentWorkspace,
  onSelectWorkspace,
  onExitToLanding,
  backendOnline,
}) => {
  const driverMeta = driverNumber ? getDriverMeta(driverNumber) : null;
  const sessionMeta = sessionKey ? getSessionMeta(sessionKey) : null;

  return (
    <header style={{
      backgroundColor: 'var(--bg-secondary)',
      borderBottom: '1px solid var(--border-subtle)',
      padding: '0 1.5rem',
      height: '60px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      position: 'sticky',
      top: 0,
      zIndex: 100,
    }}>
      {/* Brand & Wordmark */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
        <div
          onClick={onExitToLanding}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.6rem',
            cursor: 'pointer',
            userSelect: 'none',
          }}
        >
          <div style={{
            width: '28px',
            height: '28px',
            backgroundColor: 'var(--accent-red)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transform: 'skewX(-12deg)',
            borderRadius: '2px',
          }}>
            <Flag size={16} color="#ffffff" style={{ transform: 'skewX(12deg)' }} />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span className="font-display" style={{
              fontWeight: 700,
              fontSize: '1.2rem',
              letterSpacing: '0.12em',
              color: '#FFFFFF',
              lineHeight: 1,
            }}>
              PIT<span style={{ color: 'var(--accent-red)' }}>WALL</span>
            </span>
            <span style={{
              fontSize: '0.6rem',
              color: 'var(--text-muted)',
              letterSpacing: '0.2em',
              textTransform: 'uppercase',
              lineHeight: 1,
              marginTop: '2px',
            }}>
              STRATEGY INTELLIGENCE
            </span>
          </div>
        </div>

        {/* Live Backend Connection Badge */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '4px 10px',
          backgroundColor: backendOnline ? 'rgba(16, 185, 129, 0.1)' : 'rgba(225, 6, 0, 0.15)',
          border: `1px solid ${backendOnline ? 'rgba(16, 185, 129, 0.3)' : 'rgba(225, 6, 0, 0.4)'}`,
          borderRadius: '20px',
          fontSize: '0.68rem',
          fontFamily: 'var(--font-mono)',
        }}>
          <span style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            backgroundColor: backendOnline ? '#10B981' : '#E10600',
            boxShadow: backendOnline ? '0 0 8px #10B981' : '0 0 8px #E10600',
          }} />
          <span style={{ color: backendOnline ? '#10B981' : '#FF5A54' }}>
            {backendOnline ? 'FASTAPI LINK ONLINE (127.0.0.1:8000)' : 'FASTAPI LINK OFFLINE'}
          </span>
        </div>
      </div>

      {/* Navigation Links */}
      <nav style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <button
          onClick={() => onSelectWorkspace('integrated_workspace')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '7px',
            padding: '6px 14px',
            backgroundColor: 'var(--bg-card)',
            color: '#FFFFFF',
            border: '1px solid var(--accent-red)',
            borderRadius: '4px',
            cursor: 'pointer',
            fontFamily: 'var(--font-display)',
            fontSize: '0.85rem',
            fontWeight: 600,
          }}
        >
          <Cpu size={14} color="var(--accent-red)" />
          <span>Strategy & Replay Workstation</span>
        </button>
      </nav>

      {/* Active Session & Driver Indicators */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        {sessionMeta && (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'flex-end',
            fontSize: '0.72rem',
            lineHeight: 1.2,
          }}>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.65rem', textTransform: 'uppercase' }}>
              Active Session
            </span>
            <span style={{ color: '#FFFFFF', fontWeight: 600 }}>
              {sessionMeta.name}
            </span>
          </div>
        )}

        {driverMeta && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '4px 10px',
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-subtle)',
            borderLeft: `3px solid ${driverMeta.teamColor}`,
            borderRadius: '4px',
          }}>
            <div style={{
              fontFamily: 'var(--font-mono)',
              fontWeight: 800,
              fontSize: '0.95rem',
              color: '#FFFFFF',
            }}>
              #{driverMeta.number}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#FFFFFF', lineHeight: 1 }}>
                {driverMeta.code}
              </span>
              <span style={{ fontSize: '0.62rem', color: 'var(--text-muted)', lineHeight: 1, marginTop: '2px' }}>
                {driverMeta.team}
              </span>
            </div>
          </div>
        )}

        <button
          onClick={onExitToLanding}
          title="Switch race or driver"
          style={{
            background: 'transparent',
            border: '1px solid var(--border-subtle)',
            color: 'var(--text-secondary)',
            padding: '5px 10px',
            borderRadius: '4px',
            fontSize: '0.72rem',
            cursor: 'pointer',
            fontFamily: 'var(--font-mono)',
            transition: 'border-color 0.2s',
          }}
        >
          CHANGE DRIVER
        </button>
      </div>
    </header>
  );
};
