export default function GitlabForm({
  config,
  update,
}: {
  config: Record<string, any>;
  update: (p: Record<string, any>) => void;
}) {
  return (
    <div>
      <div className="text-sm mb-2">GitLab task config (JSON)</div>
      <textarea
        className="w-full h-64 font-mono text-sm p-3 bg-surface-container-low"
        value={JSON.stringify(config, null, 2)}
        onChange={(e) => {
          try {
            update(JSON.parse(e.target.value));
          } catch {
            /* ignore parse errors while typing */
          }
        }}
      />
    </div>
  );
}
