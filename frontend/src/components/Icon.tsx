interface IconProps {
  name: string;
  filled?: boolean;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

const sizeMap = { sm: 'text-sm', md: 'text-xl', lg: 'text-2xl' };

export default function Icon({ name, filled, className = '', size = 'md' }: IconProps) {
  return (
    <span
      className={`material-symbols-outlined ${sizeMap[size]} ${className}`}
      style={filled ? { fontVariationSettings: "'FILL' 1" } : undefined}
    >
      {name}
    </span>
  );
}
