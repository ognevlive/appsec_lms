import { useEffect, useState } from 'react';
import { api } from '../api';
import ProgressBar from '../components/ProgressBar';
import PulseIndicator from '../components/PulseIndicator';
import type { ProgressData } from '../types';

export default function MyResultsPage() {
  const [data, setData] = useState<ProgressData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getProgress()
      .then(setData)
      .finally(() => setLoading(false));
  }, []);

  if (loading || !data) {
    return (
      <div className="flex items-center justify-center h-64">
        <span className="text-primary animate-pulse font-headline text-xl">Загрузка...</span>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Hero Progress Section */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-surface-container-low p-8 border border-outline-variant/10 relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-10">
            <span className="material-symbols-outlined text-[120px]">shield</span>
          </div>
          <div className="relative z-10">
            <span className="text-on-surface-variant font-label text-xs uppercase tracking-[0.2em]">
              Текущий статус
            </span>
            <h1 className="text-4xl md:text-6xl font-headline font-bold text-on-surface mt-2 mb-6 tracking-tight">
              Мой Прогресс
            </h1>
            <div className="flex items-end gap-4 mb-4">
              <span className="text-6xl font-headline font-bold text-primary">
                {data.progress_pct}%
              </span>
              <span className="text-on-surface-variant font-label pb-2 uppercase tracking-widest">
                пройдено обучения
              </span>
            </div>
            <ProgressBar value={data.progress_pct} />
          </div>
        </div>

        <div className="space-y-4">
          <div className="bg-surface-container-low p-6 border border-outline-variant/10 flex flex-col justify-between">
            <span className="text-on-surface-variant font-label text-[10px] uppercase tracking-widest flex items-center gap-2">
              <PulseIndicator size="sm" />
              Пройдено лаб
            </span>
            <div className="text-3xl font-headline font-bold mt-2">{data.completed_tasks}</div>
          </div>
          <div className="bg-surface-container-low p-6 border border-outline-variant/10 flex flex-col justify-between">
            <span className="text-on-surface-variant font-label text-[10px] uppercase tracking-widest">
              Всего баллов
            </span>
            <div className="text-3xl font-headline font-bold mt-2 text-secondary">
              {data.total_xp} <span className="text-sm font-label text-on-surface-variant font-normal">XP</span>
            </div>
          </div>
          <div className="bg-surface-container-low p-6 border border-outline-variant/10 flex flex-col justify-between">
            <span className="text-on-surface-variant font-label text-[10px] uppercase tracking-widest">
              Место в рейтинге
            </span>
            <div className="text-3xl font-headline font-bold mt-2">
              {data.rank}
              <span className="text-on-surface-variant font-normal text-xl">/{data.total_users}</span>
            </div>
          </div>
        </div>
      </section>

      {/* Middle Section */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Specialization */}
        <div className="lg:col-span-4 bg-surface-container-low p-6 border border-outline-variant/10 flex flex-col">
          <h3 className="text-sm font-headline font-bold uppercase tracking-widest mb-8 border-b border-outline-variant/15 pb-4">
            Специализация
          </h3>
          <div className="space-y-6 flex-grow">
            {data.specializations.map((spec) => (
              <div key={spec.name} className="space-y-2">
                <div className="flex justify-between text-xs font-label uppercase">
                  <span>{spec.name}</span>
                  <span className="text-primary">{spec.pct}%</span>
                </div>
                <ProgressBar value={spec.pct} size="sm" />
              </div>
            ))}
            {data.specializations.length === 0 && (
              <p className="text-on-surface-variant text-sm">Нет данных</p>
            )}
          </div>
        </div>

        {/* Activity Log */}
        <div className="lg:col-span-8 bg-surface-container-low p-6 border border-outline-variant/10">
          <h3 className="text-sm font-headline font-bold uppercase tracking-widest mb-6 border-b border-outline-variant/15 pb-4">
            Журнал активности
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-outline-variant/10">
                  <th className="text-left text-[10px] uppercase tracking-widest font-bold text-on-surface-variant pb-3">
                    Дата
                  </th>
                  <th className="text-left text-[10px] uppercase tracking-widest font-bold text-on-surface-variant pb-3">
                    Задание
                  </th>
                  <th className="text-left text-[10px] uppercase tracking-widest font-bold text-on-surface-variant pb-3">
                    Баллы
                  </th>
                  <th className="text-left text-[10px] uppercase tracking-widest font-bold text-on-surface-variant pb-3">
                    Статус
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.activity_log.map((item, idx) => (
                  <tr key={idx} className="border-b border-outline-variant/5 hover:bg-surface-bright/50 transition-colors">
                    <td className="py-3 text-xs font-mono text-on-surface-variant">
                      {item.date ? new Date(item.date).toLocaleDateString('ru-RU') : '—'}
                    </td>
                    <td className="py-3 text-sm text-on-surface">{item.task_title}</td>
                    <td className="py-3 text-sm font-bold text-primary">
                      {item.points > 0 ? `+${item.points}` : '—'}
                    </td>
                    <td className="py-3">
                      <span
                        className={`text-[9px] font-bold uppercase px-2 py-0.5 ${
                          item.status === 'success'
                            ? 'bg-primary/10 text-primary'
                            : item.status === 'fail'
                            ? 'bg-tertiary/10 text-tertiary'
                            : 'bg-secondary/10 text-secondary'
                        }`}
                      >
                        {item.status === 'success' ? 'Успех' : item.status === 'fail' ? 'Ошибка' : 'На проверке'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {data.activity_log.length === 0 && (
              <div className="text-center py-8 text-on-surface-variant text-sm">
                Нет активности
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
