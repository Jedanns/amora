export type CharacterClass =
  | 'warrior'
  | 'mage'
  | 'rogue'
  | 'cleric'
  | 'ranger'
  | 'bard'
  | 'paladin'
  | 'monk';

export interface CharacterAttributes {
  strength: number;
  dexterity: number;
  constitution: number;
  intelligence: number;
  wisdom: number;
  charisma: number;
}

export interface Character {
  id: string;
  name: string;
  character_class: CharacterClass;
  level: number;
  experience: number;
  hp_current: number;
  hp_max: number;
  mana_current: number;
  mana_max: number;
  attributes: CharacterAttributes;
  location: string;
  gold: number;
  armor_class: number;
}

export interface SkillEntry {
  name: string;
  modifier: number;
  current_xp: number;
  max_xp: number;
}

export interface SkillCategory {
  name: string;
  icon: string;
  color: string;
  skills: SkillEntry[];
}

export const CLASS_LABELS: Record<CharacterClass, string> = {
  warrior: 'Guerrier',
  mage: 'Mage',
  rogue: 'Voleur',
  cleric: 'Clerc',
  ranger: 'Ranger',
  bard: 'Barde',
  paladin: 'Paladin',
  monk: 'Moine',
};

export const DEFAULT_SKILL_CATEGORIES: SkillCategory[] = [
  {
    name: 'AVENTURIER',
    icon: 'sparkles',
    color: '#c9a84c',
    skills: [
      { name: 'Investigation', modifier: -1, current_xp: 1, max_xp: 2 },
      { name: 'Escalade', modifier: 1, current_xp: 0, max_xp: 4 },
      { name: 'Visee', modifier: -1, current_xp: 0, max_xp: 2 },
      { name: 'Maitrise des Betes', modifier: -3, current_xp: 0, max_xp: 2 },
    ],
  },
  {
    name: 'BRUTE',
    icon: 'swords',
    color: '#c9a84c',
    skills: [
      { name: 'Combat Rapproche', modifier: 5, current_xp: 0, max_xp: 12 },
      { name: 'A Distance', modifier: -2, current_xp: 0, max_xp: 2 },
      { name: 'Une Main', modifier: 6, current_xp: 0, max_xp: 10 },
      { name: 'Deux Mains', modifier: -2, current_xp: 0, max_xp: 2 },
    ],
  },
  {
    name: 'VOLEUR',
    icon: 'lock',
    color: '#c9a84c',
    skills: [
      { name: 'Acrobatie', modifier: 4, current_xp: 0, max_xp: 10 },
      { name: 'Prestidigitation', modifier: -1, current_xp: 0, max_xp: 2 },
      { name: 'Discretion', modifier: 2, current_xp: 0, max_xp: 6 },
      { name: 'Crochetage', modifier: -2, current_xp: 0, max_xp: 2 },
    ],
  },
  {
    name: 'SILVER TONGUE',
    icon: 'chat',
    color: '#c9a84c',
    skills: [
      { name: 'Tromperie', modifier: -1, current_xp: 0, max_xp: 2 },
      { name: 'Persuasion', modifier: -1, current_xp: 1, max_xp: 2 },
      { name: 'Representation', modifier: -3, current_xp: 0, max_xp: 2 },
      { name: 'Intimidation', modifier: 3, current_xp: 0, max_xp: 8 },
      { name: 'Seduction', modifier: -2, current_xp: 0, max_xp: 2 },
      { name: 'Negociation', modifier: -1, current_xp: 0, max_xp: 2 },
    ],
  },
];
