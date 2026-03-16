import { type CSSProperties, useState } from 'react';

interface GameHeaderProps {
  location?: string;
  timeOfDay?: string;
  isConnected: boolean;
  modelName?: string;
  onMenuClick?: () => void;
}

const headerContainer: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  height: '100%',
  padding: '0 16px',
  backgroundColor: '#151520',
  fontFamily: 'inherit',
};

const titleStyle: CSSProperties = {
  fontSize: 14,
  fontWeight: 700,
  letterSpacing: '0.12em',
  color: '#c9a84c',
  textTransform: 'uppercase',
  whiteSpace: 'nowrap',
  userSelect: 'none',
};

const centerStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 6,
  fontSize: 12,
  color: '#9898a8',
  letterSpacing: '0.04em',
};

const separatorStyle: CSSProperties = {
  color: '#2a2a3a',
  userSelect: 'none',
};

const rightGroupStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 12,
};

const statusStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 6,
  fontSize: 11,
  fontWeight: 600,
  letterSpacing: '0.04em',
};

function statusDot(connected: boolean): CSSProperties {
  return {
    width: 7,
    height: 7,
    borderRadius: '50%',
    backgroundColor: connected ? '#53d769' : '#e94560',
    boxShadow: connected
      ? '0 0 6px rgba(83, 215, 105, 0.5)'
      : '0 0 6px rgba(233, 69, 96, 0.5)',
    flexShrink: 0,
  };
}

const menuButtonBase: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  width: 32,
  height: 32,
  border: '1px solid #2a2a3a',
  borderRadius: 6,
  backgroundColor: 'transparent',
  color: '#9898a8',
  fontSize: 16,
  cursor: 'pointer',
  transition: 'all 0.2s ease',
  padding: 0,
  fontFamily: 'inherit',
  lineHeight: 1,
};

function GameHeader({
  location,
  timeOfDay,
  isConnected,
  modelName,
  onMenuClick,
}: GameHeaderProps) {
  const [menuHovered, setMenuHovered] = useState(false);

  const menuStyle: CSSProperties = {
    ...menuButtonBase,
    borderColor: menuHovered ? '#9898a8' : '#2a2a3a',
    color: menuHovered ? '#e8e8f0' : '#9898a8',
    backgroundColor: menuHovered ? '#1a1a28' : 'transparent',
  };

  const parts = [location, timeOfDay].filter(Boolean);

  return (
    <div style={headerContainer}>
      <span style={titleStyle}>TAVERNE DU VIEUX GREG</span>

      <div style={centerStyle}>
        {parts.length > 0 ? (
          parts.map((part, i) => (
            <span key={i}>
              {i > 0 && <span style={separatorStyle}> &middot; </span>}
              {part}
            </span>
          ))
        ) : (
          <span style={{ color: '#2a2a3a' }}>---</span>
        )}
        {modelName && (
          <>
            <span style={separatorStyle}> &middot; </span>
            <span style={{ color: '#4a9eff', fontSize: 10 }}>{modelName}</span>
          </>
        )}
      </div>

      <div style={rightGroupStyle}>
        <div style={statusStyle}>
          <span style={statusDot(isConnected)} />
          <span style={{ color: isConnected ? '#53d769' : '#e94560' }}>
            {isConnected ? 'Connecte' : 'Deconnecte'}
          </span>
        </div>

        <button
          style={menuStyle}
          onClick={onMenuClick}
          onMouseEnter={() => setMenuHovered(true)}
          onMouseLeave={() => setMenuHovered(false)}
          aria-label="Menu"
        >
          &#9776;
        </button>
      </div>
    </div>
  );
}

export default GameHeader;
