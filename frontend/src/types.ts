// PITWALL Data Types & Interfaces matching updated backend contracts

export interface SessionResponse {
  sessions: number[];
  count: number;
}

export interface DriversResponse {
  session_key: number;
  drivers: number[];
  count: number;
}

export interface OptimizeRequest {
  session_key: number;
  target_driver: number;
  decision_lap: number;
  race_length?: number;
  track_mode?: 'causal' | 'replay';
  pit_loss?: number;
  max_stops?: number;
  max_candidates?: number;
}

export interface StrategyItem {
  strategy_id: string;
  pit_sequence: [number, string][];
  pit_sequence_str: string;
  is_baseline: boolean;
  num_stops: number;
  projected_final_position: number;
  projected_cumulative_time_s: number;
  time_delta_vs_actual_s: number;
  positions_gained_vs_actual: number | null;
  ground_truth_available: boolean;
  description: string;
}

export interface LapReplayRecord {
  lap_number: number;
  driver_number: number;
  lap_duration: number;
  cum_time: number;
  position: number;
  gap_to_leader: number;
  gap_ahead: number;
  gap_behind: number;
  compound: string;
  tyre_age: number;
  is_target: boolean;
  ground_truth_available: boolean;
}

export interface BestReplaySummary {
  target_driver: number;
  decision_lap: number;
  race_length: number;
  ground_truth_available: boolean;
  final_position: number;
  final_cumulative_time: number;
  total_time_delta_vs_actual: number;
  positions_gained_vs_actual: number | null;
}

export interface OptimizationResponse {
  session_key: number;
  target_driver: number;
  decision_lap: number;
  race_length: number;
  track_mode: 'causal' | 'replay';
  model: {
    type: string;
    reference_age: number;
    degradation: Record<string, number>;
    r_squared: number;
  };
  recommendation: {
    strategy_id: string;
    strategy: StrategyItem;
    interpretation: string;
    objective: string;
  };
  ranking: StrategyItem[];
  best_replay: {
    summary: BestReplaySummary;
    laps_table: LapReplayRecord[];
  };
  projected_classification?: LapReplayRecord[];
}

export interface DriverMetadata {
  number: number;
  code: string;
  name: string;
  team: string;
  teamColor: string;
}

export type ActiveWorkspace = 'integrated_workspace' | 'dashboard' | 'strategy' | 'results' | 'replay' | 'whatif' | 'about';
