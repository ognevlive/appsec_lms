interface Props { outcomes: string[]; }

export default function LearningOutcomesList({ outcomes }: Props) {
  if (!outcomes.length) return null;
  return (
    <ul className="space-y-1.5 mb-3">
      {outcomes.map((o, i) => (
        <li key={i} className="flex items-start gap-2 text-sm text-on-surface-variant">
          <span className="material-symbols-outlined text-primary text-base mt-0.5">check_circle</span>
          <span>{o}</span>
        </li>
      ))}
    </ul>
  );
}
