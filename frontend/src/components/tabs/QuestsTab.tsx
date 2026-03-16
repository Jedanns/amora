import { type CSSProperties, useState, useCallback } from 'react';

interface QuestNote {
  source: string;
  text: string;
}

interface QuestsTabProps {
  quests: Array<{
    id: string;
    name: string;
    description: string;
    level: number;
    xp_reward: number;
    status: 'active' | 'completed' | 'failed';
    reward_text?: string;
    bookmarked?: boolean;
    notes?: QuestNote[];
  }>;
  rumors: Array<{
    id: string;
    name: string;
    description: string;
    level: number;
    xp_reward: number;
    bookmarked?: boolean;
    source?: string;
  }>;
  onCompleteQuest?: (id: string) => void;
  onDismissQuest?: (id: string) => void;
  onBookmarkQuest?: (id: string) => void;
  onBookmarkRumor?: (id: string) => void;
  onDismissRumor?: (id: string) => void;
}

const INITIAL_NOTES_SHOWN = 2;

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
    overflowY: 'auto',
    padding: '12px 10px',
    gap: 16,
  } satisfies CSSProperties,

  sectionHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    marginBottom: 8,
  } satisfies CSSProperties,

  sectionTitle: {
    fontSize: 12,
    fontWeight: 700,
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    color: '#c9a84c',
  } satisfies CSSProperties,

  sectionIcon: {
    fontSize: 14,
    color: '#c9a84c',
  } satisfies CSSProperties,

  sectionCount: {
    fontSize: 11,
    fontWeight: 600,
    color: '#8b7340',
  } satisfies CSSProperties,

  questList: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  } satisfies CSSProperties,

  card: {
    backgroundColor: '#1a1a28',
    borderRadius: 8,
    border: '1px solid #2a2a3a',
    padding: '10px 12px',
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
  } satisfies CSSProperties,

  cardTopRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 8,
  } satisfies CSSProperties,

  questName: {
    fontSize: 14,
    fontWeight: 700,
    color: '#e8e8f0',
    flex: 1,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  } satisfies CSSProperties,

  badgeRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    flexWrap: 'wrap',
  } satisfies CSSProperties,

  badge: (bg: string, color: string): CSSProperties => ({
    display: 'inline-flex',
    alignItems: 'center',
    padding: '1px 8px',
    borderRadius: 999,
    fontSize: 11,
    fontWeight: 600,
    lineHeight: 1.5,
    letterSpacing: '0.02em',
    whiteSpace: 'nowrap',
    userSelect: 'none',
    backgroundColor: hexToRgba(bg, 0.18),
    border: `1px solid ${hexToRgba(bg, 0.3)}`,
    color,
  }),

  actionRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 4,
    marginLeft: 'auto',
    flexShrink: 0,
  } satisfies CSSProperties,

  description: {
    fontSize: 12,
    fontStyle: 'italic',
    color: '#9898a8',
    lineHeight: 1.5,
  } satisfies CSSProperties,

  rewardText: {
    fontSize: 12,
    fontWeight: 600,
    color: '#53d769',
    lineHeight: 1.4,
  } satisfies CSSProperties,

  notesSection: {
    borderTop: '1px solid #2a2a3a',
    paddingTop: 6,
    marginTop: 2,
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  } satisfies CSSProperties,

  noteSourceRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    fontSize: 11,
    fontWeight: 600,
    color: '#c9a84c',
  } satisfies CSSProperties,

  noteSourceIcon: {
    fontSize: 12,
  } satisfies CSSProperties,

  noteItem: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: 6,
    paddingLeft: 4,
  } satisfies CSSProperties,

  noteBullet: {
    color: '#8b7340',
    fontSize: 10,
    lineHeight: '18px',
    flexShrink: 0,
  } satisfies CSSProperties,

  noteText: {
    fontSize: 11,
    color: '#9898a8',
    lineHeight: 1.5,
  } satisfies CSSProperties,

  showMoreLink: {
    fontSize: 11,
    color: '#c9a84c',
    cursor: 'pointer',
    background: 'none',
    border: 'none',
    padding: '2px 4px',
    fontFamily: 'inherit',
    textAlign: 'left',
    userSelect: 'none',
  } satisfies CSSProperties,

  emptyState: {
    fontSize: 12,
    color: '#5a5a6e',
    fontStyle: 'italic',
    textAlign: 'center',
    padding: '16px 0',
  } satisfies CSSProperties,
};

function IconButton({
  label,
  children,
  color,
  hoverColor,
  onClick,
}: {
  label: string;
  children: string;
  color: string;
  hoverColor: string;
  onClick?: () => void;
}) {
  const [hovered, setHovered] = useState(false);

  const style: CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: 24,
    height: 24,
    border: 'none',
    borderRadius: 4,
    backgroundColor: hovered ? 'rgba(255, 255, 255, 0.06)' : 'transparent',
    color: hovered ? hoverColor : color,
    fontSize: 14,
    cursor: 'pointer',
    transition: 'all 0.15s ease',
    padding: 0,
    fontFamily: 'inherit',
    lineHeight: 1,
  };

  return (
    <button
      style={style}
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      aria-label={label}
      title={label}
    >
      {children}
    </button>
  );
}

function QuestNotes({ notes }: { notes: QuestNote[] }) {
  const [expanded, setExpanded] = useState(false);

  if (notes.length === 0) return null;

  const grouped = new Map<string, string[]>();
  for (const note of notes) {
    const existing = grouped.get(note.source) ?? [];
    existing.push(note.text);
    grouped.set(note.source, existing);
  }

  const allEntries = Array.from(grouped.entries());

  return (
    <div style={styles.notesSection}>
      {allEntries.map(([source, texts]) => {
        const visibleTexts = expanded
          ? texts
          : texts.slice(0, INITIAL_NOTES_SHOWN);
        const hiddenCount = texts.length - INITIAL_NOTES_SHOWN;

        return (
          <div key={source} style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <div style={styles.noteSourceRow}>
              <span style={styles.noteSourceIcon}>&#128100;</span>
              <span>{source}</span>
            </div>
            {visibleTexts.map((text, i) => (
              <div key={i} style={styles.noteItem}>
                <span style={styles.noteBullet}>&#9679;</span>
                <span style={styles.noteText}>{text}</span>
              </div>
            ))}
            {!expanded && hiddenCount > 0 && (
              <button
                style={styles.showMoreLink}
                onClick={() => setExpanded(true)}
              >
                Show {hiddenCount} more...
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}

function QuestCard({
  quest,
  onComplete,
  onDismiss,
  onBookmark,
}: {
  quest: QuestsTabProps['quests'][number];
  onComplete?: () => void;
  onDismiss?: () => void;
  onBookmark?: () => void;
}) {
  return (
    <div style={styles.card}>
      <div style={styles.cardTopRow}>
        <span style={styles.questName}>{quest.name}</span>
        <div style={styles.actionRow}>
          <IconButton
            label={quest.bookmarked ? 'Remove bookmark' : 'Bookmark'}
            color={quest.bookmarked ? '#c9a84c' : '#5a5a6e'}
            hoverColor="#c9a84c"
            onClick={onBookmark}
          >
            &#9733;
          </IconButton>
          <IconButton
            label="Dismiss"
            color="#5a5a6e"
            hoverColor="#e94560"
            onClick={onDismiss}
          >
            &#10005;
          </IconButton>
          <IconButton
            label="Complete"
            color="#5a5a6e"
            hoverColor="#53d769"
            onClick={onComplete}
          >
            &#10003;
          </IconButton>
        </div>
      </div>

      <div style={styles.badgeRow}>
        <span style={styles.badge('#53d769', '#53d769')}>
          Lvl {quest.level}
        </span>
        <span style={styles.badge('#c9a84c', '#c9a84c')}>
          {quest.xp_reward} XP
        </span>
      </div>

      <span style={styles.description}>{quest.description}</span>

      {quest.reward_text && (
        <span style={styles.rewardText}>
          &#127873; {quest.reward_text}
        </span>
      )}

      {quest.notes && quest.notes.length > 0 && (
        <QuestNotes notes={quest.notes} />
      )}
    </div>
  );
}

function RumorCard({
  rumor,
  onBookmark,
  onDismiss,
}: {
  rumor: QuestsTabProps['rumors'][number];
  onBookmark?: () => void;
  onDismiss?: () => void;
}) {
  return (
    <div style={styles.card}>
      <div style={styles.cardTopRow}>
        <span style={styles.questName}>{rumor.name}</span>
        <div style={styles.actionRow}>
          <IconButton
            label={rumor.bookmarked ? 'Remove bookmark' : 'Bookmark'}
            color={rumor.bookmarked ? '#c9a84c' : '#5a5a6e'}
            hoverColor="#c9a84c"
            onClick={onBookmark}
          >
            &#9733;
          </IconButton>
          <IconButton
            label="Dismiss"
            color="#5a5a6e"
            hoverColor="#e94560"
            onClick={onDismiss}
          >
            &#10005;
          </IconButton>
        </div>
      </div>

      <div style={styles.badgeRow}>
        <span style={styles.badge('#53d769', '#53d769')}>
          Lvl {rumor.level}
        </span>
        <span style={styles.badge('#c9a84c', '#c9a84c')}>
          {rumor.xp_reward} XP
        </span>
      </div>

      <span style={styles.description}>{rumor.description}</span>

      {rumor.source && (
        <div style={styles.noteSourceRow}>
          <span style={styles.noteSourceIcon}>&#128100;</span>
          <span>{rumor.source}</span>
        </div>
      )}
    </div>
  );
}

function QuestsTab({
  quests,
  rumors,
  onCompleteQuest,
  onDismissQuest,
  onBookmarkQuest,
  onBookmarkRumor,
  onDismissRumor,
}: QuestsTabProps) {
  const activeQuests = quests.filter(q => q.status === 'active');

  const handleComplete = useCallback(
    (id: string) => onCompleteQuest?.(id),
    [onCompleteQuest],
  );
  const handleDismissQuest = useCallback(
    (id: string) => onDismissQuest?.(id),
    [onDismissQuest],
  );
  const handleBookmarkQuest = useCallback(
    (id: string) => onBookmarkQuest?.(id),
    [onBookmarkQuest],
  );
  const handleBookmarkRumor = useCallback(
    (id: string) => onBookmarkRumor?.(id),
    [onBookmarkRumor],
  );
  const handleDismissRumor = useCallback(
    (id: string) => onDismissRumor?.(id),
    [onDismissRumor],
  );

  return (
    <div style={styles.container}>
      <section>
        <div style={styles.sectionHeader}>
          <span style={styles.sectionIcon}>&#9876;</span>
          <span style={styles.sectionTitle}>QUETES</span>
          <span style={styles.sectionCount}>({activeQuests.length})</span>
        </div>
        <div style={styles.questList}>
          {activeQuests.length === 0 ? (
            <div style={styles.emptyState}>Aucune quete active</div>
          ) : (
            activeQuests.map(quest => (
              <QuestCard
                key={quest.id}
                quest={quest}
                onComplete={() => handleComplete(quest.id)}
                onDismiss={() => handleDismissQuest(quest.id)}
                onBookmark={() => handleBookmarkQuest(quest.id)}
              />
            ))
          )}
        </div>
      </section>

      <section>
        <div style={styles.sectionHeader}>
          <span style={styles.sectionIcon}>&#128172;</span>
          <span style={styles.sectionTitle}>RUMEURS</span>
          <span style={styles.sectionCount}>({rumors.length})</span>
        </div>
        <div style={styles.questList}>
          {rumors.length === 0 ? (
            <div style={styles.emptyState}>Aucune rumeur entendue</div>
          ) : (
            rumors.map(rumor => (
              <RumorCard
                key={rumor.id}
                rumor={rumor}
                onBookmark={() => handleBookmarkRumor(rumor.id)}
                onDismiss={() => handleDismissRumor(rumor.id)}
              />
            ))
          )}
        </div>
      </section>
    </div>
  );
}

export default QuestsTab;
