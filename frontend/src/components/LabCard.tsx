import { Link } from 'react-router-dom';
import StatusBadge from './StatusBadge';
import DifficultyIndicator from './DifficultyIndicator';
import type { TaskCatalogItem } from '../types';

interface LabCardProps {
  task: TaskCatalogItem;
  status?: string;
}

export default function LabCard({ task, status }: LabCardProps) {
  const isCompleted = status === 'success';
  const isPending = status === 'pending';
  const badgeStatus =
    status === 'success'
      ? 'success'
      : status === 'fail'
        ? 'fail'
        : status === 'pending'
          ? 'pending'
          : 'available';

  return (
    <Link to={`/challenges/${task.id}`}>
      <article
        className={`bg-[#1a1b26] border-l-2 ${
          isCompleted
            ? 'border-primary'
            : isPending
              ? 'border-secondary'
              : 'border-outline-variant'
        } hover:border-2 hover:border-primary transition-all group flex flex-col p-6 relative overflow-hidden`}
      >
        <div className="flex justify-between items-start mb-6">
          <div className="flex flex-col gap-1">
            <span className="text-[10px] font-mono text-on-surface-variant uppercase tracking-tighter">
              LAB_ID: 0x{task.id.toString(16).padStart(3, '0')}
            </span>
            <h3 className="text-lg font-headline font-bold text-on-surface group-hover:text-primary transition-colors leading-tight">
              {task.title}
            </h3>
          </div>
          <StatusBadge status={badgeStatus} />
        </div>
        <div className="mb-6">
          <DifficultyIndicator level={task.difficulty} />
          <p className="text-sm text-on-surface-variant line-clamp-2 leading-relaxed font-body mt-3">
            {task.description}
          </p>
        </div>
        <div className="mt-auto flex flex-wrap gap-2">
          {task.tags.map((tag) => (
            <span
              key={tag}
              className="text-[9px] font-mono bg-surface-container-lowest px-2 py-1 text-secondary"
            >
              #{tag}
            </span>
          ))}
        </div>
      </article>
    </Link>
  );
}
