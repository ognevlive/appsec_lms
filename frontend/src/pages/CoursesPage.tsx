import { useEffect, useState } from 'react';
import { api } from '../api';
import type { CourseItem } from '../types';
import CourseCard from '../components/CourseCard';

export default function CoursesPage() {
  const [courses, setCourses] = useState<CourseItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listCourses().then(setCourses).finally(() => setLoading(false));
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
      <div className="mb-8">
        <h1 className="text-3xl md:text-4xl font-headline font-bold text-on-surface tracking-tighter uppercase mb-2">
          Курсы
        </h1>
        <p className="text-on-surface-variant text-sm max-w-2xl">
          Структурированные программы по безопасной разработке.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {courses.map(c => <CourseCard key={c.id} course={c} />)}
      </div>

      {courses.length === 0 && (
        <div className="text-center py-20 text-on-surface-variant">Нет доступных курсов</div>
      )}
    </div>
  );
}
