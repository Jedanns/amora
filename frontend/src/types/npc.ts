export type Disposition =
  | 'Friendly'
  | 'Curious'
  | 'Guarded'
  | 'Hostile'
  | 'Neutral'
  | 'Fearful';

export interface NpcRelationship {
  id: string;
  name: string;
  title?: string;
  portrait?: string;
  disposition: Disposition;
  relationship_level: number;
  max_relationship: number;
  is_dead: boolean;
  notes?: string;
}

export const DISPOSITION_COLORS: Record<Disposition, string> = {
  Friendly: '#53d769',
  Curious: '#c9a84c',
  Guarded: '#e84393',
  Hostile: '#e94560',
  Neutral: '#9898a8',
  Fearful: '#b06aff',
};
