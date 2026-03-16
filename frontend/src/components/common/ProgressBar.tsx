import type { CSSProperties } from 'react';

interface ProgressBarProps {
  current: number;
  max: number;
  color?: string;
  height?: number;
  showLabel?: boolean;
  label?: string;
  labelColor?: string;
}

const styles = {
  container: {
    width: '100%',
  } satisfies CSSProperties,

  labelRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    marginBottom: 4,
    fontSize: 11,
    fontWeight: 500,
    letterSpacing: '0.02em',
  } satisfies CSSProperties,

  track: (height: number): CSSProperties => ({
    width: '100%',
    height,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: height / 2,
    overflow: 'hidden',
    position: 'relative',
  }),

  fill: (percent: number, color: string, height: number): CSSProperties => ({
    width: `${Math.min(100, Math.max(0, percent))}%`,
    height: '100%',
    backgroundColor: color,
    borderRadius: height / 2,
    transition: 'width 0.4s ease',
    boxShadow: percent > 0 ? `0 0 6px ${color}40` : 'none',
  }),
};

function ProgressBar({
  current,
  max,
  color = '#c9a84c',
  height = 6,
  showLabel = false,
  label,
  labelColor,
}: ProgressBarProps) {
  const percent = max > 0 ? (current / max) * 100 : 0;

  return (
    <div style={styles.container}>
      {showLabel && (
        <div style={styles.labelRow}>
          <span style={{ color: labelColor ?? '#9898a8' }}>
            {label ?? ''}
          </span>
          <span style={{ color: labelColor ?? '#9898a8' }}>
            {current}/{max}
          </span>
        </div>
      )}
      <div style={styles.track(height)}>
        <div style={styles.fill(percent, color, height)} />
      </div>
    </div>
  );
}

export default ProgressBar;
