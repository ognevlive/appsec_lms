import { useEffect, useState } from 'react';
import { api } from '../api';
import LabCard from '../components/LabCard';
import Pagination from '../components/Pagination';
import Icon from '../components/Icon';
import type { TaskCatalogItem, TaskStatuses } from '../types';

const ITEMS_PER_PAGE = 9;

export default function CatalogPage() {
  const [tasks, setTasks] = useState<TaskCatalogItem[]>([]);
  const [statuses, setStatuses] = useState<TaskStatuses>({});
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.listTasks(), api.getTaskStatuses()])
      .then(([t, s]) => {
        setTasks(t);
        setStatuses(s);
      })
      .finally(() => setLoading(false));
  }, []);

  const totalPages = Math.ceil(tasks.length / ITEMS_PER_PAGE);
  const paginatedTasks = tasks.slice((page - 1) * ITEMS_PER_PAGE, page * ITEMS_PER_PAGE);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <span className="text-primary animate-pulse font-headline text-xl">Загрузка...</span>
      </div>
    );
  }

  return (
    <div>
      {/* Section Header */}
      <div className="mb-10 flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-4xl md:text-5xl font-headline font-bold text-on-surface tracking-tighter uppercase mb-2">
            Каталог испытаний
          </h1>
          <p className="text-xs font-mono uppercase tracking-[0.2em] text-primary/80">
            Выберите цель для атаки <span className="animate-pulse">_</span>
          </p>
        </div>
        <div className="flex gap-2">
          <button className="bg-surface-container-high hover:bg-surface-bright px-4 py-2 border border-outline-variant/20 flex items-center gap-2 transition-colors">
            <Icon name="filter_list" size="sm" />
            <span className="text-[10px] font-bold uppercase tracking-widest">Фильтры</span>
          </button>
        </div>
      </div>

      {/* Bento Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {paginatedTasks.map((task) => (
          <LabCard key={task.id} task={task} status={statuses[task.id]} />
        ))}
      </div>

      {tasks.length === 0 && (
        <div className="text-center py-20 text-on-surface-variant">
          Задания не найдены
        </div>
      )}

      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
    </div>
  );
}
