export type ItemType = 'weapon' | 'armor' | 'consumable' | 'quest' | 'misc';
export type ItemRarity = 'common' | 'uncommon' | 'rare' | 'epic' | 'legendary';
export type EquipSlot = 'main_hand' | 'off_hand' | 'head' | 'chest' | 'arms' | 'legs' | 'cape';
export type WeaponHand = 'one_hand' | 'two_hand';

export interface Item {
  id: string;
  name: string;
  type: ItemType;
  rarity: ItemRarity;
  description?: string;
  value: number;
  slot?: EquipSlot;
  weapon_hand?: WeaponHand;
  damage_dice?: string;
  armor_bonus?: number;
  heal_percent?: number;
  heal_type?: string;
  equipped?: boolean;
  quantity: number;
}

export interface EquipmentSlots {
  main_hand: Item | null;
  off_hand: Item | null;
  head: Item | null;
  chest: Item | null;
  arms: Item | null;
  legs: Item | null;
  cape: Item | null;
}

export interface Inventory {
  items: Item[];
  equipment: EquipmentSlots;
  crowns: number;
  armor_class: number;
  total_damage: string;
  weapon_bonus: number;
}

export const RARITY_COLORS: Record<ItemRarity, string> = {
  common: '#9898a8',
  uncommon: '#53d769',
  rare: '#4a9eff',
  epic: '#b06aff',
  legendary: '#c9a84c',
};

export const SLOT_LABELS: Record<EquipSlot, string> = {
  main_hand: 'Main 1',
  off_hand: 'Main 2',
  head: 'Tete',
  chest: 'Torse',
  arms: 'Bras',
  legs: 'Jambes',
  cape: 'Cape',
};
