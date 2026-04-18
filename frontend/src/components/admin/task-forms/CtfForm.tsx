import { useState } from 'react';

import FormInput from '../../FormInput';
import FormSelect from '../../FormSelect';

export default function CtfForm({
  config,
  update,
}: {
  config: Record<string, any>;
  update: (p: Record<string, any>) => void;
}) {
  const [changeFlag, setChangeFlag] = useState(false);
  const hasHash = !!config.flag_hash;

  return (
    <div className="space-y-3">
      <div className="space-y-1">
        <FormInput
          label="Docker image"
          value={config.docker_image || ''}
          onChange={(e) => update({ docker_image: e.target.value })}
        />
        <div className="text-[10px] text-on-surface-variant ml-1">
          myuser/lms-xyz:v1 — образ должен быть доступен docker pull с хоста
        </div>
      </div>
      <FormInput
        label="Port (внутри контейнера)"
        type="number"
        value={String(config.port ?? 5000)}
        onChange={(e) => update({ port: Number(e.target.value) })}
      />
      <FormInput
        label="TTL minutes"
        type="number"
        value={String(config.ttl_minutes ?? 120)}
        onChange={(e) => update({ ttl_minutes: Number(e.target.value) })}
      />
      <FormSelect
        label="Difficulty"
        value={config.difficulty || 'medium'}
        onChange={(e) => update({ difficulty: e.target.value })}
        options={['easy', 'medium', 'hard'].map((x) => ({ value: x, label: x }))}
      />
      {hasHash && !changeFlag ? (
        <div className="flex gap-3 items-center">
          <span className="text-sm">Flag hash set</span>
          <button
            type="button"
            className="underline"
            onClick={() => setChangeFlag(true)}
          >
            Изменить
          </button>
        </div>
      ) : (
        <div className="space-y-1">
          <FormInput
            label="Flag (plaintext)"
            type="password"
            value={config.flag || ''}
            onChange={(e) => update({ flag: e.target.value })}
          />
          <div className="text-[10px] text-on-surface-variant ml-1">
            Хэшируется в SHA256 при сохранении; plaintext не сохраняется.
          </div>
        </div>
      )}
    </div>
  );
}
