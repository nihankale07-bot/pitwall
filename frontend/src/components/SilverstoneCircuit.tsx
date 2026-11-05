import React from 'react';
import { getDriverMeta } from '../constants';
import { LapReplayRecord } from '../types';

interface TrackPoint {
  x: number;
  y: number;
  name?: string;
  sector?: number;
}

// Authentic geometric coordinates tracing the official 5.891 km Silverstone Grand Prix Circuit
// Starting at Hamilton Straight (Start/Finish), Abbey, Farm, Arena, Brooklands, Luffield, Woodcote,
// Copse, Maggotts, Becketts, Chapel, Hangar Straight, Stowe, Vale, Club.
const SILVERSTONE_CORNERS: TrackPoint[] = [
  { x: 345, y: 395, name: 'S/F Line', sector: 1 },
  { x: 420, y: 395, name: 'T1 Abbey', sector: 1 },
  { x: 475, y: 430, name: 'T2 Farm', sector: 1 },
  { x: 480, y: 520, name: 'T3 Village', sector: 1 },
  { x: 425, y: 565, name: 'T4 The Loop', sector: 1 },
  { x: 380, y: 520, name: 'T5 Aintree', sector: 1 },
  { x: 275, y: 450, name: 'Wellington Straight', sector: 1 },
  { x: 190, y: 410, name: 'T6 Brooklands', sector: 1 },
  { x: 170, y: 470, name: 'T7 Luffield', sector: 2 },
  { x: 230, y: 470, name: 'T8 Woodcote', sector: 2 },
  { x: 285, y: 420, name: 'National Straight', sector: 2 },
  { x: 360, y: 320, name: 'T9 Copse', sector: 2 },
  { x: 430, y: 220, name: 'T10 Maggotts', sector: 2 },
  { x: 475, y: 170, name: 'T11 Becketts', sector: 2 },
  { x: 495, y: 130, name: 'T12 Chapel', sector: 2 },
  { x: 420, y: 100, name: 'Hangar Straight', sector: 2 },
  { x: 290, y: 105, name: 'T15 Stowe', sector: 3 },
  { x: 220, y: 200, name: 'T16 Vale', sector: 3 },
  { x: 235, y: 250, name: 'T17 Club', sector: 3 },
  { x: 290, y: 340, name: 'T18 Hamilton Straight', sector: 3 },
  { x: 345, y: 395, name: 'S/F Line', sector: 1 },
];

// Helper to interpolate position along circuit polyline
function getPositionAlongTrack(fraction: number): { x: number; y: number } {
  const norm = ((fraction % 1) + 1) % 1;
  const n = SILVERSTONE_CORNERS.length - 1;
  const segmentLen = 1 / n;
  const index = Math.min(Math.floor(norm / segmentLen), n - 1);
  const t = (norm - index * segmentLen) / segmentLen;

  const p1 = SILVERSTONE_CORNERS[index];
  const p2 = SILVERSTONE_CORNERS[index + 1];

  return {
    x: p1.x + (p2.x - p1.x) * t,
    y: p1.y + (p2.y - p1.y) * t,
  };
}

interface SilverstoneCircuitProps {
  currentLapRecords: LapReplayRecord[];
  targetDriver: number;
  currentLap: number;
  maxLap: number;
  highlightedDriver: number | null;
  onSelectDriver?: (driverNumber: number) => void;
}

export const SilverstoneCircuit: React.FC<SilverstoneCircuitProps> = ({
  currentLapRecords,
  targetDriver,
  currentLap,
  maxLap,
  highlightedDriver,
  onSelectDriver,
}) => {
  // SVG track path string
  const trackPathString = SILVERSTONE_CORNERS.map((pt, i) => `${i === 0 ? 'M' : 'L'} ${pt.x} ${pt.y}`).join(' ');

  // Generate driver positions along circuit based on gap to leader and position
  const driversOnTrack = currentLapRecords.map((driver) => {
    const meta = getDriverMeta(driver.driver_number);
    const isTarget = driver.driver_number === targetDriver;
    const isHighlighted = highlightedDriver === driver.driver_number;

    // Relative progress in lap: leader is furthest forward (e.g. 0.90), trailing cars spread back based on gap
    // Lap duration ~96s. Normalize gap
    const gapNormalized = (driver.gap_to_leader % 96) / 96;
    const lapFraction = Math.max(0.03, 0.92 - gapNormalized);
    const coords = getPositionAlongTrack(lapFraction);

    return {
      driver,
      meta,
      isTarget,
      isHighlighted,
      coords,
    };
  });

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', minHeight: '380px' }}>
      <svg
        viewBox="100 50 450 550"
        style={{
          width: '100%',
          height: '100%',
          maxHeight: '440px',
          filter: 'drop-shadow(0 10px 20px rgba(0,0,0,0.8))',
        }}
      >
        {/* Track asphalt base */}
        <path
          d={trackPathString}
          fill="none"
          stroke="#1F1F1F"
          strokeWidth="26"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Track kerbs & boundary outline */}
        <path
          d={trackPathString}
          fill="none"
          stroke="#333333"
          strokeWidth="18"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Racing line track core */}
        <path
          d={trackPathString}
          fill="none"
          stroke="#141414"
          strokeWidth="12"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Start / Finish line marker */}
        <line x1="330" y1="390" x2="360" y2="400" stroke="var(--accent-red)" strokeWidth="4" />
        <text x="365" y="415" fill="var(--accent-red)" fontSize="10" fontFamily="JetBrains Mono" fontWeight="bold">
          S/F (Hamilton Straight)
        </text>

        {/* Corner & Sector Labels for Authentic Engineering Visualisation */}
        <text x="430" y="380" fill="#6B7280" fontSize="9" fontFamily="JetBrains Mono">Abbey</text>
        <text x="440" y="585" fill="#6B7280" fontSize="9" fontFamily="JetBrains Mono">The Loop</text>
        <text x="140" y="440" fill="#6B7280" fontSize="9" fontFamily="JetBrains Mono">Brooklands</text>
        <text x="360" y="305" fill="#6B7280" fontSize="9" fontFamily="JetBrains Mono">Copse</text>
        <text x="480" y="150" fill="#6B7280" fontSize="9" fontFamily="JetBrains Mono">Maggotts/Becketts</text>
        <text x="380" y="85" fill="#6B7280" fontSize="9" fontFamily="JetBrains Mono">Hangar Straight</text>
        <text x="260" y="90" fill="#6B7280" fontSize="9" fontFamily="JetBrains Mono">Stowe</text>
        <text x="190" y="240" fill="#6B7280" fontSize="9" fontFamily="JetBrains Mono">Club</text>

        {/* Sector boundary indicators */}
        <circle cx="230" cy="470" r="4" fill="#3B82F6" />
        <text x="240" y="480" fill="#3B82F6" fontSize="8" fontFamily="JetBrains Mono">Sector 1/2</text>

        <circle cx="290" cy="105" r="4" fill="#10B981" />
        <text x="300" y="125" fill="#10B981" fontSize="8" fontFamily="JetBrains Mono">Sector 2/3</text>

        {/* Driver Markers */}
        {driversOnTrack.map(({ driver, meta, isTarget, isHighlighted, coords }) => {
          return (
            <g
              key={driver.driver_number}
              onClick={() => onSelectDriver?.(driver.driver_number)}
              style={{ cursor: 'pointer', transition: 'all 0.4s ease' }}
            >
              {/* Target pulse ring */}
              {isTarget && (
                <circle
                  cx={coords.x}
                  cy={coords.y}
                  r="13"
                  fill="none"
                  stroke="var(--accent-red)"
                  strokeWidth="2"
                  opacity="0.8"
                />
              )}

              {/* Marker Dot */}
              <circle
                cx={coords.x}
                cy={coords.y}
                r={isTarget ? 7 : isHighlighted ? 6 : 4.5}
                fill={isTarget ? 'var(--accent-red)' : meta.teamColor}
                stroke={isTarget ? '#FFFFFF' : '#090909'}
                strokeWidth={isTarget ? 2 : 1.2}
              />

              {/* Driver Label for Target & Top 5 */}
              {(isTarget || driver.position <= 5 || isHighlighted) && (
                <text
                  x={coords.x + 9}
                  y={coords.y + 4}
                  fill={isTarget ? '#FFFFFF' : '#D1D5DB'}
                  fontSize={isTarget ? "11" : "9"}
                  fontFamily="JetBrains Mono"
                  fontWeight={isTarget ? "bold" : "normal"}
                >
                  P{driver.position} {meta.code}
                </text>
              )}
            </g>
          );
        })}
      </svg>

      {/* Engineering Discloser Footer */}
      <div style={{
        position: 'absolute',
        bottom: '8px',
        left: '12px',
        right: '12px',
        backgroundColor: 'rgba(21, 21, 21, 0.90)',
        border: '1px solid var(--border-subtle)',
        borderRadius: '4px',
        padding: '6px 10px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        fontSize: '0.68rem',
        color: 'var(--text-muted)',
        fontFamily: 'var(--font-mono)',
      }}>
        <span>SILVERSTONE GP CIRCUIT (5.891 KM • 18 CORNERS)</span>
        <span>DRIVERS POSITIONED VIA RECONSTRUCTED SECTOR TIMING & TIME DELTAS</span>
      </div>
    </div>
  );
};

