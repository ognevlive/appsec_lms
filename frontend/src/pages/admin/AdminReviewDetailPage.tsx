import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../../api';

interface SubmissionFile {
  id: number;
  filename: string;
  size_bytes: number;
}

interface Submission {
  id: number;
  user_id: number;
  task_id: number;
  status: 'pending' | 'success' | 'fail';
  details: Record<string, any>;
  submitted_at: string;
  reviewer_id: number | null;
  reviewed_at: string | null;
  review_comment: string | null;
  files: SubmissionFile[];
}

export default function AdminReviewDetailPage() {
  const { submissionId } = useParams();
  const navigate = useNavigate();
  const [sub, setSub] = useState<Submission | null>(null);
  const [task, setTask] = useState<any>(null);
  const [verdict, setVerdict] = useState<'success' | 'fail'>('success');
  const [comment, setComment] = useState('');
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      const id = Number(submissionId);
      const s = await api.getAdminSubmission(id);
      setSub(s);
      const t = await api.getTask(s.task_id);
      setTask(t);
    })();
  }, [submissionId]);

  async function submit() {
    if (!sub) return;
    setSaving(true);
    setErr(null);
    try {
      await api.reviewSubmission(sub.id, verdict, comment);
      navigate('/admin/review');
    } catch (e: any) {
      setErr(e.message || 'Ошибка');
    } finally {
      setSaving(false);
    }
  }

  if (!sub) return <div className="p-6 text-sm">Загрузка…</div>;

  const locked = sub.status !== 'pending' || sub.reviewer_id !== null;
  const auto = sub.details?.auto_score;

  return (
    <div className="p-6 space-y-4 max-w-3xl">
      <h1 className="text-2xl font-semibold">Проверка: {task?.title}</h1>
      <p className="text-sm text-on-surface-variant">
        Отправлено: {new Date(sub.submitted_at).toLocaleString()}
      </p>

      {sub.details?.answer_text && (
        <section>
          <h2 className="text-sm font-medium mb-1">Ответ студента</h2>
          <pre className="whitespace-pre-wrap bg-surface-container-low rounded p-3 text-sm">
            {sub.details.answer_text}
          </pre>
        </section>
      )}

      {auto && (
        <section className="text-sm">
          <h2 className="font-medium mb-1">Автопроверка (quiz)</h2>
          <p>Счёт: {auto.score} / {auto.total}. Правильно: {auto.correct.join(', ') || '—'}. Неверно: {auto.wrong.join(', ') || '—'}.</p>
        </section>
      )}

      {sub.files.length > 0 && (
        <section>
          <h2 className="text-sm font-medium mb-1">Файлы</h2>
          <ul className="space-y-1 text-sm">
            {sub.files.map((f) => (
              <li key={f.id}>
                <a
                  className="text-primary hover:underline"
                  href={api.fileDownloadUrl(sub.id, f.id, true)}
                  target="_blank"
                  rel="noreferrer"
                >
                  {f.filename}
                </a>
                <span className="text-on-surface-variant/60 text-xs ml-2">
                  {Math.round(f.size_bytes / 1024)} KB
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="space-y-2">
        <h2 className="text-sm font-medium">Вердикт</h2>
        {locked ? (
          <p className="text-sm text-on-surface-variant">
            Уже проверено: статус <b>{sub.status}</b>. Комментарий: {sub.review_comment || '—'}.
          </p>
        ) : (
          <>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="radio"
                checked={verdict === 'success'}
                onChange={() => setVerdict('success')}
              />
              Зачесть
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="radio"
                checked={verdict === 'fail'}
                onChange={() => setVerdict('fail')}
              />
              Не зачесть
            </label>
            <textarea
              rows={4}
              className="w-full bg-surface-container-low rounded p-3 text-sm"
              placeholder="Комментарий"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
            />
            {err && <p className="text-red-400 text-sm">{err}</p>}
            <button
              onClick={submit}
              disabled={saving}
              className="px-4 py-2 rounded bg-primary text-on-primary text-sm disabled:opacity-50"
            >
              {saving ? 'Сохраняем…' : 'Сохранить вердикт'}
            </button>
          </>
        )}
      </section>
    </div>
  );
}
