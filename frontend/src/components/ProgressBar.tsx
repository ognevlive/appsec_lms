interface ProgressBarProps {
  value: number;
  size?: 'sm' | 'lg';
}

export default function ProgressBar({ value, size = 'lg' }: ProgressBarProps) {
  const height = size === 'lg' ? 'h-3' : 'h-1.5';
  return (
    <div className={`w-full ${height} bg-surface-container-highest rounded-sm overflow-hidden`}>
      <div
        className={`${height} bg-gradient-to-r from-primary to-primary-dim rounded-sm transition-all duration-500`}
        style={{
          width: `${Math.min(100, Math.max(0, value))}%`,
          boxShadow: '0 0 12px rgba(142, 255, 113, 0.3)',
        }}
      />
    </div>
  );
}
