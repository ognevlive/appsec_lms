interface DifficultyIndicatorProps {
  level: string | null;
}

const difficultyConfig: Record<string, { label: string; color: string }> = {
  low: { label: 'Низкая', color: 'text-primary bg-primary/5' },
  medium: { label: 'Средняя', color: 'text-secondary bg-secondary/5' },
  high: { label: 'Высокая', color: 'text-tertiary bg-tertiary/5' },
};

export default function DifficultyIndicator({ level }: DifficultyIndicatorProps) {
  if (!level) return null;
  const config = difficultyConfig[level] || difficultyConfig.low;
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] uppercase font-bold text-on-surface-variant">Сложность:</span>
      <span className={`text-[10px] font-bold uppercase px-2 py-0.5 ${config.color}`}>
        {config.label}
      </span>
    </div>
  );
}
