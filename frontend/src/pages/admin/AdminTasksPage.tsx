import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { api } from '../../api';
import Button from '../../components/Button';
import FormInput from '../../components/FormInput';
import FormSelect from '../../components/FormSelect';
import type { AdminTask, TaskType } from '../../types';

const TYPES: (TaskType | '')[] = ['', 'theory', 'quiz', 'ctf', 'ssh_lab', 'gitlab'];

export default function AdminTasksPage() {
  const nav = useNavigate();
  const [tasks, setTasks] = useState<AdminTask[]>([]);
  const [type, setType] = useState<string>('');
  const [search, setSearch] = useState('');
  const [unused, setUnused] = useState(false);
  const [error, setError] = useState('');

  const load = async () => {
    try {
      const t = await api.adminContent.listTasks({
        type: type || undefined,
        search: search || undefined,
        unused: unused || undefined,
      });
      setTasks(t);
    } catch (e: any) {
      setError(e.message);
    }
  };
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [type, unused]);

  const onImport = async (file: File) => {
    try {
      await api.adminContent.importTask(file);
      await load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center gap-3">
        <h2 className="text-xl font-bold">Таски</h2>
        <div className="flex-1" />
        <Link to="/admin/tasks/new"><Button>Новый таск</Button></Link>
        <label className="inline-block">
          <input
            type="file"
            accept=".zip"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && onImport(e.target.files[0])}
          />
          <span className="px-3 py-2 bg-surface-container-low cursor-pointer">Импорт</span>
        </label>
      </div>

      <div className="flex gap-3 items-end">
        <FormSelect
          label="Тип"
          value={type}
          onChange={(e) => setType(e.target.value)}
          options={TYPES.map((t) => ({ value: t, label: t || 'Все' }))}
        />
        <FormInput
          label="Поиск"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && load()}
        />
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={unused}
            onChange={(e) => setUnused(e.target.checked)}
          />
          Неиспользуемые
        </label>
        <Button onClick={load}>Обновить</Button>
      </div>

      {error && <div className="text-error">{error}</div>}

      <table className="w-full">
        <thead>
          <tr>
            <th className="text-left">Title</th>
            <th className="text-left">Slug</th>
            <th className="text-left">Type</th>
            <th className="text-left">Updated</th>
          </tr>
        </thead>
        <tbody>
          {tasks.map((t) => (
            <tr
              key={t.id}
              className="cursor-pointer hover:bg-surface-container-low"
              onClick={() => nav(`/admin/tasks/${t.id}`)}
            >
              <td>{t.title}</td>
              <td className="font-mono text-sm">{t.slug}</td>
              <td>{t.type}</td>
              <td className="text-sm">{new Date(t.updated_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
