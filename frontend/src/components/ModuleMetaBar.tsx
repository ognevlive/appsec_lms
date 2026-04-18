interface Props {
  estimatedHours: number | null;
  outcomesCount: number;
}

export default function ModuleMetaBar({ estimatedHours, outcomesCount }: Props) {
  const parts: string[] = [];
  if (estimatedHours !== null && estimatedHours !== undefined) {
    parts.push(`⏱ ~${estimatedHours} ${estimatedHours === 1 ? 'час' : 'часа/часов'}`);
  }
  if (outcomesCount > 0) {
    parts.push(`🎯 ${outcomesCount} ${outcomesCount === 1 ? 'цель' : 'цели'}`);
  }
  if (!parts.length) return null;
  return (
    <div className="text-[10px] font-mono uppercase tracking-widest text-on-surface-variant mb-3">
      {parts.join(' · ')}
    </div>
  );
}
