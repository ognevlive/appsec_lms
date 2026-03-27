import type { InputHTMLAttributes } from 'react';

interface FormInputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
}

export default function FormInput({ label, className = '', ...props }: FormInputProps) {
  return (
    <div className="space-y-1">
      {label && (
        <label className="text-[10px] uppercase tracking-wider text-on-surface-variant font-bold ml-1">
          {label}
        </label>
      )}
      <input
        className={`w-full h-10 bg-surface-container-lowest border border-outline-variant/30 text-sm text-on-surface focus:border-primary focus:ring-0 focus:outline-none transition-colors placeholder:text-outline-variant px-3 ${className}`}
        {...props}
      />
    </div>
  );
}
