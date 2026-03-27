import type { SelectHTMLAttributes } from 'react';

interface FormSelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options: { value: string; label: string }[];
}

export default function FormSelect({ label, options, className = '', ...props }: FormSelectProps) {
  return (
    <div className="space-y-1">
      {label && (
        <label className="text-[10px] uppercase tracking-wider text-on-surface-variant font-bold ml-1">
          {label}
        </label>
      )}
      <select
        className={`w-full h-10 bg-surface-container-lowest border border-outline-variant/30 text-sm text-on-surface focus:border-primary focus:ring-0 focus:outline-none transition-colors appearance-none px-3 ${className}`}
        {...props}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}
