import { useNavigate } from 'react-router-dom';
import type { UnitItem } from '../types';

const TYPE_LABELS: Record<string, string> = {
  quiz: 'ТЕСТ',
  ctf: 'ЛАБ',
  gitlab: 'GITLAB',
  theory: 'ТЕОРИЯ',
  ssh_lab: 'SSH',
};

const DIFFICULTY_LABELS: Record<string, string> = {
  low: 'Низкая',
  medium: 'Средняя',
  hard: 'Высокая',
  advanced: 'Продвинутый',
};

interface UnitRowProps {
  unit: UnitItem;
  index: number;
  locked?: boolean;
}

export default function UnitRow({ unit, index, locked = false }: UnitRowProps) {
  const navigate = useNavigate();
  const isTheory = unit.task_type === 'theory';
  const isDone = unit.user_status === 'success';
  const isFail = unit.user_status === 'fail';
  const isPending = unit.user_status === 'pending';
  const typeLabel = TYPE_LABELS[unit.task_type] || unit.task_type.toUpperCase();

  const handleClick = () => {
    if (locked) return;
    navigate(`/challenges/${unit.task_id}`);
  };

  return (
    <button
      onClick={handleClick}
      disabled={locked}
      className={`w-full text-left flex items-center gap-4 px-5 py-4 border transition-all duration-150 group
        ${locked
          ? 'border-outline-variant/10 bg-surface-container-low/30 opacity-60 cursor-not-allowed'
          : isTheory
            ? 'border-amber-500/15 hover:border-amber-500/40 hover:bg-surface-container bg-surface-container-low/60'
            : 'border-outline-variant/15 hover:border-primary/40 hover:bg-surface-container bg-surface-container-low'
        }`}
    >
      <div className={`w-8 h-8 flex-shrink-0 flex items-center justify-center border text-xs font-mono font-bold
        ${isTheory
          ? 'border-amber-500/30 text-amber-400'
          : isDone
            ? 'border-primary bg-primary/10 text-primary'
            : isPending
              ? 'border-secondary/50 bg-secondary/10 text-secondary'
              : 'border-outline-variant/30 text-on-surface-variant'
        }`}>
        {isTheory ? (
          <span className="material-symbols-outlined text-base">menu_book</span>
        ) : isDone ? (
          <span className="material-symbols-outlined text-base" style={{ fontVariationSettings: "'FILL' 1" }}>check</span>
        ) : isPending ? (
          <span className="material-symbols-outlined text-base" style={{ fontVariationSettings: "'FILL' 1" }}>hourglass_top</span>
        ) : (
          String(index).padStart(2, '0')
        )}
      </div>

      <span className={`flex-shrink-0 text-[9px] font-mono font-bold uppercase tracking-widest px-2 py-0.5 border
        ${isTheory
          ? 'border-amber-500/40 text-amber-400 bg-amber-500/5'
          : unit.task_type === 'quiz'
            ? 'border-blue-500/40 text-blue-400 bg-blue-500/5'
            : 'border-primary/40 text-primary bg-primary/5'
        }`}>
        {typeLabel}
      </span>

      <span className={`flex-1 font-body font-medium text-sm truncate transition-colors
        ${isTheory
          ? 'text-on-surface-variant group-hover:text-amber-400'
          : 'text-on-surface group-hover:text-primary'
        }`}>
        {unit.task_title}
      </span>

      {!isTheory && unit.task_difficulty && (
        <span className="flex-shrink-0 text-[10px] font-mono text-on-surface-variant hidden sm:block">
          {DIFFICULTY_LABELS[unit.task_difficulty] || unit.task_difficulty}
        </span>
      )}

      {!isTheory && (
        <div className="flex-shrink-0 w-24 text-right">
          {isDone && (
            <span className="text-[10px] font-mono uppercase tracking-widest text-primary">Выполнено</span>
          )}
          {isFail && (
            <span className="text-[10px] font-mono uppercase tracking-widest text-error">Неверно</span>
          )}
          {isPending && (
            <span className="text-[10px] font-mono uppercase tracking-widest text-secondary">На проверке</span>
          )}
          {!isDone && !isFail && !isPending && (
            <span className="text-[10px] font-mono uppercase tracking-widest text-on-surface-variant">—</span>
          )}
        </div>
      )}

      {locked ? (
        <span className="material-symbols-outlined text-on-surface-variant text-base flex-shrink-0">lock</span>
      ) : (
        <span className="material-symbols-outlined text-on-surface-variant text-base flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
          chevron_right
        </span>
      )}
    </button>
  );
}
