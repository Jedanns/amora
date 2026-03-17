import type { ButtonHTMLAttributes } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'gold' | 'danger';
  size?: 'sm' | 'md' | 'lg';
}

const sizeClasses: Record<NonNullable<ButtonProps['size']>, string> = {
  sm: 'px-2.5 py-1 text-[11px] rounded-sm',
  md: 'px-4 py-[7px] text-[13px] rounded-md',
  lg: 'px-6 py-2.5 text-[15px] rounded-lg',
};

const variantClasses: Record<NonNullable<ButtonProps['variant']>, string> = {
  primary:
    'bg-red text-white border-red hover:bg-red-bright hover:border-red-bright hover:shadow-[0_0_12px_rgba(233,69,96,0.35)]',
  secondary:
    'bg-bg-card text-text-primary border-border-primary hover:bg-bg-hover hover:border-text-secondary',
  gold:
    'bg-gold text-bg-primary border-gold hover:bg-gold-bright hover:border-gold-bright hover:shadow-gold',
  danger:
    'bg-red/15 text-red border-red hover:bg-red/25 hover:border-red-bright hover:shadow-[0_0_12px_rgba(233,69,96,0.25)]',
};

function Button({
  variant = 'secondary',
  size = 'md',
  disabled = false,
  className = '',
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-1.5 font-semibold tracking-wide leading-snug border whitespace-nowrap select-none transition-all duration-200 ${sizeClasses[size]} ${variantClasses[variant]} ${disabled ? 'opacity-45 cursor-not-allowed' : 'cursor-pointer'} ${className}`}
      disabled={disabled}
      {...rest}
    >
      {children}
    </button>
  );
}

export default Button;
