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
} from '@dnd-kit/sortable';
import { useEffect, useState } from 'react';

import { api } from '../../api';
import Button from '../Button';
import FormInput from '../FormInput';
import type { AdminModule, AdminTask, AdminUnit } from '../../types';
import TaskPicker from './TaskPicker';
import UnitRow from './UnitRow';

export default function ModuleCard({
  module,
  onChange,
  onDelete,
}: {
  module: AdminModule;
  onChange: (m: AdminModule) => void;
  onDelete: () => void;
}) {
  const [units, setUnits] = useState<AdminUnit[]>([]);
  const [tasks, setTasks] = useState<Record<number, AdminTask>>({});
  const [picker, setPicker] = useState(false);
  const [local, setLocal] = useState(module);
  const [loadError, setLoadError] = useState('');
  const sensors = useSensors(useSensor(PointerSensor));

  useEffect(() => {
    setLocal(module);
  }, [module]);

  // Load units + their associated tasks
  useEffect(() => {
    api.adminContent
      .getModuleFull(module.id)
      .then((r) => {
        setUnits(r.units);
        const tmap: Record<number, AdminTask> = {};
        r.units.forEach((u) => {
          tmap[u.task_id] = {
            id: u.task_id,
            slug: u.task_slug,
            title: u.task_title,
            type: u.task_type,
            description: '',
            order: 0,
            config: {},
            author_id: null,
            updated_at: '',
          } as AdminTask;
        });
        setTasks(tmap);
        setLoadError('');
      })
      .catch((e: any) => {
        console.error(e);
        setLoadError(e?.message || 'Не удалось загрузить юниты модуля');
      });
  }, [module.id]);

  const saveMeta = async () => {
    const m = await api.adminContent.patchModule(module.id, {
      title: local.title,
      description: local.description,
      estimated_hours: local.estimated_hours,
      learning_outcomes: local.learning_outcomes,
    });
    onChange(m);
  };

  const addUnit = async (task: AdminTask) => {
    const u = await api.adminContent.createUnit(module.id, {
      task_id: task.id,
      unit_order: units.length + 1,
      is_required: true,
    });
    setUnits([...units, u]);
    setTasks({ ...tasks, [task.id]: task });
    setPicker(false);
  };

  const onDragEnd = async (e: DragEndEvent) => {
    if (!e.over || e.active.id === e.over.id) return;
    const oldIdx = units.findIndex((u) => u.id === e.active.id);
    const newIdx = units.findIndex((u) => u.id === e.over!.id);
    const snapshot = units;
    const next = arrayMove(units, oldIdx, newIdx);
    setUnits(next);
    try {
      await api.adminContent.reorderUnits(
        module.id,
        next.map((u, i) => ({ id: u.id, order: i + 1 })),
      );
    } catch (err) {
      console.error(err);
      setUnits(snapshot);
    }
  };

  return (
    <div className="border p-4 space-y-3">
      <div className="flex gap-3 items-start">
        <div className="flex-1 space-y-2">
          <FormInput
            label="Title"
            value={local.title}
            onChange={(e) => setLocal({ ...local, title: e.target.value })}
            onBlur={saveMeta}
          />
          <div className="space-y-1">
            <label className="text-[10px] uppercase tracking-wider text-on-surface-variant font-bold ml-1">
              Description
            </label>
            <textarea
              className="w-full min-h-[80px] bg-surface-container-lowest border border-outline-variant/30 text-sm text-on-surface focus:border-primary focus:ring-0 focus:outline-none transition-colors placeholder:text-outline-variant px-3 py-2"
              value={local.description}
              onChange={(e) => setLocal({ ...local, description: e.target.value })}
              onBlur={saveMeta}
            />
          </div>
          <FormInput
            label="Estimated hours"
            type="number"
            value={String(local.estimated_hours ?? '')}
            onChange={(e) =>
              setLocal({
                ...local,
                estimated_hours: e.target.value ? Number(e.target.value) : null,
              })
            }
            onBlur={saveMeta}
          />
        </div>
        <Button onClick={onDelete} variant="danger">
          Удалить модуль
        </Button>
      </div>

      <div className="space-y-2">
        {loadError && <div className="text-error text-xs">{loadError}</div>}
        <DndContext sensors={sensors} onDragEnd={onDragEnd}>
          <SortableContext
            items={units.map((u) => u.id)}
            strategy={verticalListSortingStrategy}
          >
            {units.map((u) => (
              <UnitRow
                key={u.id}
                unit={u}
                task={tasks[u.task_id]}
                onChange={(patched) =>
                  setUnits(units.map((x) => (x.id === u.id ? patched : x)))
                }
                onDelete={async () => {
                  await api.adminContent.deleteUnit(u.id);
                  setUnits(units.filter((x) => x.id !== u.id));
                }}
              />
            ))}
          </SortableContext>
        </DndContext>
        <Button onClick={() => setPicker(true)}>+ Добавить юнит</Button>
      </div>

      {picker && <TaskPicker onPick={addUnit} onClose={() => setPicker(false)} />}
    </div>
  );
}
