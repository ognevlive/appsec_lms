import FormInput from '../../FormInput';
import FormSelect from '../../FormSelect';
import MarkdownEditor from '../MarkdownEditor';

export default function TheoryForm({
  config,
  update,
}: {
  config: Record<string, any>;
  update: (p: Record<string, any>) => void;
}) {
  const kind = config.content_kind || 'text';
  const video = config.video || { provider: 'youtube', src: '' };

  const showText = kind === 'text' || kind === 'mixed';
  const showVideo = kind === 'video' || kind === 'mixed';

  return (
    <div className="space-y-4">
      <FormSelect
        label="Content kind"
        value={kind}
        onChange={(e) => update({ content_kind: e.target.value })}
        options={[
          { value: 'text', label: 'Text' },
          { value: 'video', label: 'Video' },
          { value: 'mixed', label: 'Mixed' },
        ]}
      />

      {showVideo && (
        <>
          <FormSelect
            label="Video provider"
            value={video.provider}
            onChange={(e) =>
              update({ video: { ...video, provider: e.target.value } })
            }
            options={[
              { value: 'youtube', label: 'YouTube' },
              { value: 'url', label: 'URL' },
            ]}
          />
          <FormInput
            label="Video URL"
            value={video.src}
            onChange={(e) => update({ video: { ...video, src: e.target.value } })}
          />
        </>
      )}

      {showText && (
        <div>
          <div className="text-sm mb-2">Content (markdown)</div>
          <MarkdownEditor
            value={config.content || ''}
            onChange={(v) => update({ content: v })}
          />
        </div>
      )}
    </div>
  );
}
