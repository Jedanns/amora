import type { Campaign, GameState, GameResponse, DiceResult, StreamMessage } from '@/types/game';
import type { Character } from '@/types/character';

const isDev = import.meta.env.DEV;
const BASE_URL = isDev ? '' : 'http://127.0.0.1:8000';

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const opts: RequestInit = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body) opts.body = JSON.stringify(body);

  const resp = await fetch(`${BASE_URL}${path}`, opts);
  if (resp.status === 204) return null as T;

  const data = await resp.json();
  if (!resp.ok) {
    throw new Error(data.detail || data.error || `HTTP ${resp.status}`);
  }
  return data as T;
}

export interface InventoryApiResponse {
  character_id: string;
  items: ApiItem[];
  total_weight: number;
  max_weight: number;
  used_slots: number;
  max_slots: number;
}

export interface ApiItem {
  id: string;
  name: string;
  description: string;
  item_type: string;
  rarity: string;
  quantity: number;
  weight: number;
  value: number;
}

export interface HistoryApiResponse {
  entries: HistoryApiEntry[];
  total: number;
}

export interface HistoryApiEntry {
  id: string;
  timestamp: string;
  type: string;
  content: string;
  metadata: Record<string, unknown>;
}

export interface QuestApiResponse {
  id: string;
  name: string;
  description: string;
  status: string;
  objectives: { id: string; description: string; current: number; target: number; completed: boolean }[];
  progress: number;
}

export const api = {
  llm: {
    health: () =>
      request<{ healthy: boolean; provider?: string; model?: string; message?: string }>(
        'GET',
        '/api/llm/health',
      ),
  },

  game: {
    listSessions: () =>
      request<Campaign[]>('GET', '/api/game/sessions'),

    createSession: (name: string) =>
      request<Campaign>('POST', '/api/game/session', { name }),

    getSession: (sessionId: string) =>
      request<GameState>('GET', `/api/game/session/${sessionId}`),

    deleteSession: (sessionId: string) =>
      request<void>('DELETE', `/api/game/session/${sessionId}`),

    sendInput: (sessionId: string, message: string, temperature?: number, maxTokens?: number) =>
      request<GameResponse>('POST', `/api/game/session/${sessionId}/input`, {
        message,
        ...(temperature !== undefined && { temperature }),
        ...(maxTokens !== undefined && { max_tokens: maxTokens }),
      }),

    rollDice: (sessionId: string, notation: string, reason?: string) =>
      request<DiceResult>('POST', `/api/game/session/${sessionId}/roll`, { notation, reason }),

    advanceTurn: (sessionId: string) =>
      request<GameState>('POST', `/api/game/session/${sessionId}/advance-turn`),

    rollback: (sessionId: string, steps: number = 1) =>
      request<GameState>('POST', `/api/game/session/${sessionId}/rollback?steps=${steps}`),

    save: (sessionId: string) =>
      request<void>('POST', `/api/game/session/${sessionId}/save`),

    getHistory: (sessionId: string, limit: number = 50) =>
      request<HistoryApiResponse>('GET', `/api/game/session/${sessionId}/history?limit=${limit}`),

    setActiveCharacter: (sessionId: string, characterId: string) =>
      request<GameState>(
        'POST',
        `/api/game/session/${sessionId}/set-character?character_id=${characterId}`,
      ),

    listQuests: (sessionId: string, status?: string) =>
      request<{ quests: QuestApiResponse[]; total: number }>(
        'GET',
        `/api/game/session/${sessionId}/quests${status ? `?status=${status}` : ''}`,
      ),
  },

  character: {
    create: (data: { name: string; character_class: string; player_id?: string }) =>
      request<Character>('POST', '/api/character', data),

    list: () =>
      request<{ characters: Character[]; total: number }>('GET', '/api/character'),

    get: (id: string) =>
      request<Character>('GET', `/api/character/${id}`),

    delete: (id: string) =>
      request<void>('DELETE', `/api/character/${id}`),

    damage: (id: string, amount: number) =>
      request<Character>('POST', `/api/character/${id}/damage`, { amount }),

    heal: (id: string, amount: number) =>
      request<Character>('POST', `/api/character/${id}/heal`, { amount }),

    addExperience: (id: string, amount: number) =>
      request<Character>('POST', `/api/character/${id}/experience`, { amount }),

    move: (id: string, location: string) =>
      request<Character>('POST', `/api/character/${id}/move`, { location }),

    getInventory: (id: string) =>
      request<InventoryApiResponse>('GET', `/api/character/${id}/inventory`),

    addItem: (id: string, item: {
      name: string;
      description?: string;
      item_type?: string;
      rarity?: string;
      quantity?: number;
      weight?: number;
      value?: number;
    }) =>
      request<ApiItem>('POST', `/api/character/${id}/inventory`, item),
  },

  lore: {
    list: () =>
      request<Array<{
        id: string;
        name: string;
        content: string;
        keys: string[];
        category: string;
        priority: number;
        enabled: boolean;
      }>>('GET', '/api/lore'),
  },
};

export function createGameStream(
  sessionId: string,
  onChunk: (text: string) => void,
  onComplete: (msg: StreamMessage & { type: 'complete' }) => void,
  onError: (error: string) => void,
): {
  send: (message: string) => void;
  close: () => void;
} {
  const wsUrl = isDev
    ? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/game/session/${sessionId}/stream`
    : `ws://127.0.0.1:8000/api/game/session/${sessionId}/stream`;
  const ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    // connection established
  };

  ws.onmessage = (event) => {
    try {
      const msg: StreamMessage = JSON.parse(event.data);
      if (msg.type === 'chunk') {
        onChunk(msg.text);
      } else if (msg.type === 'complete') {
        onComplete(msg as StreamMessage & { type: 'complete' });
      } else if (msg.type === 'error') {
        onError(msg.error);
      }
    } catch {
      onError('Failed to parse WebSocket message');
    }
  };

  ws.onerror = () => {
    onError('WebSocket connection error');
  };

  ws.onclose = (event) => {
    if (event.code !== 1000) {
      onError(`WebSocket closed: ${event.reason || `code ${event.code}`}`);
    }
  };

  return {
    send: (message: string) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ message }));
      }
    },
    close: () => {
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close(1000);
      }
    },
  };
}
