import { Link } from 'react-router-dom';
import type { CourseItem } from '../types';

interface Props {
  course: CourseItem;
}

export default function CourseCard({ course }: Props) {
  const icon = (course.config?.icon as string) || 'school';
  const progression = (course.config?.progression as string) || 'free';
  return (
    <Link
      to={`/courses/${course.slug}`}
      className="block p-5 border border-outline-variant/20 bg-surface-container-low hover:border-primary/40 hover:bg-surface-container transition-all duration-150 group"
    >
      <div className="flex items-start gap-4 mb-3">
        <span className="material-symbols-outlined text-primary text-3xl">{icon}</span>
        <div className="flex-1 min-w-0">
          <h3 className="font-headline font-bold text-lg text-on-surface group-hover:text-primary transition-colors truncate">
            {course.title}
          </h3>
          <p className="text-[10px] font-mono uppercase tracking-widest text-on-surface-variant mt-1">
            {course.module_count} {course.module_count === 1 ? 'модуль' : 'модулей'} · {progression === 'linear' ? 'последовательно' : 'свободно'}
          </p>
        </div>
      </div>
      <p className="text-sm text-on-surface-variant line-clamp-2 mb-4">{course.description}</p>
      <div className="space-y-1.5">
        <div className="flex justify-between text-[10px] font-mono uppercase tracking-widest">
          <span className="text-on-surface-variant">Прогресс</span>
          <span className="text-primary">{course.completed_unit_count}/{course.unit_count}</span>
        </div>
        <div className="h-1.5 bg-surface-container-high">
          <div className="h-full bg-primary transition-all duration-500" style={{ width: `${course.progress_pct}%` }} />
        </div>
      </div>
    </Link>
  );
}
