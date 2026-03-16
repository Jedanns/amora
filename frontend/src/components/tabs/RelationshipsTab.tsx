import { type CSSProperties, useState, useCallback, useMemo } from 'react';

type Disposition = 'Friendly' | 'Curious' | 'Guarded' | 'Hostile' | 'Neutral' | 'Fearful';

interface NpcRelationship {
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

interface RelationshipsTabProps {
  relationships: NpcRelationship[];
  onSelectNpc?: (id: string) => void;
}

const DISPOSITION_COLORS: Record<Disposition, string> = {
  Friendly: '#53d769',
  Curious: '#c9a84c',
  Guarded: '#e84393',
  Hostile: '#e94560',
  Neutral: '#9898a8',
  Fearful: '#b06aff',
};

function hexToRgba(hex: string, alpha: number): string {
  const cleaned = hex.replace('#', '');
  const r = parseInt(cleaned.substring(0, 2), 16);
  const g = parseInt(cleaned.substring(2, 4), 16);
  const b = parseInt(cleaned.substring(4, 6), 16);
  if (isNaN(r) || isNaN(g) || isNaN(b)) return hex;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    overflow: 'hidden',
  } satisfies CSSProperties,

  toggleRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 0,
    padding: '10px 10px 0',
    flexShrink: 0,
  } satisfies CSSProperties,

  toggleButton: (active: boolean, hovered: boolean): CSSProperties => ({
    flex: 1,
    padding: '7px 12px',
    fontSize: 11,
    fontWeight: 700,
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    fontFamily: 'inherit',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    border: '1px solid',
    userSelect: 'none',
    lineHeight: 1.4,
    backgroundColor: active
      ? 'rgba(201, 168, 76, 0.12)'
      : hovered
        ? '#252535'
        : 'transparent',
    borderColor: active ? '#c9a84c' : '#2a2a3a',
    color: active ? '#c9a84c' : hovered ? '#e8e8f0' : '#9898a8',
    boxShadow: active ? '0 0 8px rgba(201, 168, 76, 0.15)' : 'none',
  }),

  toggleLeft: {
    borderRadius: '6px 0 0 6px',
    borderRight: 'none',
  } satisfies CSSProperties,

  toggleRight: {
    borderRadius: '0 6px 6px 0',
  } satisfies CSSProperties,

  searchContainer: {
    padding: '10px',
    flexShrink: 0,
  } satisfies CSSProperties,

  searchWrapper: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    backgroundColor: '#1a1a28',
    border: '1px solid #2a2a3a',
    borderRadius: 6,
    padding: '6px 10px',
    transition: 'border-color 0.2s ease',
  } satisfies CSSProperties,

  searchIcon: {
    fontSize: 13,
    color: '#5a5a6e',
    flexShrink: 0,
  } satisfies CSSProperties,

  searchInput: {
    flex: 1,
    backgroundColor: 'transparent',
    border: 'none',
    outline: 'none',
    fontSize: 12,
    color: '#e8e8f0',
    fontFamily: 'inherit',
    lineHeight: 1.4,
  } satisfies CSSProperties,

  listContainer: {
    flex: 1,
    overflowY: 'auto',
    padding: '0 10px 12px',
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  } satisfies CSSProperties,

  npcCard: (isDead: boolean, hovered: boolean): CSSProperties => ({
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
    backgroundColor: '#1a1a28',
    borderRadius: 8,
    border: '1px solid #2a2a3a',
    borderLeft: `3px solid ${isDead ? '#5a5a6e' : '#8b7340'}`,
    padding: '10px 12px',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
    opacity: isDead ? 0.6 : 1,
    filter: isDead ? 'grayscale(0.5)' : 'none',
    ...(hovered && {
      borderColor: isDead ? '#6a6a7e' : '#8b7340',
      backgroundColor: '#1e1e2e',
    }),
  }),

  cardTopRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
  } satisfies CSSProperties,

  portrait: (isDead: boolean): CSSProperties => ({
    width: 56,
    height: 56,
    borderRadius: 8,
    backgroundColor: '#0a0a0f',
    border: `1px solid ${isDead ? '#2a2a3a' : '#2a2a3a'}`,
    flexShrink: 0,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 20,
    color: isDead ? '#5a5a6e' : '#8b7340',
    overflow: 'hidden',
    filter: isDead ? 'grayscale(1)' : 'none',
  }),

  portraitImage: {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
    borderRadius: 8,
  } satisfies CSSProperties,

  cardInfo: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
    minWidth: 0,
  } satisfies CSSProperties,

  nameRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 8,
  } satisfies CSSProperties,

  npcName: {
    fontSize: 18,
    fontWeight: 700,
    color: '#e8e8f0',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  } satisfies CSSProperties,

  chevron: (expanded: boolean): CSSProperties => ({
    fontSize: 14,
    color: '#5a5a6e',
    transition: 'transform 0.2s ease',
    transform: expanded ? 'rotate(90deg)' : 'rotate(0deg)',
    flexShrink: 0,
    userSelect: 'none',
  }),

  dispositionBadge: (color: string): CSSProperties => ({
    display: 'inline-flex',
    alignItems: 'center',
    padding: '1px 10px',
    borderRadius: 999,
    fontSize: 11,
    fontWeight: 600,
    lineHeight: 1.5,
    letterSpacing: '0.02em',
    whiteSpace: 'nowrap',
    userSelect: 'none',
    backgroundColor: hexToRgba(color, 0.15),
    border: `1px solid ${hexToRgba(color, 0.3)}`,
    color,
  }),

  relationshipRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    marginTop: 2,
  } satisfies CSSProperties,

  relationshipLabel: {
    fontSize: 11,
    fontWeight: 700,
    color: '#8b7340',
    minWidth: 22,
    flexShrink: 0,
  } satisfies CSSProperties,

  barContainer: {
    flex: 1,
    position: 'relative',
    height: 14,
    display: 'flex',
    alignItems: 'center',
  } satisfies CSSProperties,

  barTrack: {
    width: '100%',
    height: 4,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 2,
    overflow: 'visible',
    position: 'relative',
  } satisfies CSSProperties,

  barFill: (percent: number): CSSProperties => ({
    width: `${Math.min(100, Math.max(0, percent))}%`,
    height: '100%',
    backgroundColor: '#c9a84c',
    borderRadius: 2,
    transition: 'width 0.4s ease',
    boxShadow: percent > 0 ? '0 0 6px rgba(201, 168, 76, 0.4)' : 'none',
  }),

  heartIcon: (percent: number, isDead: boolean): CSSProperties => ({
    position: 'absolute',
    left: `${Math.min(100, Math.max(0, percent))}%`,
    top: '50%',
    transform: 'translate(-50%, -50%)',
    fontSize: 12,
    color: isDead ? '#5a5a6e' : '#e84393',
    filter: isDead ? 'grayscale(1)' : `drop-shadow(0 0 4px rgba(232, 67, 147, 0.5))`,
    zIndex: 1,
    lineHeight: 1,
    pointerEvents: 'none',
  }),

  expandedContent: {
    borderTop: '1px solid #2a2a3a',
    paddingTop: 8,
    marginTop: 2,
  } satisfies CSSProperties,

  npcTitle: {
    fontSize: 11,
    fontStyle: 'italic',
    color: '#8b7340',
    marginBottom: 4,
  } satisfies CSSProperties,

  notesText: {
    fontSize: 12,
    color: '#9898a8',
    lineHeight: 1.5,
  } satisfies CSSProperties,

  emptyState: {
    fontSize: 12,
    color: '#5a5a6e',
    fontStyle: 'italic',
    textAlign: 'center',
    padding: '24px 0',
  } satisfies CSSProperties,
};

function ToggleButton({
  active,
  label,
  side,
  onClick,
}: {
  active: boolean;
  label: string;
  side: 'left' | 'right';
  onClick: () => void;
}) {
  const [hovered, setHovered] = useState(false);

  const sideStyle = side === 'left' ? styles.toggleLeft : styles.toggleRight;
  const merged: CSSProperties = {
    ...styles.toggleButton(active, hovered),
    ...sideStyle,
  };

  return (
    <button
      style={merged}
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {label}
    </button>
  );
}

function NpcCard({
  npc,
  onSelect,
}: {
  npc: NpcRelationship;
  onSelect?: () => void;
}) {
  const [hovered, setHovered] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const percent = npc.max_relationship > 0
    ? (npc.relationship_level / npc.max_relationship) * 100
    : 0;

  const dispColor = DISPOSITION_COLORS[npc.disposition];

  const handleClick = useCallback(() => {
    setExpanded(prev => !prev);
    onSelect?.();
  }, [onSelect]);

  return (
    <div
      style={styles.npcCard(npc.is_dead, hovered)}
      onClick={handleClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <div style={styles.cardTopRow}>
        <div style={styles.portrait(npc.is_dead)}>
          {npc.portrait ? (
            <img src={npc.portrait} alt={npc.name} style={styles.portraitImage} />
          ) : (
            npc.is_dead ? '\u{1F480}' : '\u{1F9D9}'
          )}
        </div>

        <div style={styles.cardInfo}>
          <div style={styles.nameRow}>
            <span style={styles.npcName}>{npc.name}</span>
            <span style={styles.chevron(expanded)}>&#9654;</span>
          </div>

          <span style={styles.dispositionBadge(dispColor)}>
            {npc.disposition}
          </span>

          <div style={styles.relationshipRow}>
            <span style={styles.relationshipLabel}>
              R{npc.relationship_level}
            </span>
            <div style={styles.barContainer}>
              <div style={styles.barTrack}>
                <div style={styles.barFill(percent)} />
                <span style={styles.heartIcon(percent, npc.is_dead)}>
                  {npc.is_dead ? '\u{1F480}' : '\u2764'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {expanded && (npc.title || npc.notes) && (
        <div style={styles.expandedContent}>
          {npc.title && (
            <div style={styles.npcTitle}>{npc.title}</div>
          )}
          {npc.notes && (
            <div style={styles.notesText}>{npc.notes}</div>
          )}
        </div>
      )}
    </div>
  );
}

function RelationshipsTab({ relationships, onSelectNpc }: RelationshipsTabProps) {
  const [activeView, setActiveView] = useState<'relationships' | 'ossuary'>('relationships');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchFocused, setSearchFocused] = useState(false);

  const living = useMemo(
    () => relationships.filter(r => !r.is_dead),
    [relationships],
  );

  const dead = useMemo(
    () => relationships.filter(r => r.is_dead),
    [relationships],
  );

  const currentList = activeView === 'relationships' ? living : dead;

  const filtered = useMemo(() => {
    if (!searchQuery.trim()) return currentList;
    const query = searchQuery.toLowerCase();
    return currentList.filter(
      npc =>
        npc.name.toLowerCase().includes(query) ||
        npc.title?.toLowerCase().includes(query) ||
        npc.disposition.toLowerCase().includes(query),
    );
  }, [currentList, searchQuery]);

  const searchWrapperStyle: CSSProperties = {
    ...styles.searchWrapper,
    borderColor: searchFocused ? '#8b7340' : '#2a2a3a',
  };

  return (
    <div style={styles.container}>
      <div style={styles.toggleRow}>
        <ToggleButton
          active={activeView === 'relationships'}
          label="RELATIONSHIPS"
          side="left"
          onClick={() => setActiveView('relationships')}
        />
        <ToggleButton
          active={activeView === 'ossuary'}
          label="OSSUARY"
          side="right"
          onClick={() => setActiveView('ossuary')}
        />
      </div>

      <div style={styles.searchContainer}>
        <div style={searchWrapperStyle}>
          <span style={styles.searchIcon}>&#128269;</span>
          <input
            style={styles.searchInput}
            type="text"
            placeholder="Rechercher des PNJ..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            onFocus={() => setSearchFocused(true)}
            onBlur={() => setSearchFocused(false)}
          />
        </div>
      </div>

      <div style={styles.listContainer}>
        {filtered.length === 0 ? (
          <div style={styles.emptyState}>
            {searchQuery.trim()
              ? 'Aucun PNJ correspondant'
              : activeView === 'ossuary'
                ? 'Aucun PNJ decede'
                : 'Aucune relation etablie'}
          </div>
        ) : (
          filtered.map(npc => (
            <NpcCard
              key={npc.id}
              npc={npc}
              onSelect={() => onSelectNpc?.(npc.id)}
            />
          ))
        )}
      </div>
    </div>
  );
}

export default RelationshipsTab;
