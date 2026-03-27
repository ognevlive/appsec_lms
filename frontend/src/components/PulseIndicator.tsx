interface PulseIndicatorProps {
  color?: 'primary' | 'tertiary' | 'secondary';
  size?: 'sm' | 'md';
}

const colorMap = {
  primary: 'bg-primary shadow-[0_0_8px_#8eff71]',
  tertiary: 'bg-tertiary shadow-[0_0_8px_#ff8b9f]',
  secondary: 'bg-secondary shadow-[0_0_8px_#59e3fe]',
};

const sizeMap = {
  sm: 'w-1.5 h-1.5',
  md: 'w-2 h-2',
};

export default function PulseIndicator({ color = 'primary', size = 'md' }: PulseIndicatorProps) {
  return <div className={`rounded-full ${colorMap[color]} ${sizeMap[size]}`} />;
}
