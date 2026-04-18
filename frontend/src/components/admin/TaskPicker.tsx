import { useEffect, useState } from 'react';

import { api } from '../../api';
import Button from '../Button';
import FormInput from '../FormInput';
import FormSelect from '../FormSelect';
import type { AdminTask } from '../../types';

export default function TaskPicker({
  onPick,
  onClose,
}: {
  onPick: (task: AdminTask) => void;
  onClose: () => void;
}) {
  const [tasks, setTasks] = useState<AdminTask[]>([]);
  const [type, setType] = useState('');
  const [search, setSearch] = useState('');

  const load = () =>
    api.adminContent
      .listTasks({
        type: type || undefined,
        search: search || undefined,
      })
      .then(setTasks);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [type]);

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-surface max-w-2xl w-full p-6 space-y-3">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-bold">Выбор таска</h3>
          <div className="flex-1" />
          <Button onClick={onClose} variant="secondary">
            Закрыть
          </Button>
        </div>
        <div className="flex gap-3 items-end">
          <FormSelect
            label="Тип"
            value={type}
            onChange={(e) => setType(e.target.value)}
            options={['', 'theory', 'quiz', 'ctf', 'ssh_lab', 'gitlab'].map((t) => ({
              value: t,
              label: t || 'Все',
            }))}
          />
          <FormInput
            label="Поиск"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') load();
            }}
          />
          <Button onClick={load}>Найти</Button>
        </div>
        <div className="max-h-96 overflow-auto">
          {tasks.map((t) => (
            <div
              key={t.id}
              className="p-2 hover:bg-surface-container-low cursor-pointer flex gap-3"
              onClick={() => onPick(t)}
            >
              <span className="text-xs bg-surface-container-high px-2">{t.type}</span>
              <span>{t.title}</span>
              <span className="font-mono text-xs text-on-surface-variant">{t.slug}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
