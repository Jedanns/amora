import { type CSSProperties, type ButtonHTMLAttributes, useState } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'gold' | 'danger';
  size?: 'sm' | 'md' | 'lg';
}

const sizeMap: Record<NonNullable<ButtonProps['size']>, CSSProperties> = {
  sm: { padding: '4px 10px', fontSize: 11, borderRadius: 4 },
  md: { padding: '7px 16px', fontSize: 13, borderRadius: 6 },
  lg: { padding: '10px 24px', fontSize: 15, borderRadius: 8 },
};

interface VariantTokens {
  bg: string;
  bgHover: string;
  border: string;
  borderHover: string;
  color: string;
  glow: string;
}

const variants: Record<NonNullable<ButtonProps['variant']>, VariantTokens> = {
  primary: {
    bg: '#e94560',
    bgHover: '#ff5a75',
    border: '#e94560',
    borderHover: '#ff5a75',
    color: '#ffffff',
    glow: '0 0 12px rgba(233, 69, 96, 0.35)',
  },
  secondary: {
    bg: '#1a1a28',
    bgHover: '#252535',
    border: '#2a2a3a',
    borderHover: '#9898a8',
    color: '#e8e8f0',
    glow: 'none',
  },
  gold: {
    bg: '#c9a84c',
    bgHover: '#e5c55a',
    border: '#c9a84c',
    borderHover: '#e5c55a',
    color: '#0a0a0f',
    glow: '0 0 12px rgba(201, 168, 76, 0.3)',
  },
  danger: {
    bg: 'rgba(233, 69, 96, 0.15)',
    bgHover: 'rgba(233, 69, 96, 0.25)',
    border: '#e94560',
    borderHover: '#ff5a75',
    color: '#e94560',
    glow: '0 0 12px rgba(233, 69, 96, 0.25)',
  },
};

function buildStyle(
  variant: NonNullable<ButtonProps['variant']>,
  size: NonNullable<ButtonProps['size']>,
  hovered: boolean,
  disabled: boolean,
): CSSProperties {
  const v = variants[variant];
  const s = sizeMap[size];

  return {
    ...s,
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    fontFamily: 'inherit',
    fontWeight: 600,
    letterSpacing: '0.02em',
    lineHeight: 1.4,
    border: '1px solid',
    cursor: disabled ? 'not-allowed' : 'pointer',
    transition: 'all 0.2s ease',
    whiteSpace: 'nowrap',
    userSelect: 'none',
    opacity: disabled ? 0.45 : 1,
    backgroundColor: disabled ? v.bg : hovered ? v.bgHover : v.bg,
    borderColor: disabled ? v.border : hovered ? v.borderHover : v.border,
    color: v.color,
    boxShadow: !disabled && hovered ? v.glow : 'none',
  };
}

function Button({
  variant = 'secondary',
  size = 'md',
  disabled = false,
  style,
  children,
  ...rest
}: ButtonProps) {
  const [hovered, setHovered] = useState(false);

  const computedStyle: CSSProperties = {
    ...buildStyle(variant, size, hovered, !!disabled),
    ...style,
  };

  return (
    <button
      style={computedStyle}
      disabled={disabled}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      {...rest}
    >
      {children}
    </button>
  );
}

export default Button;
