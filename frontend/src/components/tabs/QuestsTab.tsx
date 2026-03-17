import { useState, useCallback } from 'react';
import { Sword, MessageCircle, User, Star, X, Check, Gift, Circle } from 'lucide-react';
import { hexToRgba } from '../../utils/colors';

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

function IconButton({
  label,
  icon: Icon,
  color,
  hoverColor,
  onClick,
}: {
  label: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  color: string;
  hoverColor: string;
  onClick?: () => void;
}) {
  return (
    <button
      className="inline-flex items-center justify-center w-6 h-6 border-none rounded-sm bg-transparent cursor-pointer transition-all duration-150 p-0 leading-none hover:bg-white/[0.06] group"
      onClick={onClick}
      aria-label={label}
      title={label}
      style={{ color }}
      onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.color = hoverColor; }}
      onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.color = color; }}
    >
      <Icon size={14} />
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
    <div className="border-t border-border-primary pt-1.5 mt-0.5 flex flex-col gap-1">
      {allEntries.map(([source, texts]) => {
        const visibleTexts = expanded
          ? texts
          : texts.slice(0, INITIAL_NOTES_SHOWN);
        const hiddenCount = texts.length - INITIAL_NOTES_SHOWN;

        return (
          <div key={source} className="flex flex-col gap-0.5">
            <div className="flex items-center gap-1.5 text-[11px] font-semibold text-gold">
              <User size={12} />
              <span>{source}</span>
            </div>
            {visibleTexts.map((text, i) => (
              <div key={i} className="flex items-start gap-1.5 pl-1">
                <Circle size={6} className="text-gold-dim shrink-0 mt-[5px]" />
                <span className="text-[11px] text-text-secondary leading-normal">{text}</span>
              </div>
            ))}
            {!expanded && hiddenCount > 0 && (
              <button
                className="text-[11px] text-gold cursor-pointer bg-none border-none px-1 py-0.5 font-[inherit] text-left select-none"
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
    <div className="bg-bg-card rounded-lg border border-border-primary px-3 py-2.5 flex flex-col gap-1.5">
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-bold text-text-primary flex-1 overflow-hidden text-ellipsis whitespace-nowrap">{quest.name}</span>
        <div className="flex items-center gap-1 ml-auto shrink-0">
          <IconButton
            label={quest.bookmarked ? 'Remove bookmark' : 'Bookmark'}
            icon={Star}
            color={quest.bookmarked ? '#c9a84c' : '#5a5a6e'}
            hoverColor="#c9a84c"
            onClick={onBookmark}
          />
          <IconButton
            label="Dismiss"
            icon={X}
            color="#5a5a6e"
            hoverColor="#e94560"
            onClick={onDismiss}
          />
          <IconButton
            label="Complete"
            icon={Check}
            color="#5a5a6e"
            hoverColor="#53d769"
            onClick={onComplete}
          />
        </div>
      </div>

      <div className="flex items-center gap-1.5 flex-wrap">
        <span
          className="inline-flex items-center px-2 py-px rounded-full text-[11px] font-semibold leading-normal tracking-[0.02em] whitespace-nowrap select-none"
          style={{ backgroundColor: hexToRgba('#53d769', 0.18), border: `1px solid ${hexToRgba('#53d769', 0.3)}`, color: '#53d769' }}
        >
          Lvl {quest.level}
        </span>
        <span
          className="inline-flex items-center px-2 py-px rounded-full text-[11px] font-semibold leading-normal tracking-[0.02em] whitespace-nowrap select-none"
          style={{ backgroundColor: hexToRgba('#c9a84c', 0.18), border: `1px solid ${hexToRgba('#c9a84c', 0.3)}`, color: '#c9a84c' }}
        >
          {quest.xp_reward} XP
        </span>
      </div>

      <span className="text-xs italic text-text-secondary leading-normal">{quest.description}</span>

      {quest.reward_text && (
        <span className="text-xs font-semibold text-green leading-snug flex items-center gap-1">
          <Gift size={12} /> {quest.reward_text}
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
    <div className="bg-bg-card rounded-lg border border-border-primary px-3 py-2.5 flex flex-col gap-1.5">
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-bold text-text-primary flex-1 overflow-hidden text-ellipsis whitespace-nowrap">{rumor.name}</span>
        <div className="flex items-center gap-1 ml-auto shrink-0">
          <IconButton
            label={rumor.bookmarked ? 'Remove bookmark' : 'Bookmark'}
            icon={Star}
            color={rumor.bookmarked ? '#c9a84c' : '#5a5a6e'}
            hoverColor="#c9a84c"
            onClick={onBookmark}
          />
          <IconButton
            label="Dismiss"
            icon={X}
            color="#5a5a6e"
            hoverColor="#e94560"
            onClick={onDismiss}
          />
        </div>
      </div>

      <div className="flex items-center gap-1.5 flex-wrap">
        <span
          className="inline-flex items-center px-2 py-px rounded-full text-[11px] font-semibold leading-normal tracking-[0.02em] whitespace-nowrap select-none"
          style={{ backgroundColor: hexToRgba('#53d769', 0.18), border: `1px solid ${hexToRgba('#53d769', 0.3)}`, color: '#53d769' }}
        >
          Lvl {rumor.level}
        </span>
        <span
          className="inline-flex items-center px-2 py-px rounded-full text-[11px] font-semibold leading-normal tracking-[0.02em] whitespace-nowrap select-none"
          style={{ backgroundColor: hexToRgba('#c9a84c', 0.18), border: `1px solid ${hexToRgba('#c9a84c', 0.3)}`, color: '#c9a84c' }}
        >
          {rumor.xp_reward} XP
        </span>
      </div>

      <span className="text-xs italic text-text-secondary leading-normal">{rumor.description}</span>

      {rumor.source && (
        <div className="flex items-center gap-1.5 text-[11px] font-semibold text-gold">
          <User size={12} />
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
    <div className="flex flex-col h-full overflow-y-auto px-2.5 py-3 gap-4">
      <section>
        <div className="flex items-center gap-2 mb-2">
          <Sword size={14} className="text-gold" />
          <span className="text-xs font-bold tracking-[0.08em] uppercase text-gold">QUETES</span>
          <span className="text-[11px] font-semibold text-gold-dim">({activeQuests.length})</span>
        </div>
        <div className="flex flex-col gap-2">
          {activeQuests.length === 0 ? (
            <div className="text-xs text-text-dim italic text-center py-4">Aucune quete active</div>
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
        <div className="flex items-center gap-2 mb-2">
          <MessageCircle size={14} className="text-gold" />
          <span className="text-xs font-bold tracking-[0.08em] uppercase text-gold">RUMEURS</span>
          <span className="text-[11px] font-semibold text-gold-dim">({rumors.length})</span>
        </div>
        <div className="flex flex-col gap-2">
          {rumors.length === 0 ? (
            <div className="text-xs text-text-dim italic text-center py-4">Aucune rumeur entendue</div>
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
