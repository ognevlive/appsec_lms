import { useState } from 'react';

import FormInput from '../../FormInput';
import FormSelect from '../../FormSelect';
import MarkdownEditor from '../MarkdownEditor';

export default function SshLabForm({
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
      <FormInput
        label="Docker image"
        value={config.docker_image || ''}
        onChange={(e) => update({ docker_image: e.target.value })}
      />
      <FormInput
        label="Terminal port (ttyd)"
        type="number"
        value={String(config.terminal_port ?? 80)}
        onChange={(e) => update({ terminal_port: Number(e.target.value) })}
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
      <div>
        <div className="text-sm mb-2">Instructions (markdown)</div>
        <MarkdownEditor
          value={config.instructions || ''}
          onChange={(v) => update({ instructions: v })}
        />
      </div>
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
        <FormInput
          label="Flag (plaintext)"
          type="password"
          value={config.flag || ''}
          onChange={(e) => update({ flag: e.target.value })}
        />
      )}
    </div>
  );
}
