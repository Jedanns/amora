export type QuestStatus = 'active' | 'completed' | 'failed' | 'available' | 'abandoned';

export interface Quest {
  id: string;
  name: string;
  description: string;
  status: QuestStatus;
  level?: number;
  xp_reward?: number;
  reward_text?: string;
  objectives?: QuestObjective[];
  progress?: number;
  notes?: QuestNote[];
  bookmarked?: boolean;
}

export interface QuestObjective {
  id: string;
  description: string;
  current: number;
  target: number;
  completed: boolean;
}

export interface QuestNote {
  source: string;
  text: string;
}

export interface Rumor {
  id: string;
  name: string;
  description: string;
  level: number;
  xp_reward: number;
  bookmarked?: boolean;
  source?: string;
}
