import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { api } from '../api';
import type { TrackDetail, TrackStepItem } from '../types';

const TYPE_LABELS: Record<string, string> = {
  quiz: 'ТЕСТ',
  ctf: 'ЛАБ',
  gitlab: 'GITLAB',
};

const DIFFICULTY_LABELS: Record<string, string> = {
  low: 'Низкая',
  medium: 'Средняя',
  hard: 'Высокая',
  advanced: 'Продвинутый',
};

function StepRow({ step, index }: { step: TrackStepItem; index: number }) {
  const navigate = useNavigate();
  const isDone = step.user_status === 'success';
  const isFail = step.user_status === 'fail';
  const typeLabel = TYPE_LABELS[step.task_type] || step.task_type.toUpperCase();

  return (
    <button
      onClick={() => navigate(`/challenges/${step.task_id}`)}
      className="w-full text-left flex items-center gap-4 px-5 py-4 border border-outline-variant/15 hover:border-primary/40 hover:bg-surface-container transition-all duration-150 group bg-surface-container-low"
    >
      {/* Step number */}
      <div className={`w-8 h-8 flex-shrink-0 flex items-center justify-center border text-xs font-mono font-bold
        ${isDone ? 'border-primary bg-primary/10 text-primary' : 'border-outline-variant/30 text-on-surface-variant'}`}>
        {isDone ? (
          <span className="material-symbols-outlined text-base" style={{ fontVariationSettings: "'FILL' 1" }}>check</span>
        ) : (
          String(index + 1).padStart(2, '0')
        )}
      </div>

      {/* Type badge */}
      <span className={`flex-shrink-0 text-[9px] font-mono font-bold uppercase tracking-widest px-2 py-0.5 border
        ${step.task_type === 'quiz'
          ? 'border-blue-500/40 text-blue-400 bg-blue-500/5'
          : 'border-primary/40 text-primary bg-primary/5'}`}>
        {typeLabel}
      </span>

      {/* Title */}
      <span className="flex-1 font-body font-medium text-sm text-on-surface group-hover:text-primary transition-colors truncate">
        {step.task_title}
      </span>

      {/* Difficulty */}
      {step.task_difficulty && (
        <span className="flex-shrink-0 text-[10px] font-mono text-on-surface-variant hidden sm:block">
          {DIFFICULTY_LABELS[step.task_difficulty] || step.task_difficulty}
        </span>
      )}

      {/* Status */}
      <div className="flex-shrink-0 w-20 text-right">
        {isDone && (
          <span className="text-[10px] font-mono uppercase tracking-widest text-primary">Выполнено</span>
        )}
        {isFail && (
          <span className="text-[10px] font-mono uppercase tracking-widest text-error">Неверно</span>
        )}
        {!isDone && !isFail && (
          <span className="text-[10px] font-mono uppercase tracking-widest text-on-surface-variant">—</span>
        )}
      </div>

      {/* Arrow */}
      <span className="material-symbols-outlined text-on-surface-variant text-base flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
        chevron_right
      </span>
    </button>
  );
}

export default function TrackDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [track, setTrack] = useState<TrackDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    api.getTrack(Number(id))
      .then(setTrack)
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <span className="text-primary animate-pulse font-headline text-xl">Загрузка...</span>
      </div>
    );
  }

  if (!track) {
    return (
      <div className="text-center py-20 text-on-surface-variant">
        Трек не найден
      </div>
    );
  }

  const pct = track.step_count > 0
    ? Math.round((track.completed_count / track.step_count) * 100)
    : 0;

  return (
    <div>
      {/* Breadcrumb */}
      <div className="mb-6 flex items-center gap-2 text-[10px] font-mono uppercase tracking-widest text-on-surface-variant">
        <Link to="/tracks" className="hover:text-primary transition-colors">Треки</Link>
        <span>/</span>
        <span className="text-on-surface">{track.title}</span>
      </div>

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl md:text-4xl font-headline font-bold text-on-surface tracking-tighter uppercase mb-3">
          {track.title}
        </h1>
        <p className="text-on-surface-variant text-sm max-w-2xl mb-6">
          {track.description}
        </p>

        {/* Progress */}
        <div className="flex items-center gap-4 max-w-sm">
          <div className="flex-1 space-y-1.5">
            <div className="flex justify-between text-[10px] font-mono uppercase tracking-widest">
              <span className="text-on-surface-variant">Прогресс</span>
              <span className="text-primary">{track.completed_count}/{track.step_count}</span>
            </div>
            <div className="h-1.5 bg-surface-container-high">
              <div
                className="h-full bg-primary transition-all duration-500"
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
          <span className="text-2xl font-headline font-bold text-primary">{pct}%</span>
        </div>
      </div>

      {/* Steps */}
      <div className="space-y-2">
        {track.steps.map((step, index) => (
          <StepRow key={step.id} step={step} index={index} />
        ))}
      </div>

      {track.steps.length === 0 && (
        <div className="text-center py-20 text-on-surface-variant">
          В этом треке нет заданий
        </div>
      )}
    </div>
  );
}
