import {
  DndContext,
  DragEndEvent,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  SortableContext,
  arrayMove,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { api } from '../../api';
import ModuleCard from '../../components/admin/ModuleCard';
import Button from '../../components/Button';
import FormInput from '../../components/FormInput';
import type { AdminCourse, AdminModule } from '../../types';

function SortableModule({
  m,
  onChange,
  onDelete,
}: {
  m: AdminModule;
  onChange: (x: AdminModule) => void;
  onDelete: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({
    id: m.id,
  });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };
  return (
    <div ref={setNodeRef} style={style}>
      <div
        {...attributes}
        {...listeners}
        className="cursor-grab text-xs opacity-50"
      >
        ⋮⋮ drag module
      </div>
      <ModuleCard module={m} onChange={onChange} onDelete={onDelete} />
    </div>
  );
}

export default function CourseEditorPage() {
  const { id } = useParams<{ id: string }>();
  const nav = useNavigate();
  const [course, setCourse] = useState<AdminCourse | null>(null);
  const [modules, setModules] = useState<AdminModule[]>([]);
  const [local, setLocal] = useState<AdminCourse | null>(null);
  const [error, setError] = useState('');
  const sensors = useSensors(useSensor(PointerSensor));

  const load = async () => {
    if (!id) return;
    try {
      const all = await api.adminContent.listCourses();
      const c = all.find((x) => x.id === Number(id)) || null;
      setCourse(c);
      setLocal(c);
      const mods = await api.adminContent.listCourseModules(Number(id));
      setModules(mods);
    } catch (e: any) {
      setError(e.message);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const saveCourse = async () => {
    if (!course || !local) return;
    try {
      const c = await api.adminContent.patchCourse(course.id, {
        title: local.title,
        slug: local.slug,
        description: local.description,
        order: local.order,
      });
      setCourse(c);
      setLocal(c);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const toggleVisible = async () => {
    if (!course) return;
    try {
      const c = await api.adminContent.patchCourse(course.id, {
        is_visible: !course.is_visible,
      });
      setCourse(c);
      setLocal(c);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const addModule = async () => {
    if (!course) return;
    try {
      const m = await api.adminContent.createModule(course.id, {
        title: 'Новый модуль',
        description: '',
        order: modules.length + 1,
        estimated_hours: null,
        learning_outcomes: [],
        config: {},
      });
      setModules([...modules, m]);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const onDeleteCourse = async () => {
    if (!course) return;
    if (course.is_visible) {
      setError('Скрой курс перед удалением');
      return;
    }
    if (!confirm(`Удалить курс "${course.title}"?`)) return;
    try {
      await api.adminContent.deleteCourse(course.id);
      nav('/admin/courses');
    } catch (e: any) {
      setError(e.message);
    }
  };

  const onExport = async (bundle: boolean) => {
    if (!course) return;
    try {
      const blob = await api.adminContent.exportCourse(course.id, bundle);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `course-${course.slug}${bundle ? '-bundle' : ''}.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const onDeleteModule = async (m: AdminModule) => {
    if (!confirm(`Удалить модуль "${m.title}"?`)) return;
    try {
      await api.adminContent.deleteModule(m.id);
      setModules(modules.filter((x) => x.id !== m.id));
    } catch (e: any) {
      setError(e.message);
    }
  };

  const onDragEnd = async (e: DragEndEvent) => {
    if (!e.over || e.active.id === e.over.id || !course) return;
    const oldIdx = modules.findIndex((m) => m.id === e.active.id);
    const newIdx = modules.findIndex((m) => m.id === e.over!.id);
    const snapshot = modules;
    const next = arrayMove(modules, oldIdx, newIdx);
    setModules(next);
    try {
      await api.adminContent.reorderModules(
        course.id,
        next.map((m, i) => ({ id: m.id, order: i + 1 })),
      );
    } catch (err: any) {
      setModules(snapshot);
      setError(err.message);
    }
  };

  if (!course || !local) {
    return (
      <div className="p-6">
        {error && <div className="text-error">{error}</div>}
        {!error && <div>Загрузка…</div>}
      </div>
    );
  }

  return (
    <div className="p-6 flex gap-6">
      <aside className="w-80 space-y-3">
        <h2 className="text-xl font-bold">Курс</h2>
        {error && <div className="text-error text-sm">{error}</div>}
        <FormInput
          label="Title"
          value={local.title}
          onChange={(e) => setLocal({ ...local, title: e.target.value })}
          onBlur={saveCourse}
        />
        <FormInput
          label="Slug"
          value={local.slug}
          onChange={(e) => setLocal({ ...local, slug: e.target.value })}
          onBlur={saveCourse}
        />
        <div className="space-y-1">
          <label className="text-[10px] uppercase tracking-wider text-on-surface-variant font-bold ml-1">
            Description
          </label>
          <textarea
            className="w-full min-h-[120px] bg-surface-container-lowest border border-outline-variant/30 text-sm text-on-surface focus:border-primary focus:ring-0 focus:outline-none transition-colors placeholder:text-outline-variant px-3 py-2"
            value={local.description}
            onChange={(e) => setLocal({ ...local, description: e.target.value })}
            onBlur={saveCourse}
          />
        </div>
        <FormInput
          label="Order"
          type="number"
          value={String(local.order)}
          onChange={(e) =>
            setLocal({ ...local, order: e.target.value ? Number(e.target.value) : 0 })
          }
          onBlur={saveCourse}
        />
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={course.is_visible}
            onChange={toggleVisible}
          />
          <span className="text-sm">{course.is_visible ? 'Visible' : 'Hidden'}</span>
        </label>
        <div className="space-y-2 pt-4 border-t border-outline-variant/20">
          <Button onClick={() => onExport(false)} variant="secondary" className="w-full">
            Экспорт структуры
          </Button>
          <Button onClick={() => onExport(true)} variant="secondary" className="w-full">
            Экспорт bundle
          </Button>
          <Button onClick={onDeleteCourse} variant="danger" className="w-full">
            Удалить курс
          </Button>
        </div>
      </aside>

      <main className="flex-1 space-y-3">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-bold">Модули</h3>
          <div className="flex-1" />
          <Button onClick={addModule}>+ Модуль</Button>
        </div>
        <DndContext sensors={sensors} onDragEnd={onDragEnd}>
          <SortableContext
            items={modules.map((m) => m.id)}
            strategy={verticalListSortingStrategy}
          >
            <div className="space-y-4">
              {modules.map((m) => (
                <SortableModule
                  key={m.id}
                  m={m}
                  onChange={(x) =>
                    setModules(modules.map((y) => (y.id === x.id ? x : y)))
                  }
                  onDelete={() => onDeleteModule(m)}
                />
              ))}
            </div>
          </SortableContext>
        </DndContext>
      </main>
    </div>
  );
}
