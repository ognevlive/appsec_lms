import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

import { api } from '../../api';
import type { AdminTask, AdminUnit } from '../../types';

export default function UnitRow({
  unit,
  task,
  onChange,
  onDelete,
}: {
  unit: AdminUnit;
  task?: AdminTask;
  onChange: (u: AdminUnit) => void;
  onDelete: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({
    id: unit.id,
  });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const toggleReq = async () => {
    const u = await api.adminContent.patchUnit(unit.id, { is_required: !unit.is_required });
    onChange(u);
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="flex items-center gap-3 p-2 bg-surface-container-low"
    >
      <span {...attributes} {...listeners} className="cursor-grab">
        ⋮⋮
      </span>
      <span className="text-xs bg-surface-container-high px-2">{task?.type}</span>
      <span className="flex-1">{task?.title || `Task ${unit.task_id}`}</span>
      <label className="flex items-center gap-1 text-sm">
        <input type="checkbox" checked={unit.is_required} onChange={toggleReq} />
        required
      </label>
      <button onClick={onDelete}>×</button>
    </div>
  );
}
