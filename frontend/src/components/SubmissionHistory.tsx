import { useState } from 'react';

interface Submission {
  id: number;
  status: 'pending' | 'success' | 'fail';
  submitted_at: string;
  review_comment?: string | null;
  files?: { id: number; filename: string }[];
}

interface Props {
  items: Submission[];
  downloadUrl: (submissionId: number, fileId: number) => string;
}

const statusLabel: Record<string, string> = {
  pending: 'На проверке',
  success: 'Зачтено',
  fail: 'Не зачтено',
};

const statusColor: Record<string, string> = {
  pending: 'text-yellow-300',
  success: 'text-primary',
  fail: 'text-red-400',
};

export default function SubmissionHistory({ items, downloadUrl }: Props) {
  const [open, setOpen] = useState(false);
  if (!items.length) return null;

  return (
    <details
      open={open}
      onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)}
      className="border border-outline-variant/20 rounded"
    >
      <summary className="px-3 py-2 cursor-pointer text-sm">
        История попыток ({items.length})
      </summary>
      <ul className="divide-y divide-outline-variant/20">
        {items.map((s) => (
          <li key={s.id} className="px-3 py-2 text-sm space-y-1">
            <div className="flex justify-between">
              <span className={statusColor[s.status]}>{statusLabel[s.status]}</span>
              <span className="text-on-surface-variant/60 text-xs">
                {new Date(s.submitted_at).toLocaleString()}
              </span>
            </div>
            {s.review_comment && (
              <p className="text-on-surface-variant text-xs whitespace-pre-wrap">
                {s.review_comment}
              </p>
            )}
            {s.files && s.files.length > 0 && (
              <ul className="text-xs space-x-2">
                {s.files.map((f) => (
                  <a
                    key={f.id}
                    href={downloadUrl(s.id, f.id)}
                    className="text-primary hover:underline"
                    target="_blank"
                    rel="noreferrer"
                  >
                    {f.filename}
                  </a>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ul>
    </details>
  );
}
