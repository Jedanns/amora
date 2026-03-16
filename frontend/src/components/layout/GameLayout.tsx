import type { CSSProperties, ReactNode } from 'react';

interface GameLayoutProps {
  header: ReactNode;
  leftPanel: ReactNode;
  mainArea: ReactNode;
  rightPanel: ReactNode;
}

const wrapperStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: '320px 1fr 280px',
  gridTemplateRows: '52px 1fr',
  width: '100vw',
  height: '100vh',
  backgroundColor: '#0a0a0f',
  gap: 1,
  overflow: 'hidden',
};

const headerStyle: CSSProperties = {
  gridColumn: '1 / -1',
  gridRow: '1',
  backgroundColor: '#151520',
  borderBottom: '1px solid #2a2a3a',
  minHeight: 0,
};

const leftStyle: CSSProperties = {
  gridColumn: '1',
  gridRow: '2',
  backgroundColor: '#151520',
  borderRight: '1px solid #2a2a3a',
  overflow: 'hidden',
  display: 'flex',
  flexDirection: 'column',
  minHeight: 0,
};

const mainStyle: CSSProperties = {
  gridColumn: '2',
  gridRow: '2',
  backgroundColor: '#0a0a0f',
  overflow: 'hidden',
  display: 'flex',
  flexDirection: 'column',
  minHeight: 0,
};

const rightStyle: CSSProperties = {
  gridColumn: '3',
  gridRow: '2',
  backgroundColor: '#151520',
  borderLeft: '1px solid #2a2a3a',
  overflow: 'hidden',
  display: 'flex',
  flexDirection: 'column',
  minHeight: 0,
};

function GameLayout({ header, leftPanel, mainArea, rightPanel }: GameLayoutProps) {
  return (
    <div style={wrapperStyle}>
      <div style={headerStyle}>{header}</div>
      <div style={leftStyle}>{leftPanel}</div>
      <div style={mainStyle}>{mainArea}</div>
      <div style={rightStyle}>{rightPanel}</div>
    </div>
  );
}

export default GameLayout;
