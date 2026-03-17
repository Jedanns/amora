import { useState, useCallback, type ComponentType } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface Tab {
  id: string;
  number: number;
  icon: ComponentType<{ size?: number; className?: string }>;
  label?: string;
}

interface TabBarProps {
  tabs: Tab[];
  activeTab: string;
  onTabChange: (id: string) => void;
}

function TabButton({ tab, isActive, onClick }: {
  tab: Tab;
  isActive: boolean;
  onClick: () => void;
}) {
  const Icon = tab.icon;

  return (
    <button
      className={`inline-flex items-center gap-1 px-3 py-[5px] rounded-full text-xs font-semibold border whitespace-nowrap select-none transition-all duration-200 cursor-pointer ${
        isActive
          ? 'bg-gold/12 border-gold text-gold shadow-[0_0_8px_rgba(201,168,76,0.15)]'
          : 'bg-transparent border-border-primary text-text-secondary hover:bg-bg-hover hover:border-text-secondary hover:text-text-primary'
      }`}
      onClick={onClick}
      aria-selected={isActive}
      role="tab"
    >
      <span>{tab.number}</span>
      <Icon size={14} />
      {tab.label && <span>{tab.label}</span>}
    </button>
  );
}

function TabBar({ tabs, activeTab, onTabChange }: TabBarProps) {
  const [collapsed, setCollapsed] = useState(false);

  const handleCollapse = useCallback(() => {
    setCollapsed(prev => !prev);
  }, []);

  if (collapsed) {
    return (
      <div className="flex items-center gap-1.5 px-2 py-1.5 bg-bg-panel border-b border-border-primary">
        <button
          className="inline-flex items-center justify-center w-7 h-7 rounded-full border border-border-primary bg-transparent text-text-secondary hover:border-text-secondary hover:text-text-primary transition-all duration-200 cursor-pointer ml-auto shrink-0"
          onClick={handleCollapse}
          aria-label="Expand tabs"
        >
          <ChevronRight size={13} />
        </button>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-1.5 px-2 py-1.5 bg-bg-panel border-b border-border-primary" role="tablist">
      {tabs.map(tab => (
        <TabButton
          key={tab.id}
          tab={tab}
          isActive={tab.id === activeTab}
          onClick={() => onTabChange(tab.id)}
        />
      ))}
      <button
        className="inline-flex items-center justify-center w-7 h-7 rounded-full border border-border-primary bg-transparent text-text-secondary hover:border-text-secondary hover:text-text-primary transition-all duration-200 cursor-pointer ml-auto shrink-0"
        onClick={handleCollapse}
        aria-label="Collapse tabs"
      >
        <ChevronLeft size={13} />
      </button>
    </div>
  );
}

export default TabBar;
