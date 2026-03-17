import type { ReactNode } from 'react';
import { hexToRgba } from '@/utils/colors';

interface BadgeProps {
  children: ReactNode;
  color?: string;
  variant?: 'filled' | 'outline';
}

function Badge({
  children,
  color = '#c9a84c',
  variant = 'filled',
}: BadgeProps) {
  const isFilled = variant === 'filled';

  return (
    <span
      className="inline-flex items-center justify-center px-2 py-px rounded-full text-[11px] font-semibold leading-snug tracking-wide whitespace-nowrap select-none border"
      style={{
        backgroundColor: isFilled ? hexToRgba(color, 0.18) : 'transparent',
        borderColor: isFilled ? hexToRgba(color, 0.3) : color,
        color,
      }}
    >
      {children}
    </span>
  );
}

export default Badge;
