import { useRef, useState } from 'react';

interface Props {
  maxFiles?: number;
  maxSizeMb?: number;
  allowedExt?: string[];
  required?: boolean;
  files: File[];
  onChange: (files: File[]) => void;
  disabled?: boolean;
}

const DEFAULT_EXT = ['pdf', 'png', 'jpg', 'zip', 'txt', 'md', 'docx', 'py', 'js', 'ts'];

export default function FileUploader({
  maxFiles = 5,
  maxSizeMb = 20,
  allowedExt,
  required = false,
  files,
  onChange,
  disabled,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);

  const exts = allowedExt && allowedExt.length ? allowedExt : DEFAULT_EXT;
  const accept = exts.map((e) => `.${e}`).join(',');

  function validate(list: File[]): string | null {
    if (list.length > maxFiles) return `Максимум файлов: ${maxFiles}`;
    for (const f of list) {
      const ext = f.name.split('.').pop()?.toLowerCase() || '';
      if (!exts.includes(ext)) return `Расширение .${ext} не разрешено`;
      if (f.size > maxSizeMb * 1024 * 1024) return `Файл ${f.name} больше ${maxSizeMb} МБ`;
    }
    return null;
  }

  function addFiles(incoming: FileList | File[]) {
    const merged = [...files, ...Array.from(incoming)];
    const err = validate(merged);
    if (err) {
      setError(err);
      return;
    }
    setError(null);
    onChange(merged);
  }

  function removeAt(i: number) {
    const next = files.slice();
    next.splice(i, 1);
    onChange(next);
  }

  return (
    <div className="space-y-2">
      <div
        className="border-2 border-dashed border-outline-variant/30 rounded p-4 text-center cursor-pointer hover:bg-surface-container-low"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          if (!disabled) addFiles(e.dataTransfer.files);
        }}
        onClick={() => !disabled && inputRef.current?.click()}
      >
        <p className="text-sm text-on-surface-variant">
          Перетащите файлы или нажмите, чтобы выбрать
        </p>
        <p className="text-xs text-on-surface-variant/60 mt-1">
          До {maxFiles} шт., макс {maxSizeMb} МБ; {exts.join(', ')}
          {required ? ' (обязательно)' : ''}
        </p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={accept}
          className="hidden"
          onChange={(e) => e.target.files && addFiles(e.target.files)}
        />
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      {files.length > 0 && (
        <ul className="text-sm space-y-1">
          {files.map((f, i) => (
            <li key={i} className="flex justify-between items-center bg-surface-container-low rounded px-3 py-1.5">
              <span className="truncate">{f.name} <span className="text-on-surface-variant/60 text-xs">({Math.round(f.size / 1024)} KB)</span></span>
              <button
                type="button"
                onClick={() => removeAt(i)}
                className="text-xs text-red-400 hover:underline"
                disabled={disabled}
              >
                удалить
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
