import { type CSSProperties, useState, useCallback } from 'react';

interface Tab {
  id: string;
  number: number;
  icon: string;
  label?: string;
}

interface TabBarProps {
  tabs: Tab[];
  activeTab: string;
  onTabChange: (id: string) => void;
}

const baseTabStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 4,
  padding: '5px 12px',
  border: '1px solid',
  borderRadius: 999,
  fontSize: 12,
  fontWeight: 600,
  cursor: 'pointer',
  transition: 'all 0.2s ease',
  whiteSpace: 'nowrap',
  userSelect: 'none',
  fontFamily: 'inherit',
  lineHeight: 1.4,
};

function getTabStyle(isActive: boolean, isHovered: boolean): CSSProperties {
  if (isActive) {
    return {
      ...baseTabStyle,
      backgroundColor: 'rgba(201, 168, 76, 0.12)',
      borderColor: '#c9a84c',
      color: '#c9a84c',
      boxShadow: '0 0 8px rgba(201, 168, 76, 0.15)',
    };
  }
  return {
    ...baseTabStyle,
    backgroundColor: isHovered ? '#252535' : 'transparent',
    borderColor: isHovered ? '#9898a8' : '#2a2a3a',
    color: isHovered ? '#e8e8f0' : '#9898a8',
  };
}

const containerStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 6,
  padding: '6px 8px',
  backgroundColor: '#151520',
  borderBottom: '1px solid #2a2a3a',
};

const chevronBase: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  width: 28,
  height: 28,
  border: '1px solid #2a2a3a',
  borderRadius: 999,
  backgroundColor: 'transparent',
  color: '#9898a8',
  fontSize: 13,
  cursor: 'pointer',
  transition: 'all 0.2s ease',
  marginLeft: 'auto',
  flexShrink: 0,
  fontFamily: 'inherit',
  lineHeight: 1,
  padding: 0,
};

function TabButton({ tab, isActive, onClick }: {
  tab: Tab;
  isActive: boolean;
  onClick: () => void;
}) {
  const [hovered, setHovered] = useState(false);

  return (
    <button
      style={getTabStyle(isActive, hovered)}
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      aria-selected={isActive}
      role="tab"
    >
      <span>{tab.number}</span>
      <span>{tab.icon}</span>
      {tab.label && <span>{tab.label}</span>}
    </button>
  );
}

function TabBar({ tabs, activeTab, onTabChange }: TabBarProps) {
  const [chevronHovered, setChevronHovered] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  const handleCollapse = useCallback(() => {
    setCollapsed(prev => !prev);
  }, []);

  const chevronStyle: CSSProperties = {
    ...chevronBase,
    borderColor: chevronHovered ? '#9898a8' : '#2a2a3a',
    color: chevronHovered ? '#e8e8f0' : '#9898a8',
    transform: collapsed ? 'rotate(180deg)' : 'none',
  };

  if (collapsed) {
    return (
      <div style={containerStyle}>
        <button
          style={chevronStyle}
          onClick={handleCollapse}
          onMouseEnter={() => setChevronHovered(true)}
          onMouseLeave={() => setChevronHovered(false)}
          aria-label="Expand tabs"
        >
          &#8250;
        </button>
      </div>
    );
  }

  return (
    <div style={containerStyle} role="tablist">
      {tabs.map(tab => (
        <TabButton
          key={tab.id}
          tab={tab}
          isActive={tab.id === activeTab}
          onClick={() => onTabChange(tab.id)}
        />
      ))}
      <button
        style={chevronStyle}
        onClick={handleCollapse}
        onMouseEnter={() => setChevronHovered(true)}
        onMouseLeave={() => setChevronHovered(false)}
        aria-label="Collapse tabs"
      >
        &#8249;
      </button>
    </div>
  );
}

export default TabBar;
