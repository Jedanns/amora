import { type CSSProperties, useState } from 'react';

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
    title: 'Inviting Your Friends',
    details:
      'Share your session code with friends so they can join your campaign as party members.',
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

const panelStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  height: '100%',
  overflowY: 'auto',
  overflowX: 'hidden',
  fontFamily: 'inherit',
  color: '#e8e8f0',
};

const partyHeaderStyle: CSSProperties = {
  textAlign: 'center',
  padding: '14px 16px 12px',
  borderBottom: '1px solid #2a2a3a',
  position: 'relative',
};

const partyHeaderBorderTop: CSSProperties = {
  position: 'absolute',
  top: 0,
  left: 16,
  right: 16,
  height: 1,
  background: 'linear-gradient(90deg, transparent, #c9a84c 30%, #c9a84c 70%, transparent)',
};

const partyTitleStyle: CSSProperties = {
  fontSize: 12,
  fontWeight: 700,
  letterSpacing: '0.14em',
  color: '#c9a84c',
  textTransform: 'uppercase',
  userSelect: 'none',
};

const characterCardStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  padding: '20px 16px 16px',
  borderBottom: '1px solid #2a2a3a',
};

const portraitContainerStyle: CSSProperties = {
  position: 'relative',
  marginBottom: 12,
};

const portraitStyle: CSSProperties = {
  width: 100,
  height: 100,
  borderRadius: 12,
  border: '2px solid #c9a84c',
  backgroundColor: '#1a1a28',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  color: '#2a2a3a',
  fontSize: 36,
  userSelect: 'none',
  boxShadow: '0 0 12px rgba(201, 168, 76, 0.15)',
};

const classBadgeStyle: CSSProperties = {
  position: 'absolute',
  top: -4,
  right: -8,
  display: 'flex',
  alignItems: 'center',
  gap: 3,
  backgroundColor: '#1e1e30',
  border: '1px solid #c9a84c',
  borderRadius: 6,
  padding: '2px 7px',
  fontSize: 10,
  fontWeight: 600,
  color: '#c9a84c',
  letterSpacing: '0.04em',
  whiteSpace: 'nowrap',
  boxShadow: '0 2px 6px rgba(0, 0, 0, 0.4)',
};

const statLineStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  fontSize: 13,
  fontWeight: 600,
  letterSpacing: '0.06em',
  marginTop: 3,
};

const howToPlaySectionStyle: CSSProperties = {
  flex: 1,
  padding: '0 0 8px',
  borderBottom: '1px solid #2a2a3a',
  minHeight: 0,
  overflowY: 'auto',
};

const howToPlayHeaderStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '12px 16px',
  cursor: 'pointer',
  userSelect: 'none',
};

const howToPlayTitleStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 6,
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: '0.12em',
  color: '#c9a84c',
  textTransform: 'uppercase',
};

const chevronStyle = (expanded: boolean): CSSProperties => ({
  fontSize: 10,
  color: '#9898a8',
  transition: 'transform 0.2s ease',
  transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
});

const itemContainerStyle: CSSProperties = {
  padding: '0 12px',
};

const itemHeaderStyle = (hovered: boolean): CSSProperties => ({
  display: 'flex',
  alignItems: 'flex-start',
  gap: 8,
  padding: '8px 4px',
  cursor: 'pointer',
  borderBottom: '1px solid #1e1e2a',
  backgroundColor: hovered ? '#1a1a28' : 'transparent',
  borderRadius: 4,
  transition: 'background-color 0.15s ease',
});

const itemNumberStyle: CSSProperties = {
  fontSize: 11,
  fontWeight: 700,
  color: '#c9a84c',
  minWidth: 16,
  textAlign: 'right',
  paddingTop: 1,
  flexShrink: 0,
};

const itemTitleStyle: CSSProperties = {
  fontSize: 12,
  fontWeight: 600,
  color: '#e8e8f0',
  lineHeight: 1.4,
  flex: 1,
};

const itemChevronStyle = (expanded: boolean): CSSProperties => ({
  fontSize: 9,
  color: '#9898a8',
  transition: 'transform 0.2s ease',
  transform: expanded ? 'rotate(90deg)' : 'rotate(0deg)',
  paddingTop: 3,
  flexShrink: 0,
});

const itemDetailsStyle: CSSProperties = {
  fontSize: 11,
  color: '#9898a8',
  lineHeight: 1.5,
  padding: '4px 4px 10px 28px',
};

const quickActionsStyle: CSSProperties = {
  padding: '12px 16px',
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
  flexShrink: 0,
};

const buttonBase: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: 6,
  width: '100%',
  padding: '8px 12px',
  border: '1px solid #2a2a3a',
  borderRadius: 6,
  fontSize: 12,
  fontWeight: 600,
  letterSpacing: '0.04em',
  cursor: 'pointer',
  fontFamily: 'inherit',
  transition: 'all 0.2s ease',
};

function RightPanel({ character, playerName = 'LUCAS', onSave }: RightPanelProps) {
  const [howToPlayOpen, setHowToPlayOpen] = useState(true);
  const [expandedItem, setExpandedItem] = useState<number | null>(null);
  const [hoveredItem, setHoveredItem] = useState<number | null>(null);
  const [saveHovered, setSaveHovered] = useState(false);
  const [newsHovered, setNewsHovered] = useState(false);

  const toggleItem = (index: number) => {
    setExpandedItem(expandedItem === index ? null : index);
  };

  const saveButtonStyle: CSSProperties = {
    ...buttonBase,
    backgroundColor: saveHovered ? '#1e1e30' : 'transparent',
    color: saveHovered ? '#e8e8f0' : '#9898a8',
    borderColor: saveHovered ? '#9898a8' : '#2a2a3a',
  };

  const newsButtonStyle: CSSProperties = {
    ...buttonBase,
    backgroundColor: newsHovered ? '#2a2235' : '#1e1a28',
    color: newsHovered ? '#e8e8f0' : '#c9a84c',
    borderColor: newsHovered ? '#c9a84c' : '#2a2a3a',
  };

  const updateDotStyle: CSSProperties = {
    width: 6,
    height: 6,
    borderRadius: '50%',
    backgroundColor: '#e94560',
    boxShadow: '0 0 6px rgba(233, 69, 96, 0.6)',
    flexShrink: 0,
  };

  return (
    <div style={panelStyle}>
      {/* Party Header */}
      <div style={partyHeaderStyle}>
        <div style={partyHeaderBorderTop} />
        <span style={partyTitleStyle}>
          {playerName.toUpperCase()}&apos;S PARTY
        </span>
      </div>

      {/* Character Quick Card */}
      <div style={characterCardStyle}>
        <div style={portraitContainerStyle}>
          <div style={portraitStyle}>
            {character ? character.name.charAt(0).toUpperCase() : '?'}
          </div>
          {character && (
            <div style={classBadgeStyle}>
              <span style={{ fontSize: 10 }}>&#9733;</span>
              <span>{character.character_class}</span>
            </div>
          )}
        </div>

        {character ? (
          <>
            <div style={statLineStyle}>
              <span style={{ color: '#e94560' }}>PV</span>
              <span style={{ color: '#e94560' }}>
                {character.hp_current}/{character.hp_max}
              </span>
            </div>
            <div style={statLineStyle}>
              <span style={{ color: '#9898a8' }}>Ame</span>
              <span style={{ color: '#9898a8' }}>
                {character.mana_current}/{character.mana_max}
              </span>
            </div>
          </>
        ) : (
          <div style={{ fontSize: 12, color: '#9898a8', marginTop: 4 }}>
            Aucun personnage
          </div>
        )}
      </div>

      {/* How To Play Section */}
      <div style={howToPlaySectionStyle}>
        <div
          style={howToPlayHeaderStyle}
          onClick={() => setHowToPlayOpen(!howToPlayOpen)}
        >
          <div style={howToPlayTitleStyle}>
            <span style={{ fontSize: 13 }}>&#63;</span>
            <span>HOW TO PLAY</span>
          </div>
          <span style={chevronStyle(howToPlayOpen)}>&#9660;</span>
        </div>

        {howToPlayOpen && (
          <div style={itemContainerStyle}>
            {HOW_TO_PLAY_ITEMS.map((item, index) => (
              <div key={index}>
                <div
                  style={itemHeaderStyle(hoveredItem === index)}
                  onClick={() => toggleItem(index)}
                  onMouseEnter={() => setHoveredItem(index)}
                  onMouseLeave={() => setHoveredItem(null)}
                >
                  <span style={itemNumberStyle}>{index + 1}.</span>
                  <span style={itemTitleStyle}>{item.title}</span>
                  <span style={itemChevronStyle(expandedItem === index)}>&#9654;</span>
                </div>
                {expandedItem === index && (
                  <div style={itemDetailsStyle}>{item.details}</div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div style={quickActionsStyle}>
        <button
          style={saveButtonStyle}
          onClick={onSave}
          onMouseEnter={() => setSaveHovered(true)}
          onMouseLeave={() => setSaveHovered(false)}
        >
          &#128190; Sauvegarder
        </button>
        <button
          style={newsButtonStyle}
          onMouseEnter={() => setNewsHovered(true)}
          onMouseLeave={() => setNewsHovered(false)}
        >
          Nouveautes
          <span style={updateDotStyle} />
        </button>
      </div>
    </div>
  );
}

export default RightPanel;
