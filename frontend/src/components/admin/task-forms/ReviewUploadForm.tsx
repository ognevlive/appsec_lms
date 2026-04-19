import FormInput from '../../FormInput';
import FormSelect from '../../FormSelect';

const DEFAULT_EXT = ['pdf', 'png', 'jpg', 'zip', 'txt', 'md', 'docx', 'py', 'js', 'ts'];

export default function ReviewUploadForm({
  config,
  update,
}: {
  config: Record<string, any>;
  update: (p: Record<string, any>) => void;
}) {
  const reviewMode: 'auto' | 'manual' = config.review_mode === 'manual' ? 'manual' : 'auto';
  const fileUpload = config.file_upload || {};
  const answerText = config.answer_text || {};

  const fileEnabled = !!fileUpload.enabled;
  const allowedExt: string[] = Array.isArray(fileUpload.allowed_ext) && fileUpload.allowed_ext.length
    ? fileUpload.allowed_ext
    : DEFAULT_EXT;

  const patchFileUpload = (patch: Record<string, any>) => {
    update({ file_upload: { ...fileUpload, ...patch } });
  };

  const patchAnswerText = (patch: Record<string, any>) => {
    update({ answer_text: { ...answerText, ...patch } });
  };

  return (
    <div className="space-y-4 border-t border-outline-variant/15 pt-4">
      <div className="text-xs uppercase tracking-wider text-on-surface-variant font-bold">
        Проверка и сдача работы
      </div>

      <FormSelect
        label="Режим проверки"
        value={reviewMode}
        onChange={(e) => update({ review_mode: e.target.value })}
        options={[
          { value: 'auto', label: 'Автоматический (по типу задачи)' },
          { value: 'manual', label: 'Ручная проверка преподавателем' },
        ]}
      />

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={fileEnabled}
          onChange={(e) => {
            if (e.target.checked) {
              update({
                file_upload: {
                  enabled: true,
                  max_files: fileUpload.max_files ?? 5,
                  max_size_mb: fileUpload.max_size_mb ?? 20,
                  allowed_ext: Array.isArray(fileUpload.allowed_ext) && fileUpload.allowed_ext.length
                    ? fileUpload.allowed_ext
                    : DEFAULT_EXT,
                  required: !!fileUpload.required,
                },
              });
            } else {
              patchFileUpload({ enabled: false });
            }
          }}
        />
        <span>Разрешить загрузку файлов</span>
      </label>

      {fileEnabled && (
        <div className="pl-6 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <FormInput
              label="Макс. файлов"
              type="number"
              min={1}
              value={String(fileUpload.max_files ?? 5)}
              onChange={(e) => patchFileUpload({ max_files: Number(e.target.value) })}
            />
            <FormInput
              label="Макс. размер файла (МБ)"
              type="number"
              min={1}
              value={String(fileUpload.max_size_mb ?? 20)}
              onChange={(e) => patchFileUpload({ max_size_mb: Number(e.target.value) })}
            />
          </div>

          <FormInput
            label="Разрешённые расширения (через запятую)"
            value={allowedExt.join(', ')}
            placeholder={DEFAULT_EXT.join(', ')}
            onChange={(e) =>
              patchFileUpload({
                allowed_ext: e.target.value
                  .split(',')
                  .map((s) => s.trim().replace(/^\./, '').toLowerCase())
                  .filter(Boolean),
              })
            }
          />

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={!!fileUpload.required}
              onChange={(e) => patchFileUpload({ required: e.target.checked })}
            />
            <span>Файл обязателен</span>
          </label>
        </div>
      )}

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={!!answerText.enabled}
          onChange={(e) => patchAnswerText({ enabled: e.target.checked })}
        />
        <span>Текстовое поле ответа</span>
      </label>

      {answerText.enabled && (
        <label className="flex items-center gap-2 text-sm pl-6">
          <input
            type="checkbox"
            checked={!!answerText.required}
            onChange={(e) => patchAnswerText({ required: e.target.checked })}
          />
          <span>Текст обязателен</span>
        </label>
      )}
    </div>
  );
}
