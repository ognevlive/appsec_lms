import { useEffect, useState, useMemo } from 'react';
import { api } from '../api';
import LabCard from '../components/LabCard';
import Pagination from '../components/Pagination';
import Icon from '../components/Icon';
import type { TaskCatalogItem, TaskStatuses } from '../types';

const ITEMS_PER_PAGE = 9;

const TYPE_LABELS: Record<string, string> = {
  quiz: 'Quiz',
  ctf: 'CTF',
  gitlab: 'GitLab',
};

export default function CatalogPage() {
  const [tasks, setTasks] = useState<TaskCatalogItem[]>([]);
  const [statuses, setStatuses] = useState<TaskStatuses>({});
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('');

  useEffect(() => {
    Promise.all([api.listTasks(), api.getTaskStatuses()])
      .then(([t, s]) => {
        setTasks(t);
        setStatuses(s);
      })
      .finally(() => setLoading(false));
  }, []);

  const filteredTasks = useMemo(() => {
    const q = search.toLowerCase().trim();
    return tasks.filter((task) => {
      const matchesSearch =
        !q ||
        task.title.toLowerCase().includes(q) ||
        task.description.toLowerCase().includes(q) ||
        task.tags.some((tag) => tag.toLowerCase().includes(q));
      const matchesType = !typeFilter || task.type === typeFilter;
      return matchesSearch && matchesType;
    });
  }, [tasks, search, typeFilter]);

  const totalPages = Math.ceil(filteredTasks.length / ITEMS_PER_PAGE);
  const paginatedTasks = filteredTasks.slice((page - 1) * ITEMS_PER_PAGE, page * ITEMS_PER_PAGE);

  const handleSearch = (value: string) => {
    setSearch(value);
    setPage(1);
  };

  const handleTypeFilter = (value: string) => {
    setTypeFilter(value);
    setPage(1);
  };

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
      <div className="mb-6 flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-4xl md:text-5xl font-headline font-bold text-on-surface tracking-tighter uppercase mb-2">
            Каталог испытаний
          </h1>
          <p className="text-xs font-mono uppercase tracking-[0.2em] text-primary/80">
            Выберите цель для атаки <span className="animate-pulse">_</span>
          </p>
        </div>
      </div>

      {/* Search & Filters */}
      <div className="mb-8 flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant">
            <Icon name="search" size="sm" />
          </span>
          <input
            type="text"
            value={search}
            onChange={(e) => handleSearch(e.target.value)}
            placeholder="Поиск по названию, описанию, тегам..."
            className="w-full bg-surface-container-high border border-outline-variant/20 pl-9 pr-4 py-2 text-sm text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:border-primary/50 transition-colors"
          />
          {search && (
            <button
              onClick={() => handleSearch('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-on-surface-variant hover:text-on-surface transition-colors"
            >
              <Icon name="close" size="sm" />
            </button>
          )}
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => handleTypeFilter('')}
            className={`px-3 py-2 text-[10px] font-bold uppercase tracking-widest border transition-colors ${
              typeFilter === ''
                ? 'bg-primary text-on-primary border-primary'
                : 'bg-surface-container-high hover:bg-surface-bright border-outline-variant/20 text-on-surface'
            }`}
          >
            Все
          </button>
          {Object.entries(TYPE_LABELS).map(([type, label]) => (
            <button
              key={type}
              onClick={() => handleTypeFilter(type)}
              className={`px-3 py-2 text-[10px] font-bold uppercase tracking-widest border transition-colors ${
                typeFilter === type
                  ? 'bg-primary text-on-primary border-primary'
                  : 'bg-surface-container-high hover:bg-surface-bright border-outline-variant/20 text-on-surface'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Bento Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {paginatedTasks.map((task) => (
          <LabCard key={task.id} task={task} status={statuses[task.id]} />
        ))}
      </div>

      {filteredTasks.length === 0 && (
        <div className="text-center py-20 text-on-surface-variant">
          {search || typeFilter ? 'Ничего не найдено по заданным критериям' : 'Задания не найдены'}
        </div>
      )}

      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
    </div>
  );
}
