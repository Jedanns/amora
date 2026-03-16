import type { CSSProperties, ReactNode } from 'react';

interface BadgeProps {
  children: ReactNode;
  color?: string;
  variant?: 'filled' | 'outline';
}

function hexToRgba(hex: string, alpha: number): string {
  const cleaned = hex.replace('#', '');
  const r = parseInt(cleaned.substring(0, 2), 16);
  const g = parseInt(cleaned.substring(2, 4), 16);
  const b = parseInt(cleaned.substring(4, 6), 16);
  if (isNaN(r) || isNaN(g) || isNaN(b)) return hex;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function buildStyle(
  variant: NonNullable<BadgeProps['variant']>,
  color: string,
): CSSProperties {
  const base: CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '2px 8px',
    borderRadius: 999,
    fontSize: 11,
    fontWeight: 600,
    lineHeight: 1.5,
    letterSpacing: '0.02em',
    whiteSpace: 'nowrap',
    userSelect: 'none',
    border: '1px solid',
  };

  if (variant === 'filled') {
    return {
      ...base,
      backgroundColor: hexToRgba(color, 0.18),
      borderColor: hexToRgba(color, 0.3),
      color,
    };
  }

  return {
    ...base,
    backgroundColor: 'transparent',
    borderColor: color,
    color,
  };
}

function Badge({
  children,
  color = '#c9a84c',
  variant = 'filled',
}: BadgeProps) {
  return (
    <span style={buildStyle(variant, color)}>
      {children}
    </span>
  );
}

export default Badge;
