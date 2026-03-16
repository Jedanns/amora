import type { Campaign, GameState, GameResponse, DiceResult } from '@/types/game';
import type { Character } from '@/types/character';

const BASE_URL = '';

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

export const api = {
  llm: {
    health: () => request<{ healthy: boolean; model?: string; message?: string }>('GET', '/api/llm/health'),
  },

  game: {
    createSession: (name: string) =>
      request<Campaign>('POST', '/api/game/session', { name }),

    sendInput: (sessionId: string, message: string) =>
      request<GameResponse>('POST', `/api/game/session/${sessionId}/input`, { message }),

    rollDice: (sessionId: string, notation: string, reason?: string) =>
      request<DiceResult>('POST', `/api/game/session/${sessionId}/roll`, { notation, reason }),

    advanceTurn: (sessionId: string) =>
      request<GameState>('POST', `/api/game/session/${sessionId}/advance-turn`),

    save: (sessionId: string) =>
      request<void>('POST', `/api/game/session/${sessionId}/save`),
  },

  character: {
    create: (data: { name: string; character_class: string; player_id: string }) =>
      request<Character>('POST', '/api/character', data),

    get: (id: string) =>
      request<Character>('GET', `/api/character/${id}`),

    getInventory: (id: string) =>
      request<{ items: { name: string; quantity: number }[] }>('GET', `/api/character/${id}/inventory`),
  },
};
