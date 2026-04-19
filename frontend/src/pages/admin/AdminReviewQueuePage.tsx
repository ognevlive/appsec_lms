import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../../api';

interface QueueItem {
  submission_id: number;
  task_id: number;
  task_title: string;
  user_id: number;
  username: string;
  user_full_name: string;
  submitted_at: string;
  course_id: number | null;
  course_title: string | null;
}

export default function AdminReviewQueuePage() {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [perPage] = useState(20);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const data = await api.getReviewQueue({ page, per_page: perPage });
      setItems(data.items);
      setTotal(data.total);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [page]);

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-semibold">Проверка работ</h1>
      {loading ? (
        <p className="text-sm text-on-surface-variant">Загрузка…</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-on-surface-variant">Очередь пуста.</p>
      ) : (
        <table className="w-full text-sm">
          <thead className="text-left text-on-surface-variant">
            <tr>
              <th className="py-2">Студент</th>
              <th>Задача</th>
              <th>Курс</th>
              <th>Отправлено</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((it) => (
              <tr key={it.submission_id} className="border-t border-outline-variant/20">
                <td className="py-2">{it.user_full_name || it.username}</td>
                <td>{it.task_title}</td>
                <td>{it.course_title || '—'}</td>
                <td>{new Date(it.submitted_at).toLocaleString()}</td>
                <td>
                  <Link
                    to={`/admin/review/${it.submission_id}`}
                    className="text-primary hover:underline"
                  >
                    Проверить
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <div className="flex gap-2 items-center text-sm">
        <button
          disabled={page <= 1}
          onClick={() => setPage((p) => p - 1)}
          className="px-2 py-1 rounded bg-surface-container-low disabled:opacity-50"
        >
          ← Назад
        </button>
        <span>
          {page} / {Math.max(1, Math.ceil(total / perPage))}
        </span>
        <button
          disabled={page * perPage >= total}
          onClick={() => setPage((p) => p + 1)}
          className="px-2 py-1 rounded bg-surface-container-low disabled:opacity-50"
        >
          Вперёд →
        </button>
      </div>
    </div>
  );
}
