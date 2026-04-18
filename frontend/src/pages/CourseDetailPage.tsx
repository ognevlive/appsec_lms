import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../api';
import type { CourseDetail } from '../types';
import ModuleAccordion from '../components/ModuleAccordion';
import UnitRow from '../components/UnitRow';

export default function CourseDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const [course, setCourse] = useState<CourseDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!slug) return;
    api.getCourse(slug).then(setCourse).finally(() => setLoading(false));
  }, [slug]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <span className="text-primary animate-pulse font-headline text-xl">Загрузка...</span>
      </div>
    );
  }

  if (!course) {
    return <div className="text-center py-20 text-on-surface-variant">Курс не найден</div>;
  }

  const flatRender = course.modules.length === 1 && !course.modules[0].description;

  const defaultOpenIdx = course.modules.findIndex(m => !m.is_locked && m.completed_unit_count < m.unit_count);

  const totalHours = course.modules.reduce((sum, m) => sum + (m.estimated_hours || 0), 0);
  const hoursKnown = course.modules.filter(m => m.estimated_hours !== null && m.estimated_hours !== undefined).length;
  const showHours = hoursKnown >= Math.ceil(course.modules.length / 2);

  return (
    <div>
      <div className="mb-6 flex items-center gap-2 text-[10px] font-mono uppercase tracking-widest text-on-surface-variant">
        <Link to="/courses" className="hover:text-primary transition-colors">Курсы</Link>
        <span>/</span>
        <span className="text-on-surface">{course.title}</span>
      </div>

      <div className="mb-8">
        <h1 className="text-3xl md:text-4xl font-headline font-bold text-on-surface tracking-tighter uppercase mb-3">
          {course.title}
        </h1>
        <p className="text-on-surface-variant text-sm max-w-2xl mb-6">{course.description}</p>

        <div className="flex items-center gap-6 flex-wrap">
          <div className="flex items-center gap-4 max-w-sm min-w-[16rem]">
            <div className="flex-1 space-y-1.5">
              <div className="flex justify-between text-[10px] font-mono uppercase tracking-widest">
                <span className="text-on-surface-variant">Прогресс</span>
                <span className="text-primary">{course.completed_unit_count}/{course.unit_count}</span>
              </div>
              <div className="h-1.5 bg-surface-container-high">
                <div className="h-full bg-primary transition-all duration-500" style={{ width: `${course.progress_pct}%` }} />
              </div>
            </div>
            <span className="text-2xl font-headline font-bold text-primary">{course.progress_pct}%</span>
          </div>

          {showHours && totalHours > 0 && (
            <div className="text-[10px] font-mono uppercase tracking-widest text-on-surface-variant">
              ⏱ ~{totalHours} часов суммарно
            </div>
          )}
        </div>
      </div>

      {flatRender ? (
        <div className="space-y-2">
          {course.modules[0].units.map((unit, i) => (
            <UnitRow key={unit.id} unit={unit} index={unit.task_type === 'theory' ? 0 : i + 1} />
          ))}
        </div>
      ) : (
        <div className="space-y-3">
          {course.modules.map((m, idx) => (
            <ModuleAccordion
              key={m.id}
              module={m}
              defaultOpen={idx === defaultOpenIdx}
            />
          ))}
        </div>
      )}

      {course.modules.length === 0 && (
        <div className="text-center py-20 text-on-surface-variant">В этом курсе нет модулей</div>
      )}
    </div>
  );
}
