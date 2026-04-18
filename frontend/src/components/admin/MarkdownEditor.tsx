import { Md } from '../Md';

export default function MarkdownEditor({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="grid grid-cols-2 gap-4">
      <textarea
        className="h-96 font-mono text-sm p-3 bg-surface-container-low"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      <div className="h-96 overflow-auto p-3 bg-surface-container-low">
        <Md>{value}</Md>
      </div>
    </div>
  );
}
