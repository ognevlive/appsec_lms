import type { ButtonHTMLAttributes } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger';
  size?: 'sm' | 'md' | 'lg';
}

const variants = {
  primary:
    'bg-gradient-to-br from-primary to-primary-dim text-on-primary font-bold hover:brightness-110 active:scale-95',
  secondary:
    'bg-surface-container-high text-on-surface-variant border border-outline-variant/20 hover:bg-surface-bright hover:text-on-surface',
  danger:
    'bg-error-container/20 text-error border border-error/20 hover:bg-error-container/30',
};

const sizes = {
  sm: 'h-8 px-3 text-[10px]',
  md: 'h-10 px-4 text-xs',
  lg: 'h-12 px-6 text-sm',
};

export default function Button({
  variant = 'primary',
  size = 'md',
  className = '',
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 uppercase tracking-widest transition-all duration-150 font-bold ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
