import { type CSSProperties, useState, useCallback } from 'react';
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

type SubTab = 'inventaire' | 'spellbook';
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

const ARMOR_SLOT_ICONS: Record<string, string> = {
  head: '\u{1F451}',
  chest: '\u{1F6E1}',
  arms: '\u{1F9E4}',
  legs: '\u{1F462}',
  cape: '\u{1F9E3}',
};

const ARMOR_SLOT_ORDER = ['head', 'chest', 'arms', 'legs', 'cape'] as const;

// --- Styles ---

const containerStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  height: '100%',
  backgroundColor: '#0a0a0f',
  color: '#e8e8f0',
  fontFamily: 'inherit',
  fontSize: 13,
  overflow: 'hidden',
};

const scrollAreaStyle: CSSProperties = {
  flex: 1,
  overflowY: 'auto',
  overflowX: 'hidden',
  padding: '0 10px 16px',
};

const toggleBarStyle: CSSProperties = {
  display: 'flex',
  gap: 0,
  padding: '10px 10px 0',
};

function toggleBtnStyle(active: boolean): CSSProperties {
  return {
    flex: 1,
    padding: '7px 0',
    fontSize: 11,
    fontWeight: 700,
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    border: '1px solid',
    borderColor: active ? '#c9a84c' : '#2a2a3a',
    backgroundColor: active ? '#c9a84c' : 'transparent',
    color: active ? '#0a0a0f' : '#9898a8',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    fontFamily: 'inherit',
    borderRadius: 0,
  };
}

const statsGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: '1fr 1fr',
  gap: 6,
  margin: '10px 0',
};

function statCellStyle(): CSSProperties {
  return {
    backgroundColor: '#151520',
    border: '1px solid #2a2a3a',
    borderRadius: 6,
    padding: '8px 10px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 2,
  };
}

const statLabelStyle: CSSProperties = {
  fontSize: 9,
  fontWeight: 700,
  letterSpacing: '0.1em',
  color: '#9898a8',
  textTransform: 'uppercase',
};

function statValueStyle(color: string): CSSProperties {
  return {
    fontSize: 20,
    fontWeight: 800,
    color,
    lineHeight: 1.1,
  };
}

const statSubStyle: CSSProperties = {
  fontSize: 10,
  color: '#6a6a7a',
};

function sectionHeaderStyle(): CSSProperties {
  return {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '8px 10px',
    backgroundColor: '#1a1a28',
    borderLeft: '3px solid #c9a84c',
    borderRadius: '0 6px 6px 0',
    marginTop: 14,
    marginBottom: 8,
  };
}

const sectionTitleStyle: CSSProperties = {
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: '0.08em',
  color: '#c9a84c',
  textTransform: 'uppercase',
  flex: 1,
};

const sectionIconStyle: CSSProperties = {
  fontSize: 14,
};

function weaponSlotStyle(hasItem: boolean, hovered: boolean): CSSProperties {
  return {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '8px 10px',
    backgroundColor: hasItem ? '#151520' : 'transparent',
    border: hasItem ? '1px solid #2a2a3a' : '1px dashed #2a2a3a',
    borderLeft: hasItem ? '3px solid #8b7340' : '1px dashed #2a2a3a',
    borderRadius: 6,
    minHeight: 44,
    cursor: hasItem ? 'default' : 'default',
    transition: 'all 0.15s ease',
    opacity: hovered && hasItem ? 0.9 : 1,
    position: 'relative',
  };
}

const weaponSlotsRowStyle: CSSProperties = {
  display: 'flex',
  gap: 6,
  marginBottom: 6,
};

function armorSlotStyle(hasItem: boolean, hovered: boolean): CSSProperties {
  return {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 3,
    padding: '6px 4px',
    backgroundColor: hasItem ? '#151520' : 'transparent',
    border: hasItem ? '1px solid #2a2a3a' : '1px dashed #2a2a3a',
    borderRadius: 6,
    minHeight: 56,
    cursor: hasItem ? 'default' : 'default',
    transition: 'all 0.15s ease',
    opacity: hovered && hasItem ? 0.9 : 1,
    position: 'relative',
  };
}

const armorSlotsRowStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(5, 1fr)',
  gap: 4,
};

function itemCardStyle(hovered: boolean): CSSProperties {
  return {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '8px 10px',
    backgroundColor: hovered ? '#1a1a28' : '#151520',
    borderLeft: '3px solid #8b7340',
    borderRadius: 6,
    marginBottom: 4,
    transition: 'background-color 0.15s ease',
    cursor: 'pointer',
  };
}

function actionBtnStyle(color: string, hovered: boolean): CSSProperties {
  return {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: 24,
    height: 24,
    borderRadius: 4,
    border: `1px solid ${color}`,
    backgroundColor: hovered ? `${color}30` : 'transparent',
    color,
    fontSize: 14,
    fontWeight: 700,
    cursor: 'pointer',
    transition: 'all 0.15s ease',
    fontFamily: 'inherit',
    lineHeight: 1,
    padding: 0,
    flexShrink: 0,
  };
}

function unequipBtnStyle(hovered: boolean): CSSProperties {
  return {
    position: 'absolute' as const,
    top: 3,
    right: 3,
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: 16,
    height: 16,
    borderRadius: 3,
    border: '1px solid #e94560',
    backgroundColor: hovered ? 'rgba(233, 69, 96, 0.2)' : 'transparent',
    color: '#e94560',
    fontSize: 10,
    fontWeight: 700,
    cursor: 'pointer',
    transition: 'all 0.15s ease',
    fontFamily: 'inherit',
    lineHeight: 1,
    padding: 0,
  };
}

const emptySlotTextStyle: CSSProperties = {
  fontSize: 11,
  color: '#4a4a5a',
  fontStyle: 'italic',
};

const emptySlotIconStyle: CSSProperties = {
  fontSize: 16,
  color: '#3a3a4a',
};

const filterSelectStyle: CSSProperties = {
  backgroundColor: '#151520',
  border: '1px solid #2a2a3a',
  borderRadius: 4,
  color: '#9898a8',
  fontSize: 10,
  padding: '2px 6px',
  fontFamily: 'inherit',
  cursor: 'pointer',
  outline: 'none',
};

const chevronStyle: CSSProperties = {
  fontSize: 10,
  color: '#6a6a7a',
  transition: 'transform 0.2s ease',
  flexShrink: 0,
  userSelect: 'none',
};

const useBtnStyle = (hovered: boolean): CSSProperties => ({
  padding: '3px 10px',
  fontSize: 10,
  fontWeight: 700,
  letterSpacing: '0.05em',
  textTransform: 'uppercase',
  border: '1px solid #c9a84c',
  borderRadius: 4,
  backgroundColor: hovered ? 'rgba(201, 168, 76, 0.2)' : 'transparent',
  color: '#c9a84c',
  cursor: 'pointer',
  transition: 'all 0.15s ease',
  fontFamily: 'inherit',
  whiteSpace: 'nowrap',
  flexShrink: 0,
});

const expandedDescStyle: CSSProperties = {
  fontSize: 11,
  color: '#8a8a9a',
  padding: '6px 10px 4px 14px',
  lineHeight: 1.5,
};

// --- Sub-components ---

function HoverButton({
  styleFn,
  onClick,
  children,
  title,
}: {
  styleFn: (hovered: boolean) => CSSProperties;
  onClick: () => void;
  children: React.ReactNode;
  title?: string;
}) {
  const [hovered, setHovered] = useState(false);
  return (
    <button
      style={styleFn(hovered)}
      onClick={(e) => { e.stopPropagation(); onClick(); }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      title={title}
    >
      {children}
    </button>
  );
}

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
  const [hovered, setHovered] = useState(false);

  return (
    <div
      style={weaponSlotStyle(!!item, hovered)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {item ? (
        <>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#e8e8f0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {item.name}
            </div>
            <div style={{ fontSize: 10, color: '#6a6a7a' }}>{label}</div>
          </div>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#e94560', flexShrink: 0 }}>
            {item.damage_dice ?? '—'}
          </div>
          {onUnequip && (
            <HoverButton
              styleFn={(h) => unequipBtnStyle(h)}
              onClick={() => onUnequip(slotKey)}
              title="Desequiper"
            >
              ✕
            </HoverButton>
          )}
        </>
      ) : (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, width: '100%' }}>
          <span style={emptySlotIconStyle}>{slotKey === 'main_hand' ? '\u2694' : '\u{1F6E1}'}</span>
          <div>
            <div style={emptySlotTextStyle}>Emplacement Vide</div>
            <div style={{ fontSize: 9, color: '#3a3a4a' }}>{label}</div>
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
  const [hovered, setHovered] = useState(false);
  const label = SLOT_LABELS[slotKey as keyof typeof SLOT_LABELS] ?? slotKey;
  const icon = ARMOR_SLOT_ICONS[slotKey] ?? '\u{1F6E1}';

  return (
    <div
      style={armorSlotStyle(!!item, hovered)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {item ? (
        <>
          <div style={{ fontSize: 10, fontWeight: 600, color: '#e8e8f0', textAlign: 'center', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', width: '100%', lineHeight: 1.2 }}>
            {item.name}
          </div>
          <div style={{ fontSize: 10, color: '#4a9eff', fontWeight: 700 }}>
            +{item.armor_bonus ?? 0} CA
          </div>
          {onUnequip && (
            <HoverButton
              styleFn={(h) => unequipBtnStyle(h)}
              onClick={() => onUnequip(slotKey)}
              title="Desequiper"
            >
              ✕
            </HoverButton>
          )}
        </>
      ) : (
        <>
          <span style={emptySlotIconStyle}>{icon}</span>
          <div style={{ fontSize: 9, color: '#4a4a5a' }}>{label}</div>
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
  const [hovered, setHovered] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const rarityColor = RARITY_COLORS[item.rarity];
  const rarityLabel = RARITY_LABELS[item.rarity];
  const isConsumable = item.type === 'consumable';
  const isWeapon = item.type === 'weapon';
  const healColor = HEAL_TYPE_COLORS[item.heal_type ?? 'health'] ?? '#e5853a';

  return (
    <div>
      <div
        style={itemCardStyle(hovered)}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        onClick={() => setExpanded(!expanded)}
      >
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: '#e8e8f0' }}>
              {item.name}
            </span>
            {item.quantity > 1 && (
              <span style={{ fontSize: 10, color: '#6a6a7a' }}>x{item.quantity}</span>
            )}
            <span style={{ ...chevronStyle, transform: expanded ? 'rotate(90deg)' : 'rotate(0deg)' }}>
              &#9656;
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 2 }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: rarityColor, flexShrink: 0 }} />
            <span style={{ fontSize: 10, color: rarityColor }}>{rarityLabel}</span>
            {item.slot && (
              <>
                <span style={{ color: '#3a3a4a' }}>|</span>
                <span style={{ fontSize: 10, color: '#6a6a7a' }}>
                  {SLOT_LABELS[item.slot as keyof typeof SLOT_LABELS] ?? item.slot}
                </span>
              </>
            )}
            {isConsumable && item.heal_type && (
              <span style={{
                fontSize: 9,
                fontWeight: 700,
                padding: '1px 6px',
                borderRadius: 3,
                backgroundColor: `${healColor}20`,
                border: `1px solid ${healColor}40`,
                color: healColor,
                textTransform: 'capitalize',
              }}>
                {item.heal_type}
              </span>
            )}
            <span style={{ color: '#3a3a4a' }}>|</span>
            <span style={{ fontSize: 10, color: '#c9a84c' }}>{item.value} cr</span>
          </div>
        </div>

        {isWeapon && item.damage_dice && (
          <span style={{ fontSize: 13, fontWeight: 700, color: '#e94560', flexShrink: 0, marginRight: 4 }}>
            {item.damage_dice}
          </span>
        )}

        {!isWeapon && !isConsumable && item.armor_bonus != null && (
          <span style={{ fontSize: 13, fontWeight: 700, color: '#4a9eff', flexShrink: 0, marginRight: 4 }}>
            +{item.armor_bonus} CA
          </span>
        )}

        {isConsumable && item.heal_percent != null && (
          <span style={{ fontSize: 11, fontWeight: 600, color: healColor, flexShrink: 0, marginRight: 4 }}>
            +{item.heal_percent}%
          </span>
        )}

        <div style={{ display: 'flex', gap: 4, flexShrink: 0, alignItems: 'center' }}>
          {isConsumable && onUse && (
            <HoverButton
              styleFn={(h) => useBtnStyle(h)}
              onClick={() => onUse(item.id)}
              title="Utiliser"
            >
              Use
            </HoverButton>
          )}
          {!isConsumable && onEquip && (
            <HoverButton
              styleFn={(h) => actionBtnStyle('#53d769', h)}
              onClick={() => onEquip(item.id)}
              title="Equiper"
            >
              +
            </HoverButton>
          )}
          {onDrop && (
            <HoverButton
              styleFn={(h) => actionBtnStyle('#e94560', h)}
              onClick={() => onDrop(item.id)}
              title="Jeter"
            >
              −
            </HoverButton>
          )}
        </div>
      </div>

      {expanded && item.description && (
        <div style={expandedDescStyle}>{item.description}</div>
      )}
    </div>
  );
}

// --- Main component ---

function InventoryTab({
  inventory,
  onEquip,
  onUnequip,
  onUseItem,
  onDropItem,
}: InventoryTabProps) {
  const [subTab, setSubTab] = useState<SubTab>('inventaire');
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
    <div style={containerStyle}>
      {/* Tab toggle */}
      <div style={toggleBarStyle}>
        <button
          style={{
            ...toggleBtnStyle(subTab === 'inventaire'),
            borderRadius: '6px 0 0 6px',
          }}
          onClick={() => setSubTab('inventaire')}
        >
          Inventaire
        </button>
        <button
          style={{
            ...toggleBtnStyle(subTab === 'spellbook'),
            borderRadius: '0 6px 6px 0',
            borderLeft: 'none',
          }}
          onClick={() => setSubTab('spellbook')}
        >
          Spellbook
        </button>
      </div>

      {subTab === 'inventaire' ? (
        <div style={scrollAreaStyle}>
          {/* Quick stats grid */}
          <div style={statsGridStyle}>
            <div style={statCellStyle()}>
              <span style={statLabelStyle}>Crowns</span>
              <span style={statValueStyle('#c9a84c')}>{inventory.crowns}</span>
            </div>
            <div style={statCellStyle()}>
              <span style={statLabelStyle}>CA</span>
              <span style={statValueStyle('#4a9eff')}>{inventory.armor_class}</span>
            </div>
            <div style={statCellStyle()}>
              <span style={statLabelStyle}>Degats</span>
              <span style={statValueStyle('#e94560')}>{inventory.total_damage}</span>
            </div>
            <div style={statCellStyle()}>
              <span style={statLabelStyle}>Bonus</span>
              <span style={statValueStyle('#53d769')}>
                +{inventory.weapon_bonus}
              </span>
              <span style={statSubStyle}>{handLabel}</span>
            </div>
          </div>

          {/* EQUIPE section */}
          <div style={sectionHeaderStyle()}>
            <span style={sectionIconStyle}>{'\u2699'}</span>
            <span style={sectionTitleStyle}>Equipe</span>
          </div>

          {/* Weapon slots */}
          <div style={weaponSlotsRowStyle}>
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
          <div style={armorSlotsRowStyle}>
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
          <div style={sectionHeaderStyle()}>
            <span style={sectionIconStyle}>{'\u2694'}</span>
            <span style={sectionTitleStyle}>Armes</span>
            <select
              style={filterSelectStyle}
              value={weaponFilter}
              onChange={handleWeaponFilterChange}
            >
              <option value="all">Tous</option>
              <option value="one_hand">1 Main</option>
              <option value="two_hand">2 Mains</option>
            </select>
          </div>

          {filteredWeapons.length === 0 ? (
            <div style={{ padding: '12px 10px', fontSize: 11, color: '#4a4a5a', fontStyle: 'italic' }}>
              Aucune arme
            </div>
          ) : (
            filteredWeapons.map((item) => (
              <ItemCard
                key={item.id}
                item={item}
                onEquip={onEquip}
                onDrop={onDropItem}
              />
            ))
          )}

          {/* ARMURE section */}
          <div style={sectionHeaderStyle()}>
            <span style={sectionIconStyle}>{'\u{1F6E1}'}</span>
            <span style={sectionTitleStyle}>Armure</span>
          </div>

          {inventory.armors.length === 0 ? (
            <div style={{ padding: '12px 10px', fontSize: 11, color: '#4a4a5a', fontStyle: 'italic' }}>
              Aucune armure
            </div>
          ) : (
            inventory.armors.map((item) => (
              <ItemCard
                key={item.id}
                item={item}
                onEquip={onEquip}
                onDrop={onDropItem}
              />
            ))
          )}

          {/* CONSUMABLES section */}
          <div style={sectionHeaderStyle()}>
            <span style={sectionIconStyle}>{'\u2728'}</span>
            <span style={sectionTitleStyle}>Consumables</span>
          </div>

          {inventory.consumables.length === 0 ? (
            <div style={{ padding: '12px 10px', fontSize: 11, color: '#4a4a5a', fontStyle: 'italic' }}>
              Aucun consommable
            </div>
          ) : (
            inventory.consumables.map((item) => (
              <ItemCard
                key={item.id}
                item={item}
                onUse={onUseItem}
                onDrop={onDropItem}
              />
            ))
          )}
        </div>
      ) : (
        <div style={{
          ...scrollAreaStyle,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          <div style={{ textAlign: 'center', color: '#4a4a5a' }}>
            <div style={{ fontSize: 32, marginBottom: 8 }}>{'\u{1F4D6}'}</div>
            <div style={{ fontSize: 13, fontWeight: 600 }}>Spellbook</div>
            <div style={{ fontSize: 11, marginTop: 4, fontStyle: 'italic' }}>
              Bientot disponible...
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default InventoryTab;
