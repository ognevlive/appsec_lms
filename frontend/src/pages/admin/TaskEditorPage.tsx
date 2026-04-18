import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { api } from '../../api';
import Button from '../../components/Button';
import FormInput from '../../components/FormInput';
import FormSelect from '../../components/FormSelect';
import type { AdminTask, TaskType } from '../../types';

const TYPES: TaskType[] = ['theory', 'quiz', 'ctf', 'ssh_lab', 'gitlab'];

export default function TaskEditorPage() {
  const { id } = useParams<{ id: string }>();
  const nav = useNavigate();
  const isNew = !id;
  const [task, setTask] = useState<Partial<AdminTask>>({
    type: 'theory',
    title: '',
    slug: '',
    description: '',
    order: 0,
    config: {},
  });
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!isNew && id) {
      api.adminContent
        .getTask(Number(id))
        .then(setTask)
        .catch((e) => setError(e.message));
    }
  }, [id, isNew]);

  const onSave = async () => {
    setSaving(true);
    setError('');
    try {
      if (isNew) {
        const created = await api.adminContent.createTask(task);
        nav(`/admin/tasks/${created.id}`);
      } else {
        const u = await api.adminContent.patchTask(Number(id), task);
        setTask(u);
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const onDelete = async () => {
    if (!id) return;
    if (!confirm('Удалить таск?')) return;
    try {
      await api.adminContent.deleteTask(Number(id));
      nav('/admin/tasks');
    } catch (e: any) {
      setError(e.message);
    }
  };

  const onExport = async () => {
    if (!id) return;
    const blob = await api.adminContent.exportTask(Number(id));
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `task-${task.slug}.zip`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const updateConfig = (patch: Record<string, any>) =>
    setTask((t) => ({ ...t, config: { ...(t.config || {}), ...patch } }));

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      <div className="flex items-center gap-3">
        <h2 className="text-xl font-bold">
          {isNew ? 'Новый таск' : `Таск: ${task.title}`}
        </h2>
        <div className="flex-1" />
        {!isNew && <Button onClick={onExport}>Экспорт</Button>}
        {!isNew && task.usage && task.usage.length === 0 && (
          <Button onClick={onDelete} variant="danger">
            Удалить
          </Button>
        )}
        <Button onClick={onSave} disabled={saving}>
          {saving ? '…' : 'Сохранить'}
        </Button>
      </div>

      {error && <div className="text-error">{error}</div>}

      <FormInput
        label="Title"
        value={task.title || ''}
        onChange={(e) => {
          const v = e.target.value;
          setTask((t) => ({
            ...t,
            title: v,
            slug: t.slug || slugifyLocal(v),
          }));
        }}
      />
      <div className="space-y-1">
        <FormInput
          label="Slug"
          value={task.slug || ''}
          onChange={(e) => {
            const v = e.target.value;
            setTask((t) => ({ ...t, slug: v }));
          }}
        />
        <div className="text-[10px] text-on-surface-variant ml-1">
          a-z, 0-9, '-'; 2-100 chars
        </div>
      </div>
      <FormSelect
        label="Type"
        value={task.type || 'theory'}
        disabled={!isNew}
        onChange={(e) => {
          const v = e.target.value as TaskType;
          setTask((t) => ({ ...t, type: v, config: {} }));
        }}
        options={TYPES.map((t) => ({ value: t, label: t }))}
      />
      <div className="space-y-1">
        <label className="text-[10px] uppercase tracking-wider text-on-surface-variant font-bold ml-1">
          Description
        </label>
        <textarea
          className="w-full min-h-[96px] bg-surface-container-lowest border border-outline-variant/30 text-sm text-on-surface focus:border-primary focus:ring-0 focus:outline-none transition-colors placeholder:text-outline-variant px-3 py-2"
          value={task.description || ''}
          onChange={(e) => {
            const v = e.target.value;
            setTask((t) => ({ ...t, description: v }));
          }}
        />
      </div>
      <FormInput
        label="Order"
        type="number"
        value={String(task.order ?? 0)}
        onChange={(e) => {
          const v = e.target.value;
          setTask((t) => ({ ...t, order: Number(v) }));
        }}
      />

      <TypeSpecificForm task={task} updateConfig={updateConfig} />
    </div>
  );
}

function slugifyLocal(s: string): string {
  const map: Record<string, string> = {
    а: 'a', б: 'b', в: 'v', г: 'g', д: 'd', е: 'e', ё: 'yo', ж: 'zh',
    з: 'z', и: 'i', й: 'y', к: 'k', л: 'l', м: 'm', н: 'n', о: 'o',
    п: 'p', р: 'r', с: 's', т: 't', у: 'u', ф: 'f', х: 'h', ц: 'c',
    ч: 'ch', ш: 'sh', щ: 'sch', ъ: '', ы: 'y', ь: '', э: 'e', ю: 'yu',
    я: 'ya',
  };
  return s
    .toLowerCase()
    .split('')
    .map((c) => map[c] ?? (/[a-z0-9]/.test(c) ? c : c === ' ' ? '-' : ''))
    .join('')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 100);
}

function TypeSpecificForm({
  task,
}: {
  task: Partial<AdminTask>;
  updateConfig: (p: Record<string, any>) => void;
}) {
  // Следующие таски добавят конкретные формы; пока — заглушка для каждого типа
  return (
    <pre className="bg-surface-container-low p-4 text-xs">
      {JSON.stringify(task.config, null, 2)}
    </pre>
  );
}
