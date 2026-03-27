import { useEffect, useState } from 'react';
import { api } from '../../api';
import PulseIndicator from '../../components/PulseIndicator';

interface ContainerRow {
  id: number;
  user_id: number;
  task_id: number;
  domain: string;
  started_at: string;
  expires_at: string;
}

export default function AdminContainersPage() {
  const [containers, setContainers] = useState<ContainerRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listContainers()
      .then(setContainers)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-7xl mx-auto">
      <header className="mb-10">
        <h1 className="text-4xl font-headline font-bold text-on-surface uppercase tracking-tight leading-none mb-2">
          Контейнеры
        </h1>
        <p className="text-on-surface-variant text-xs uppercase tracking-[0.2em]">
          Активные лабораторные среды
        </p>
      </header>

      <div className="bg-surface-container overflow-hidden border border-outline-variant/5">
        {loading ? (
          <div className="py-12 text-center text-primary animate-pulse">Загрузка...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-surface-container-highest">
                  <th className="text-left text-[10px] uppercase tracking-widest font-bold text-on-surface-variant px-6 py-4">ID</th>
                  <th className="text-left text-[10px] uppercase tracking-widest font-bold text-on-surface-variant px-6 py-4">User ID</th>
                  <th className="text-left text-[10px] uppercase tracking-widest font-bold text-on-surface-variant px-6 py-4">Task ID</th>
                  <th className="text-left text-[10px] uppercase tracking-widest font-bold text-on-surface-variant px-6 py-4">Домен</th>
                  <th className="text-left text-[10px] uppercase tracking-widest font-bold text-on-surface-variant px-6 py-4">Запущен</th>
                  <th className="text-left text-[10px] uppercase tracking-widest font-bold text-on-surface-variant px-6 py-4">Истекает</th>
                  <th className="text-left text-[10px] uppercase tracking-widest font-bold text-on-surface-variant px-6 py-4">Статус</th>
                </tr>
              </thead>
              <tbody>
                {containers.map((c, idx) => (
                  <tr
                    key={c.id}
                    className={`${idx % 2 === 0 ? 'bg-[#1a1b26]' : 'bg-[#15161e]'} hover:bg-surface-bright transition-colors`}
                  >
                    <td className="px-6 py-3 text-xs font-mono text-on-surface-variant">{c.id}</td>
                    <td className="px-6 py-3 text-sm">{c.user_id}</td>
                    <td className="px-6 py-3 text-sm">{c.task_id}</td>
                    <td className="px-6 py-3">
                      <a
                        href={`http://${c.domain}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-secondary hover:text-primary text-sm font-mono transition-colors"
                      >
                        {c.domain}
                      </a>
                    </td>
                    <td className="px-6 py-3 text-xs font-mono text-on-surface-variant">
                      {new Date(c.started_at).toLocaleString('ru-RU')}
                    </td>
                    <td className="px-6 py-3 text-xs font-mono text-on-surface-variant">
                      {new Date(c.expires_at).toLocaleString('ru-RU')}
                    </td>
                    <td className="px-6 py-3">
                      <div className="flex items-center gap-2">
                        <PulseIndicator color="primary" size="sm" />
                        <span className="text-[9px] font-bold uppercase text-primary">Running</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {!loading && containers.length === 0 && (
          <div className="text-center py-12 text-on-surface-variant text-sm">
            Нет активных контейнеров
          </div>
        )}
      </div>

      <div className="mt-4 text-xs text-on-surface-variant">
        Всего: <strong className="text-on-surface">{containers.length}</strong>
      </div>
    </div>
  );
}
