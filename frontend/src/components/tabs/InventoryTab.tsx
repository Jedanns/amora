import { useState, useCallback } from 'react';
import {
  Crown, Shield, Hand, Footprints, Shirt,
  Sword, ShieldHalf, Settings, Sparkles, ChevronRight,
  Plus, Minus, X,
} from 'lucide-react';
import type { Item, EquipmentSlots } from '../../types/inventory';
import { RARITY_COLORS, SLOT_LABELS } from '../../types/inventory';

interface InventoryTabProps {
  inventory: {
    crowns: number;
    armor_class: number;
    total_damage: string;
    weapon_bonus: number;
    equipment: EquipmentSlots;
    weapons: Item[];
    armors: Item[];
    consumables: Item[];
  };
  onEquip?: (itemId: string) => void;
  onUnequip?: (slot: string) => void;
  onUseItem?: (itemId: string) => void;
  onDropItem?: (itemId: string) => void;
}

type WeaponFilter = 'all' | 'one_hand' | 'two_hand';

const HEAL_TYPE_COLORS: Record<string, string> = {
  health: '#e5853a',
  mana: '#4a9eff',
};

const RARITY_LABELS: Record<Item['rarity'], string> = {
  common: 'Basique',
  uncommon: 'Ameliore',
  rare: 'Rare',
  epic: 'Epique',
  legendary: 'Legendaire',
};

const ARMOR_SLOT_ICONS: Record<string, React.ComponentType<{ size?: number; className?: string }>> = {
  head: Crown,
  chest: Shirt,
  arms: Hand,
  legs: Footprints,
  cape: ShieldHalf,
};

const ARMOR_SLOT_ORDER = ['head', 'chest', 'arms', 'legs', 'cape'] as const;

function WeaponSlot({
  item,
  label,
  slotKey,
  onUnequip,
}: {
  item: Item | null;
  label: string;
  slotKey: string;
  onUnequip?: (slot: string) => void;
}) {
  return (
    <div
      className={`flex-1 flex items-center gap-2 px-2.5 py-2 rounded-md min-h-[44px] relative transition-all duration-150 ${
        item
          ? 'bg-bg-panel border border-border-primary border-l-[3px] border-l-border-gold hover:opacity-90'
          : 'bg-transparent border border-dashed border-border-primary'
      }`}
    >
      {item ? (
        <>
          <div className="flex-1 min-w-0">
            <div className="text-xs font-semibold text-text-primary overflow-hidden text-ellipsis whitespace-nowrap">
              {item.name}
            </div>
            <div className="text-[10px] text-text-dim">{label}</div>
          </div>
          <div className="text-xs font-bold text-red shrink-0">
            {item.damage_dice ?? '—'}
          </div>
          {onUnequip && (
            <button
              className="absolute top-[3px] right-[3px] inline-flex items-center justify-center w-4 h-4 rounded-[3px] border border-red bg-transparent text-red hover:bg-red/20 cursor-pointer transition-all duration-150 p-0"
              onClick={(e) => { e.stopPropagation(); onUnequip(slotKey); }}
              title="Desequiper"
            >
              <X size={10} />
            </button>
          )}
        </>
      ) : (
        <div className="flex items-center gap-1.5 w-full">
          {slotKey === 'main_hand' ? (
            <Sword size={16} className="text-[#3a3a4a] shrink-0" />
          ) : (
            <Shield size={16} className="text-[#3a3a4a] shrink-0" />
          )}
          <div>
            <div className="text-[11px] text-[#4a4a5a] italic">Emplacement Vide</div>
            <div className="text-[9px] text-[#3a3a4a]">{label}</div>
          </div>
        </div>
      )}
    </div>
  );
}

function ArmorSlot({
  item,
  slotKey,
  onUnequip,
}: {
  item: Item | null;
  slotKey: string;
  onUnequip?: (slot: string) => void;
}) {
  const label = SLOT_LABELS[slotKey as keyof typeof SLOT_LABELS] ?? slotKey;
  const SlotIcon = ARMOR_SLOT_ICONS[slotKey] ?? Shield;

  return (
    <div
      className={`flex-1 flex flex-col items-center gap-[3px] px-1 py-1.5 rounded-md min-h-[56px] relative transition-all duration-150 ${
        item
          ? 'bg-bg-panel border border-border-primary hover:opacity-90'
          : 'bg-transparent border border-dashed border-border-primary'
      }`}
    >
      {item ? (
        <>
          <div className="text-[10px] font-semibold text-text-primary text-center overflow-hidden text-ellipsis whitespace-nowrap w-full leading-tight">
            {item.name}
          </div>
          <div className="text-[10px] text-blue font-bold">
            +{item.armor_bonus ?? 0} CA
          </div>
          {onUnequip && (
            <button
              className="absolute top-[3px] right-[3px] inline-flex items-center justify-center w-4 h-4 rounded-[3px] border border-red bg-transparent text-red hover:bg-red/20 cursor-pointer transition-all duration-150 p-0"
              onClick={(e) => { e.stopPropagation(); onUnequip(slotKey); }}
              title="Desequiper"
            >
              <X size={10} />
            </button>
          )}
        </>
      ) : (
        <>
          <SlotIcon size={16} className="text-[#3a3a4a]" />
          <div className="text-[9px] text-[#4a4a5a]">{label}</div>
        </>
      )}
    </div>
  );
}

function ItemCard({
  item,
  onEquip,
  onDrop,
  onUse,
}: {
  item: Item;
  onEquip?: (id: string) => void;
  onDrop?: (id: string) => void;
  onUse?: (id: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const rarityColor = RARITY_COLORS[item.rarity];
  const rarityLabel = RARITY_LABELS[item.rarity];
  const isConsumable = item.type === 'consumable';
  const isWeapon = item.type === 'weapon';
  const healColor = HEAL_TYPE_COLORS[item.heal_type ?? 'health'] ?? '#e5853a';

  return (
    <div>
      <div
        className="flex items-center gap-2 px-2.5 py-2 bg-bg-panel border-l-[3px] border-l-border-gold rounded-md mb-1 transition-colors duration-150 cursor-pointer hover:bg-bg-card"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="text-[13px] font-semibold text-text-primary">{item.name}</span>
            {item.quantity > 1 && (
              <span className="text-[10px] text-text-dim">x{item.quantity}</span>
            )}
            <ChevronRight
              size={10}
              className={`text-text-dim shrink-0 transition-transform duration-200 ${expanded ? 'rotate-90' : ''}`}
            />
          </div>
          <div className="flex items-center gap-1.5 mt-0.5">
            <span
              className="w-1.5 h-1.5 rounded-full shrink-0"
              style={{ backgroundColor: rarityColor }}
            />
            <span className="text-[10px]" style={{ color: rarityColor }}>{rarityLabel}</span>
            {item.slot && (
              <>
                <span className="text-[#3a3a4a]">|</span>
                <span className="text-[10px] text-text-dim">
                  {SLOT_LABELS[item.slot as keyof typeof SLOT_LABELS] ?? item.slot}
                </span>
              </>
            )}
            {isConsumable && item.heal_type && (
              <span
                className="text-[9px] font-bold px-1.5 py-px rounded-[3px] capitalize"
                style={{
                  backgroundColor: `${healColor}20`,
                  border: `1px solid ${healColor}40`,
                  color: healColor,
                }}
              >
                {item.heal_type}
              </span>
            )}
            <span className="text-[#3a3a4a]">|</span>
            <span className="text-[10px] text-gold">{item.value} cr</span>
          </div>
        </div>

        {isWeapon && item.damage_dice && (
          <span className="text-[13px] font-bold text-red shrink-0 mr-1">{item.damage_dice}</span>
        )}

        {!isWeapon && !isConsumable && item.armor_bonus != null && (
          <span className="text-[13px] font-bold text-blue shrink-0 mr-1">+{item.armor_bonus} CA</span>
        )}

        {isConsumable && item.heal_percent != null && (
          <span className="text-[11px] font-semibold shrink-0 mr-1" style={{ color: healColor }}>
            +{item.heal_percent}%
          </span>
        )}

        <div className="flex gap-1 shrink-0 items-center">
          {isConsumable && onUse && (
            <button
              className="px-2.5 py-[3px] text-[10px] font-bold tracking-[0.05em] uppercase border border-gold rounded-sm bg-transparent text-gold hover:bg-gold/20 cursor-pointer transition-all duration-150 whitespace-nowrap shrink-0"
              onClick={(e) => { e.stopPropagation(); onUse(item.id); }}
              title="Utiliser"
            >
              Use
            </button>
          )}
          {!isConsumable && onEquip && (
            <button
              className="inline-flex items-center justify-center w-6 h-6 rounded-sm border border-green bg-transparent text-green hover:bg-green/20 cursor-pointer transition-all duration-150 p-0 shrink-0"
              onClick={(e) => { e.stopPropagation(); onEquip(item.id); }}
              title="Equiper"
            >
              <Plus size={14} />
            </button>
          )}
          {onDrop && (
            <button
              className="inline-flex items-center justify-center w-6 h-6 rounded-sm border border-red bg-transparent text-red hover:bg-red/20 cursor-pointer transition-all duration-150 p-0 shrink-0"
              onClick={(e) => { e.stopPropagation(); onDrop(item.id); }}
              title="Jeter"
            >
              <Minus size={14} />
            </button>
          )}
        </div>
      </div>

      {expanded && item.description && (
        <div className="text-[11px] text-text-secondary px-2.5 pt-1.5 pb-1 pl-3.5 leading-normal">
          {item.description}
        </div>
      )}
    </div>
  );
}

function InventoryTab({
  inventory,
  onEquip,
  onUnequip,
  onUseItem,
  onDropItem,
}: InventoryTabProps) {
  const [weaponFilter, setWeaponFilter] = useState<WeaponFilter>('all');

  const filteredWeapons = inventory.weapons.filter((w) => {
    if (weaponFilter === 'all') return true;
    return w.weapon_hand === weaponFilter;
  });

  const handleWeaponFilterChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      setWeaponFilter(e.target.value as WeaponFilter);
    },
    [],
  );

  const handLabel =
    inventory.equipment.main_hand?.weapon_hand === 'two_hand'
      ? '2 mains'
      : '1 main';

  return (
    <div className="flex flex-col h-full bg-bg-primary text-text-primary text-[13px] overflow-hidden">
      <div className="flex-1 overflow-y-auto overflow-x-hidden px-2.5 pb-4">
        {/* Quick stats grid */}
        <div className="grid grid-cols-2 gap-1.5 my-2.5">
          <div className="bg-bg-panel border border-border-primary rounded-md px-2.5 py-2 flex flex-col items-center gap-0.5">
            <span className="text-[9px] font-bold tracking-[0.1em] uppercase text-text-secondary">Crowns</span>
            <span className="text-xl font-extrabold text-gold leading-none">{inventory.crowns}</span>
          </div>
          <div className="bg-bg-panel border border-border-primary rounded-md px-2.5 py-2 flex flex-col items-center gap-0.5">
            <span className="text-[9px] font-bold tracking-[0.1em] uppercase text-text-secondary">CA</span>
            <span className="text-xl font-extrabold text-blue leading-none">{inventory.armor_class}</span>
          </div>
          <div className="bg-bg-panel border border-border-primary rounded-md px-2.5 py-2 flex flex-col items-center gap-0.5">
            <span className="text-[9px] font-bold tracking-[0.1em] uppercase text-text-secondary">Degats</span>
            <span className="text-xl font-extrabold text-red leading-none">{inventory.total_damage}</span>
          </div>
          <div className="bg-bg-panel border border-border-primary rounded-md px-2.5 py-2 flex flex-col items-center gap-0.5">
            <span className="text-[9px] font-bold tracking-[0.1em] uppercase text-text-secondary">Bonus</span>
            <span className="text-xl font-extrabold text-green leading-none">+{inventory.weapon_bonus}</span>
            <span className="text-[10px] text-text-dim">{handLabel}</span>
          </div>
        </div>

        {/* EQUIPE section */}
        <div className="flex items-center gap-2 px-2.5 py-2 bg-bg-card border-l-[3px] border-l-gold rounded-r-md mt-3.5 mb-2">
          <Settings size={14} className="text-gold shrink-0" />
          <span className="text-[11px] font-bold tracking-[0.08em] uppercase text-gold flex-1">Equipe</span>
        </div>

        {/* Weapon slots */}
        <div className="flex gap-1.5 mb-1.5">
          <WeaponSlot
            item={inventory.equipment.main_hand}
            label={SLOT_LABELS.main_hand}
            slotKey="main_hand"
            onUnequip={onUnequip}
          />
          <WeaponSlot
            item={inventory.equipment.off_hand}
            label={SLOT_LABELS.off_hand}
            slotKey="off_hand"
            onUnequip={onUnequip}
          />
        </div>

        {/* Armor slots */}
        <div className="grid grid-cols-5 gap-1">
          {ARMOR_SLOT_ORDER.map((slot) => (
            <ArmorSlot
              key={slot}
              item={inventory.equipment[slot]}
              slotKey={slot}
              onUnequip={onUnequip}
            />
          ))}
        </div>

        {/* ARMES section */}
        <div className="flex items-center gap-2 px-2.5 py-2 bg-bg-card border-l-[3px] border-l-gold rounded-r-md mt-3.5 mb-2">
          <Sword size={14} className="text-gold shrink-0" />
          <span className="text-[11px] font-bold tracking-[0.08em] uppercase text-gold flex-1">Armes</span>
          <select
            className="bg-bg-panel border border-border-primary rounded-sm text-text-secondary text-[10px] px-1.5 py-0.5 cursor-pointer outline-none"
            value={weaponFilter}
            onChange={handleWeaponFilterChange}
          >
            <option value="all">Tous</option>
            <option value="one_hand">1 Main</option>
            <option value="two_hand">2 Mains</option>
          </select>
        </div>

        {filteredWeapons.length === 0 ? (
          <div className="py-3 px-2.5 text-[11px] text-[#4a4a5a] italic">Aucune arme</div>
        ) : (
          filteredWeapons.map((item) => (
            <ItemCard key={item.id} item={item} onEquip={onEquip} onDrop={onDropItem} />
          ))
        )}

        {/* ARMURE section */}
        <div className="flex items-center gap-2 px-2.5 py-2 bg-bg-card border-l-[3px] border-l-gold rounded-r-md mt-3.5 mb-2">
          <Shield size={14} className="text-gold shrink-0" />
          <span className="text-[11px] font-bold tracking-[0.08em] uppercase text-gold flex-1">Armure</span>
        </div>

        {inventory.armors.length === 0 ? (
          <div className="py-3 px-2.5 text-[11px] text-[#4a4a5a] italic">Aucune armure</div>
        ) : (
          inventory.armors.map((item) => (
            <ItemCard key={item.id} item={item} onEquip={onEquip} onDrop={onDropItem} />
          ))
        )}

        {/* CONSUMABLES section */}
        <div className="flex items-center gap-2 px-2.5 py-2 bg-bg-card border-l-[3px] border-l-gold rounded-r-md mt-3.5 mb-2">
          <Sparkles size={14} className="text-gold shrink-0" />
          <span className="text-[11px] font-bold tracking-[0.08em] uppercase text-gold flex-1">Consumables</span>
        </div>

        {inventory.consumables.length === 0 ? (
          <div className="py-3 px-2.5 text-[11px] text-[#4a4a5a] italic">Aucun consommable</div>
        ) : (
          inventory.consumables.map((item) => (
            <ItemCard key={item.id} item={item} onUse={onUseItem} onDrop={onDropItem} />
          ))
        )}
      </div>
    </div>
  );
}

export default InventoryTab;
