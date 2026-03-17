import { useState } from 'react';
import { Save, HelpCircle, ChevronDown, ChevronRight, Star } from 'lucide-react';

interface RightPanelProps {
  character: {
    name: string;
    character_class: string;
    level: number;
    hp_current: number;
    hp_max: number;
    mana_current: number;
    mana_max: number;
  } | null;
  playerName?: string;
  onSave?: () => void;
}

interface HowToPlayItem {
  title: string;
  details: string;
}

const HOW_TO_PLAY_ITEMS: HowToPlayItem[] = [
  {
    title: 'Taking an Action',
    details:
      'Type what you want your player to do in the chat input. Be descriptive — the more detail you give, the richer the narration.',
  },
  {
    title: 'Rolling for Skill Checks',
    details:
      'When your action requires a skill check, a dice roll is triggered automatically. Your modifiers are applied based on your character stats.',
  },
  {
    title: 'Completing Quests',
    details:
      'Follow quest objectives shown in the left panel. Complete them to earn experience, gold, and items.',
  },
  {
    title: 'Turning Rumors into Quests',
    details:
      'Rumors you hear from NPCs can become full quests. Investigate them to unlock new storylines.',
  },
  {
    title: 'Hearing Rumors',
    details:
      'Talk to NPCs in taverns and marketplaces. They may share rumors about hidden treasures, dangers, or opportunities.',
  },
  {
    title: 'Trading',
    details:
      'Visit merchants to buy and sell items. Prices vary based on your Negotiation skill and the merchant\'s disposition.',
  },
];

function RightPanel({ character, playerName = 'LUCAS', onSave }: RightPanelProps) {
  const [howToPlayOpen, setHowToPlayOpen] = useState(true);
  const [expandedItem, setExpandedItem] = useState<number | null>(null);
  const [hoveredItem, setHoveredItem] = useState<number | null>(null);

  const toggleItem = (index: number) => {
    setExpandedItem(expandedItem === index ? null : index);
  };

  return (
    <div className="flex flex-col h-full overflow-y-auto overflow-x-hidden text-text-primary">
      {/* Party Header */}
      <div className="text-center px-4 py-3.5 pb-3 border-b border-border-primary relative">
        <div className="absolute top-0 left-4 right-4 h-px bg-[linear-gradient(90deg,transparent,var(--color-gold)_30%,var(--color-gold)_70%,transparent)]" />
        <span className="text-xs font-bold tracking-[0.14em] text-gold uppercase select-none">
          {playerName.toUpperCase()}&apos;S PARTY
        </span>
      </div>

      {/* Character Quick Card */}
      <div className="flex flex-col items-center px-4 pt-5 pb-4 border-b border-border-primary">
        <div className="relative mb-3">
          <div className="w-[100px] h-[100px] rounded-lg border-2 border-gold bg-bg-card flex items-center justify-center text-border-primary text-4xl select-none shadow-gold">
            {character ? character.name.charAt(0).toUpperCase() : '?'}
          </div>
          {character && (
            <div className="absolute -top-1 -right-2 flex items-center gap-[3px] bg-[#1e1e30] border border-gold rounded-md px-[7px] py-0.5 text-[10px] font-semibold text-gold tracking-[0.04em] whitespace-nowrap shadow-md">
              <Star size={10} />
              <span>{character.character_class}</span>
            </div>
          )}
        </div>

        {character ? (
          <>
            <div className="flex items-center gap-2 text-[13px] font-semibold tracking-[0.06em] mt-[3px]">
              <span className="text-red">PV</span>
              <span className="text-red">
                {character.hp_current}/{character.hp_max}
              </span>
            </div>
            <div className="flex items-center gap-2 text-[13px] font-semibold tracking-[0.06em] mt-[3px]">
              <span className="text-text-secondary">Ame</span>
              <span className="text-text-secondary">
                {character.mana_current}/{character.mana_max}
              </span>
            </div>
          </>
        ) : (
          <div className="text-xs text-text-secondary mt-1">
            Aucun personnage
          </div>
        )}
      </div>

      {/* How To Play Section */}
      <div className="flex-1 pb-2 border-b border-border-primary min-h-0 overflow-y-auto">
        <div
          className="flex items-center justify-between px-4 py-3 cursor-pointer select-none"
          onClick={() => setHowToPlayOpen(!howToPlayOpen)}
        >
          <div className="flex items-center gap-1.5 text-[11px] font-bold tracking-[0.12em] text-gold uppercase">
            <HelpCircle size={13} />
            <span>HOW TO PLAY</span>
          </div>
          <ChevronDown
            size={12}
            className={`text-text-secondary transition-transform duration-200 ${howToPlayOpen ? 'rotate-180' : 'rotate-0'}`}
          />
        </div>

        {howToPlayOpen && (
          <div className="px-3">
            {HOW_TO_PLAY_ITEMS.map((item, index) => (
              <div key={index}>
                <div
                  className={`flex items-start gap-2 px-1 py-2 cursor-pointer border-b border-[#1e1e2a] rounded-sm transition-colors duration-150 ${
                    hoveredItem === index ? 'bg-bg-card' : 'bg-transparent'
                  }`}
                  onClick={() => toggleItem(index)}
                  onMouseEnter={() => setHoveredItem(index)}
                  onMouseLeave={() => setHoveredItem(null)}
                >
                  <span className="text-[11px] font-bold text-gold min-w-4 text-right pt-px shrink-0">
                    {index + 1}.
                  </span>
                  <span className="text-xs font-semibold text-text-primary leading-[1.4] flex-1">
                    {item.title}
                  </span>
                  <ChevronRight
                    size={10}
                    className={`text-text-secondary transition-transform duration-200 pt-[3px] shrink-0 ${
                      expandedItem === index ? 'rotate-90' : 'rotate-0'
                    }`}
                  />
                </div>
                {expandedItem === index && (
                  <div className="text-[11px] text-text-secondary leading-[1.5] px-1 pt-1 pb-2.5 pl-7">
                    {item.details}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="p-4 flex flex-col gap-2 shrink-0">
        <button
          className="flex items-center justify-center gap-1.5 w-full px-3 py-2 border border-border-primary rounded-md text-xs font-semibold tracking-[0.04em] cursor-pointer transition-all duration-200 bg-transparent text-text-secondary hover:bg-bg-input hover:text-text-primary hover:border-text-secondary"
          onClick={onSave}
        >
          <Save size={14} />
          Sauvegarder
        </button>
      </div>
    </div>
  );
}

export default RightPanel;
