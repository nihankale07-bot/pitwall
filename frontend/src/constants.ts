import { DriverMetadata } from './types';

export const F1_DRIVERS_METADATA: Record<number, DriverMetadata> = {
  1: { number: 1, code: 'VER', name: 'Max Verstappen', team: 'Red Bull Racing', teamColor: '#3671C6' },
  11: { number: 11, code: 'PER', name: 'Sergio Perez', team: 'Red Bull Racing', teamColor: '#3671C6' },
  44: { number: 44, code: 'HAM', name: 'Lewis Hamilton', team: 'Mercedes-AMG', teamColor: '#27F4D2' },
  63: { number: 63, code: 'RUS', name: 'George Russell', team: 'Mercedes-AMG', teamColor: '#27F4D2' },
  16: { number: 16, code: 'LEC', name: 'Charles Leclerc', team: 'Ferrari', teamColor: '#E8002D' },
  55: { number: 55, code: 'SAI', name: 'Carlos Sainz', team: 'Ferrari', teamColor: '#E8002D' },
  4: { number: 4, code: 'NOR', name: 'Lando Norris', team: 'McLaren', teamColor: '#FF8000' },
  81: { number: 81, code: 'PIA', name: 'Oscar Piastri', team: 'McLaren', teamColor: '#FF8000' },
  14: { number: 14, code: 'ALO', name: 'Fernando Alonso', team: 'Aston Martin', teamColor: '#229971' },
  18: { number: 18, code: 'STR', name: 'Lance Stroll', team: 'Aston Martin', teamColor: '#229971' },
  10: { number: 10, code: 'GAS', name: 'Pierre Gasly', team: 'Alpine', teamColor: '#FF87BC' },
  31: { number: 31, code: 'OCO', name: 'Esteban Ocon', team: 'Alpine', teamColor: '#FF87BC' },
  23: { number: 23, code: 'ALB', name: 'Alexander Albon', team: 'Williams', teamColor: '#64C4FF' },
  2: { number: 2, code: 'SAR', name: 'Logan Sargeant', team: 'Williams', teamColor: '#64C4FF' },
  3: { number: 3, code: 'RIC', name: 'Daniel Ricciardo', team: 'RB', teamColor: '#6692FF' },
  22: { number: 22, code: 'TSU', name: 'Yuki Tsunoda', team: 'RB', teamColor: '#6692FF' },
  77: { number: 77, code: 'BOT', name: 'Valtteri Bottas', team: 'Kick Sauber', teamColor: '#52E252' },
  24: { number: 24, code: 'ZHO', name: 'Zhou Guanyu', team: 'Kick Sauber', teamColor: '#52E252' },
  27: { number: 27, code: 'HUL', name: 'Nico Hulkenberg', team: 'Haas', teamColor: '#B6BABD' },
  20: { number: 20, code: 'MAG', name: 'Kevin Magnussen', team: 'Haas', teamColor: '#B6BABD' },
};

export const SESSION_METADATA: Record<number, { name: string; circuit: string; country: string; year: number; defaultRaceLength: number }> = {
  9558: {
    name: '2024 British Grand Prix',
    circuit: 'Silverstone Circuit',
    country: 'United Kingdom',
    year: 2024,
    defaultRaceLength: 52,
  },
};

export function getDriverMeta(driverNumber: number): DriverMetadata {
  return (
    F1_DRIVERS_METADATA[driverNumber] || {
      number: driverNumber,
      code: `D${driverNumber}`,
      name: `Driver #${driverNumber}`,
      team: 'Formula Racing Team',
      teamColor: '#E10600',
    }
  );
}

export function getSessionMeta(sessionKey: number) {
  return (
    SESSION_METADATA[sessionKey] || {
      name: `Grand Prix Session #${sessionKey}`,
      circuit: 'FIA Championship Circuit',
      country: 'FIA Calendar',
      year: 2024,
      defaultRaceLength: 52,
    }
  );
}

