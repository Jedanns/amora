export type QuestStatus = 'active' | 'completed' | 'failed' | 'available';

export interface Quest {
  id: string;
  name: string;
  description: string;
  level: number;
  xp_reward: number;
  status: QuestStatus;
  reward_text?: string;
  objectives?: QuestObjective[];
  notes?: string[];
  bookmarked?: boolean;
}

export interface QuestObjective {
  description: string;
  completed: boolean;
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
