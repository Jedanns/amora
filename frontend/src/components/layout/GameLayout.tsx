import type { ReactNode } from 'react';

interface GameLayoutProps {
  header: ReactNode;
  leftPanel: ReactNode;
  mainArea: ReactNode;
  rightPanel: ReactNode;
}

function GameLayout({ header, leftPanel, mainArea, rightPanel }: GameLayoutProps) {
  return (
    <div className="grid grid-cols-[320px_1fr_280px] grid-rows-[52px_1fr] w-screen h-screen bg-bg-primary gap-px overflow-hidden">
      <div className="col-span-full row-start-1 bg-bg-panel border-b border-border-primary min-h-0">
        {header}
      </div>
      <div className="col-start-1 row-start-2 bg-bg-panel border-r border-border-primary overflow-hidden flex flex-col min-h-0">
        {leftPanel}
      </div>
      <div className="col-start-2 row-start-2 bg-bg-primary overflow-hidden flex flex-col min-h-0">
        {mainArea}
      </div>
      <div className="col-start-3 row-start-2 bg-bg-panel border-l border-border-primary overflow-hidden flex flex-col min-h-0">
        {rightPanel}
      </div>
    </div>
  );
}

export default GameLayout;
