import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import type { TrackItem } from '../types';

export default function TracksPage() {
  const [tracks, setTracks] = useState<TrackItem[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    api.listTracks()
      .then(setTracks)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <span className="text-primary animate-pulse font-headline text-xl">Загрузка...</span>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-10">
        <h1 className="text-4xl md:text-5xl font-headline font-bold text-on-surface tracking-tighter uppercase mb-2">
          Треки обучения
        </h1>
        <p className="text-xs font-mono uppercase tracking-[0.2em] text-primary/80">
          Структурированные курсы с лабами и тестами <span className="animate-pulse">_</span>
        </p>
      </div>

      {tracks.length === 0 && (
        <div className="text-center py-20 text-on-surface-variant">
          Треки не найдены
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {tracks.map((track) => {
          const pct = track.step_count > 0
            ? Math.round((track.completed_count / track.step_count) * 100)
            : 0;
          const icon = track.config?.icon || 'route';

          return (
            <button
              key={track.id}
              onClick={() => navigate(`/tracks/${track.id}`)}
              className="text-left bg-surface-container-low border border-outline-variant/15 hover:border-primary/40 hover:bg-surface-container transition-all duration-150 p-6 group"
            >
              <div className="flex items-start gap-4 mb-4">
                <div className="w-10 h-10 bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0">
                  <span className="material-symbols-outlined text-primary text-xl">{icon}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <h2 className="font-headline font-bold text-on-surface text-lg leading-tight group-hover:text-primary transition-colors">
                    {track.title}
                  </h2>
                  <p className="text-on-surface-variant text-sm mt-1 line-clamp-2">
                    {track.description}
                  </p>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-[10px] font-mono uppercase tracking-widest text-on-surface-variant">
                    Прогресс
                  </span>
                  <span className="text-[10px] font-mono text-primary">
                    {track.completed_count}/{track.step_count}
                  </span>
                </div>
                <div className="h-1 bg-surface-container-high">
                  <div
                    className="h-full bg-primary transition-all duration-300"
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-[10px] font-mono uppercase tracking-widest text-on-surface-variant">
                    {track.step_count} {track.step_count === 1 ? 'шаг' : 'шагов'}
                  </span>
                  {pct === 100 && (
                    <span className="text-[10px] font-mono uppercase tracking-widest text-primary">
                      ✓ Завершён
                    </span>
                  )}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
