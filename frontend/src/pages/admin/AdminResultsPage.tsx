import { useEffect, useState } from 'react';
import { api } from '../../api';
import Pagination from '../../components/Pagination';
import PulseIndicator from '../../components/PulseIndicator';
import type { Submission, User, TaskCatalogItem, PaginatedResponse } from '../../types';

export default function AdminResultsPage() {
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const perPage = 20;

  // Filters
  const [filterUserId, setFilterUserId] = useState<string>('');
  const [filterTaskId, setFilterTaskId] = useState<string>('');
  const [filterStatus, setFilterStatus] = useState<string>('');

  // Reference data for filters
  const [users, setUsers] = useState<User[]>([]);
  const [tasks, setTasks] = useState<TaskCatalogItem[]>([]);

  useEffect(() => {
    api.listUsers().then((res: any) => setUsers(Array.isArray(res) ? res : res.items || [])).catch(() => {});
    api.listTasks().then(setTasks).catch(() => {});
  }, []);

  const fetchSubmissions = async () => {
    setLoading(true);
    try {
      const params: any = { page, per_page: perPage };
      if (filterUserId) params.user_id = Number(filterUserId);
      if (filterTaskId) params.task_id = Number(filterTaskId);
      if (filterStatus) params.status = filterStatus;
      const res = await api.listSubmissions(params);
      if (res.items) {
        setSubmissions(res.items);
        setTotal(res.total);
      } else {
        setSubmissions(Array.isArray(res) ? res : []);
        setTotal(Array.isArray(res) ? res.length : 0);
      }
    } catch {
      setSubmissions([]);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchSubmissions();
  }, [page, filterUserId, filterTaskId, filterStatus]);

  const resetFilters = () => {
    setFilterUserId('');
    setFilterTaskId('');
    setFilterStatus('');
    setPage(1);
  };

  const totalPages = Math.ceil(total / perPage);

  const getUserName = (userId: number) => {
    const u = users.find((u) => u.id === userId);
    return u ? (u.full_name || u.username) : `#${userId}`;
  };

  const getTaskTitle = (taskId: number) => {
    const t = tasks.find((t) => t.id === taskId);
    return t?.title || `#${taskId}`;
  };

  const successCount = submissions.filter((s) => s.status === 'success').length;
  const failCount = submissions.filter((s) => s.status === 'fail').length;

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-5xl font-bold font-headline tracking-tighter text-on-surface uppercase">
            Результаты
          </h1>
          <p className="text-on-surface-variant text-sm mt-2 max-w-xl">
            Мониторинг выполнения лабораторных работ и статусов безопасности.
          </p>
        </div>
      </div>

      {/* Filter Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-surface-container-low p-1 border border-outline-variant/5">
          <label className="block text-[10px] uppercase font-bold text-on-surface-variant px-3 pt-2">
            Студент
          </label>
          <select
            value={filterUserId}
            onChange={(e) => { setFilterUserId(e.target.value); setPage(1); }}
            className="w-full bg-transparent border-none text-on-surface text-sm focus:ring-0 cursor-pointer py-1 px-3"
          >
            <option value="">Все студенты</option>
            {users.map((u) => (
              <option key={u.id} value={u.id}>{u.full_name || u.username}</option>
            ))}
          </select>
        </div>
        <div className="bg-surface-container-low p-1 border border-outline-variant/5">
          <label className="block text-[10px] uppercase font-bold text-on-surface-variant px-3 pt-2">
            Задание
          </label>
          <select
            value={filterTaskId}
            onChange={(e) => { setFilterTaskId(e.target.value); setPage(1); }}
            className="w-full bg-transparent border-none text-on-surface text-sm focus:ring-0 cursor-pointer py-1 px-3"
          >
            <option value="">Все задания</option>
            {tasks.map((t) => (
              <option key={t.id} value={t.id}>{t.title}</option>
            ))}
          </select>
        </div>
        <div className="bg-surface-container-low p-1 border border-outline-variant/5">
          <label className="block text-[10px] uppercase font-bold text-on-surface-variant px-3 pt-2">
            Статус
          </label>
          <select
            value={filterStatus}
            onChange={(e) => { setFilterStatus(e.target.value); setPage(1); }}
            className="w-full bg-transparent border-none text-on-surface text-sm focus:ring-0 cursor-pointer py-1 px-3"
          >
            <option value="">Все статусы</option>
            <option value="success">Успешно</option>
            <option value="fail">Ошибка</option>
            <option value="pending">В ожидании</option>
          </select>
        </div>
        <div className="flex items-end">
          <button
            onClick={resetFilters}
            className="w-full h-11 bg-surface-container-highest text-on-surface text-xs font-bold uppercase tracking-widest hover:text-primary transition-all border border-outline-variant/10"
          >
            Сбросить фильтры
          </button>
        </div>
      </div>

      {/* Results Table */}
      <div className="bg-surface-container overflow-hidden border border-outline-variant/5">
        {loading ? (
          <div className="py-12 text-center text-primary animate-pulse">Загрузка...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead className="bg-surface-container-highest">
                <tr>
                  <th className="px-6 py-4 text-[10px] font-bold uppercase text-on-surface-variant tracking-widest">
                    Студент
                  </th>
                  <th className="px-6 py-4 text-[10px] font-bold uppercase text-on-surface-variant tracking-widest">
                    Задание
                  </th>
                  <th className="px-6 py-4 text-[10px] font-bold uppercase text-on-surface-variant tracking-widest">
                    Статус
                  </th>
                  <th className="px-6 py-4 text-[10px] font-bold uppercase text-on-surface-variant tracking-widest">
                    Дата
                  </th>
                </tr>
              </thead>
              <tbody>
                {submissions.map((s, idx) => (
                  <tr
                    key={s.id}
                    className={`${idx % 2 === 0 ? 'bg-[#1a1b26]' : 'bg-[#15161e]'} hover:bg-surface-bright transition-colors`}
                  >
                    <td className="px-6 py-4 text-sm">
                      <div className="flex items-center gap-3">
                        <div className="w-7 h-7 rounded-sm bg-surface-container-highest flex items-center justify-center text-[10px] font-bold text-on-surface-variant">
                          {getUserName(s.user_id).charAt(0).toUpperCase()}
                        </div>
                        <span>{getUserName(s.user_id)}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-on-surface-variant">
                      {getTaskTitle(s.task_id)}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        {s.status === 'success' && <PulseIndicator color="primary" size="sm" />}
                        {s.status === 'fail' && <PulseIndicator color="tertiary" size="sm" />}
                        {s.status === 'pending' && <PulseIndicator color="secondary" size="sm" />}
                        <span
                          className={`text-[9px] font-bold uppercase ${
                            s.status === 'success'
                              ? 'text-primary'
                              : s.status === 'fail'
                              ? 'text-tertiary'
                              : 'text-secondary'
                          }`}
                        >
                          {s.status === 'success' ? 'Успешно' : s.status === 'fail' ? 'Ошибка' : 'Ожидание'}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-xs font-mono text-on-surface-variant">
                      {new Date(s.submitted_at).toLocaleString('ru-RU')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Summary */}
      <div className="flex items-center gap-6 mt-4 text-xs text-on-surface-variant">
        <span>Всего: <strong className="text-on-surface">{total}</strong></span>
        <span className="flex items-center gap-1">
          <PulseIndicator color="primary" size="sm" />
          Успешно: <strong className="text-primary">{successCount}</strong>
        </span>
        <span className="flex items-center gap-1">
          <PulseIndicator color="tertiary" size="sm" />
          Ошибки: <strong className="text-tertiary">{failCount}</strong>
        </span>
      </div>

      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
    </div>
  );
}
