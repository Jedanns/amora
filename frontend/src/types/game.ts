export interface Campaign {
  session_id: string;
  name: string;
  created_at?: string;
  updated_at?: string;
  last_played?: string;
  character_name?: string;
  character_class?: string;
  turn?: number;
  location?: string;
  active_character_id?: string | null;
  version?: number;
}

export interface GameState {
  session_id: string;
  turn: number;
  combat_active: boolean;
  location: string;
  active_character_id?: string | null;
  flags?: Record<string, unknown>;
  version?: number;
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
  id?: string;
  type?: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: string;
  metadata?: Record<string, unknown>;
  actions?: GameAction[];
}

export interface StreamChunk {
  type: 'chunk';
  text: string;
}

export interface StreamComplete {
  type: 'complete';
  narrative: string;
  actions: GameAction[];
  state: GameState;
}

export type StreamMessage = StreamChunk | StreamComplete | { type: 'error'; error: string };
