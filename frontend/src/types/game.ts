export interface Campaign {
  session_id: string;
  name: string;
  created_at?: string;
  last_played?: string;
  character_name?: string;
  character_class?: string;
  turn?: number;
}

export interface GameState {
  session_id: string;
  turn: number;
  combat_active: boolean;
  location: string;
  time_of_day?: string;
}

export interface GameResponse {
  narrative: string;
  actions?: GameAction[];
  state?: GameState;
  dice_rolls?: DiceResult[];
}

export interface GameAction {
  type: string;
  target: string;
  value?: string | number;
}

export interface DiceResult {
  notation: string;
  individual: number[];
  modifier: number;
  total: number;
  reason?: string;
}

export interface HistoryEntry {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: string;
  actions?: GameAction[];
}
