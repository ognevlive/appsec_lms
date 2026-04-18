import { useState } from 'react';
import type { ModuleItem } from '../types';
import UnitRow from './UnitRow';
import LearningOutcomesList from './LearningOutcomesList';
import ModuleMetaBar from './ModuleMetaBar';

interface Props {
  module: ModuleItem;
  defaultOpen: boolean;
}

export default function ModuleAccordion({ module, defaultOpen }: Props) {
  const [open, setOpen] = useState(defaultOpen && !module.is_locked);

  const pct = module.unit_count > 0
    ? Math.round((module.completed_unit_count / module.unit_count) * 100)
    : 0;

  const icon = (module.config?.icon as string) || 'folder';

  return (
    <div className={`border transition-colors
      ${module.is_locked ? 'border-outline-variant/10 bg-surface-container-low/20' : 'border-outline-variant/20 bg-surface-container-low'}`}>
      <button
        onClick={() => !module.is_locked && setOpen(o => !o)}
        disabled={module.is_locked}
        className={`w-full flex items-center gap-3 px-5 py-4 text-left transition-colors
          ${module.is_locked ? 'cursor-not-allowed' : 'hover:bg-surface-container'}`}
      >
        <span className={`material-symbols-outlined ${module.is_locked ? 'text-on-surface-variant/50' : 'text-primary'} text-xl`}>
          {module.is_locked ? 'lock' : icon}
        </span>
        <div className="flex-1 min-w-0">
          <div className={`font-headline font-bold uppercase tracking-tight text-sm truncate
            ${module.is_locked ? 'text-on-surface-variant' : 'text-on-surface'}`}>
            Модуль {module.order}: {module.title}
          </div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-on-surface-variant mt-0.5">
            {module.is_locked
              ? 'Заблокирован — завершите предыдущие модули'
              : `${module.completed_unit_count}/${module.unit_count} выполнено · ${pct}%`}
          </div>
        </div>
        {!module.is_locked && (
          <span className="material-symbols-outlined text-on-surface-variant">
            {open ? 'expand_less' : 'expand_more'}
          </span>
        )}
      </button>

      {open && !module.is_locked && (
        <div className="border-t border-outline-variant/15 px-5 pt-4 pb-5">
          {module.description && (
            <p className="text-sm text-on-surface-variant mb-3 max-w-3xl">{module.description}</p>
          )}
          <ModuleMetaBar estimatedHours={module.estimated_hours} outcomesCount={module.learning_outcomes.length} />
          <LearningOutcomesList outcomes={module.learning_outcomes} />

          <div className="space-y-2 mt-4">
            {module.units.map((unit, i) => (
              <UnitRow
                key={unit.id}
                unit={unit}
                index={unit.task_type === 'theory' ? 0 : i + 1}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
