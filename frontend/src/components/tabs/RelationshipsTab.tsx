import { useState, useCallback, useMemo } from 'react';
import { Search, User, Skull, Heart, ChevronRight } from 'lucide-react';
import { hexToRgba } from '../../utils/colors';

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

function NpcCard({
  npc,
  onSelect,
}: {
  npc: NpcRelationship;
  onSelect?: () => void;
}) {
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
      className={`flex flex-col gap-2 bg-bg-card rounded-lg border border-border-primary border-l-[3px] px-3 py-2.5 cursor-pointer transition-all duration-150 hover:bg-bg-input ${
        npc.is_dead ? 'opacity-60 grayscale-[0.5]' : ''
      }`}
      style={{ borderLeftColor: npc.is_dead ? '#5a5a6e' : '#8b7340' }}
      onClick={handleClick}
    >
      <div className="flex items-center gap-2.5">
        <div
          className={`w-14 h-14 rounded-lg bg-bg-primary border border-border-primary shrink-0 flex items-center justify-center overflow-hidden ${
            npc.is_dead ? 'grayscale' : ''
          }`}
        >
          {npc.portrait ? (
            <img src={npc.portrait} alt={npc.name} className="w-full h-full object-cover rounded-lg" />
          ) : npc.is_dead ? (
            <Skull size={20} className="text-[#5a5a6e]" />
          ) : (
            <User size={20} className="text-border-gold" />
          )}
        </div>

        <div className="flex-1 flex flex-col gap-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <span className="text-lg font-bold text-text-primary overflow-hidden text-ellipsis whitespace-nowrap">
              {npc.name}
            </span>
            <ChevronRight
              size={14}
              className={`text-[#5a5a6e] shrink-0 transition-transform duration-200 ${expanded ? 'rotate-90' : ''}`}
            />
          </div>

          <span
            className="inline-flex items-center self-start px-2.5 py-px rounded-full text-[11px] font-semibold leading-normal tracking-[0.02em] whitespace-nowrap select-none"
            style={{
              backgroundColor: hexToRgba(dispColor, 0.15),
              border: `1px solid ${hexToRgba(dispColor, 0.3)}`,
              color: dispColor,
            }}
          >
            {npc.disposition}
          </span>

          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-[11px] font-bold text-border-gold min-w-[22px] shrink-0">
              R{npc.relationship_level}
            </span>
            <div className="flex-1 relative h-3.5 flex items-center">
              <div className="w-full h-1 bg-white/[0.08] rounded-sm overflow-visible relative">
                <div
                  className="h-full bg-gold rounded-sm transition-[width] duration-400"
                  style={{
                    width: `${Math.min(100, Math.max(0, percent))}%`,
                    boxShadow: percent > 0 ? '0 0 6px rgba(201, 168, 76, 0.4)' : 'none',
                  }}
                />
                <span
                  className="absolute top-1/2 -translate-y-1/2 z-[1] pointer-events-none"
                  style={{ left: `${Math.min(100, Math.max(0, percent))}%`, transform: 'translate(-50%, -50%)' }}
                >
                  {npc.is_dead ? (
                    <Skull size={12} className="text-[#5a5a6e] grayscale" />
                  ) : (
                    <Heart size={12} className="text-pink fill-pink drop-shadow-[0_0_4px_rgba(232,67,147,0.5)]" />
                  )}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {expanded && (npc.title || npc.notes) && (
        <div className="border-t border-border-primary pt-2 mt-0.5">
          {npc.title && (
            <div className="text-[11px] italic text-border-gold mb-1">{npc.title}</div>
          )}
          {npc.notes && (
            <div className="text-xs text-text-secondary leading-normal">{npc.notes}</div>
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

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Toggle buttons */}
      <div className="flex items-center px-2.5 pt-2.5 shrink-0">
        <button
          className={`flex-1 py-[7px] px-3 text-[11px] font-bold tracking-[0.08em] uppercase cursor-pointer transition-all duration-200 select-none border rounded-l-md border-r-0 ${
            activeView === 'relationships'
              ? 'bg-gold/12 border-gold text-gold shadow-[0_0_8px_rgba(201,168,76,0.15)]'
              : 'bg-transparent border-border-primary text-text-secondary hover:bg-bg-hover hover:text-text-primary'
          }`}
          onClick={() => setActiveView('relationships')}
        >
          RELATIONSHIPS
        </button>
        <button
          className={`flex-1 py-[7px] px-3 text-[11px] font-bold tracking-[0.08em] uppercase cursor-pointer transition-all duration-200 select-none border rounded-r-md ${
            activeView === 'ossuary'
              ? 'bg-gold/12 border-gold text-gold shadow-[0_0_8px_rgba(201,168,76,0.15)]'
              : 'bg-transparent border-border-primary text-text-secondary hover:bg-bg-hover hover:text-text-primary'
          }`}
          onClick={() => setActiveView('ossuary')}
        >
          OSSUARY
        </button>
      </div>

      {/* Search */}
      <div className="p-2.5 shrink-0">
        <div
          className={`flex items-center gap-2 bg-bg-card border rounded-md px-2.5 py-1.5 transition-colors duration-200 ${
            searchFocused ? 'border-border-gold' : 'border-border-primary'
          }`}
        >
          <Search size={13} className="text-[#5a5a6e] shrink-0" />
          <input
            className="flex-1 bg-transparent border-none outline-none text-xs text-text-primary placeholder:text-text-dim"
            type="text"
            placeholder="Rechercher des PNJ..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            onFocus={() => setSearchFocused(true)}
            onBlur={() => setSearchFocused(false)}
          />
        </div>
      </div>

      {/* NPC list */}
      <div className="flex-1 overflow-y-auto px-2.5 pb-3 flex flex-col gap-2">
        {filtered.length === 0 ? (
          <div className="text-xs text-[#5a5a6e] italic text-center py-6">
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
