import { useEffect, useState, useCallback } from 'react';
import { api } from '../api';
import Button from '../components/Button';
import Icon from '../components/Icon';
import type { ContainerInfo } from '../types';

interface SshLabSectionProps {
  taskId: number;
  config: Record<string, any>;
  onSubmit: () => void;
}

export default function SshLabSection({ taskId, config, onSubmit }: SshLabSectionProps) {
  const [container, setContainer] = useState<ContainerInfo | null>(null);
  const [flag, setFlag] = useState('');
  const [flagResult, setFlagResult] = useState<'correct' | 'wrong' | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [terminalReady, setTerminalReady] = useState(false);
  const [iframeKey, setIframeKey] = useState(0);

  const hasFlag = !!config?.flag_hash;

  useEffect(() => {
    api.ctfStatus(taskId).then((info) => {
      setContainer(info);
      if (info) setTerminalReady(true);
    }).catch(() => {});
  }, [taskId]);

  const startContainer = async () => {
    setLoading(true);
    setError('');
    setTerminalReady(false);
    try {
      const info = await api.startCtf(taskId);
      setContainer(info);
      setTimeout(() => setTerminalReady(true), 3000);
    } catch (err: any) {
      setError(err.message);
    }
    setLoading(false);
  };

  const reloadTerminal = useCallback(() => {
    setIframeKey((k) => k + 1);
  }, []);

  const stopContainer = async () => {
    setLoading(true);
    try {
      await api.stopCtf(taskId);
      setContainer(null);
      setTerminalReady(false);
      setFlagResult(null);
    } catch (err: any) {
      setError(err.message);
    }
    setLoading(false);
  };

  const submitFlag = async () => {
    setFlagResult(null);
    setError('');
    try {
      await api.submitFlag(taskId, flag);
      setFlagResult('correct');
      onSubmit();
    } catch (err: any) {
      setFlagResult('wrong');
      setError(err.message);
    }
  };

  return (
    <>
      {/* Container Control */}
      <section className="bg-surface-container-low p-6">
        <h3 className="text-xs font-bold uppercase tracking-[0.3em] text-primary mb-4 flex items-center gap-2">
          <Icon name="terminal" size="sm" />
          Лаборатория
        </h3>
        {container ? (
          <div className="space-y-4">
            {/* Status bar */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-primary shadow-[0_0_8px_#8eff71]" />
                <span className="text-xs uppercase text-primary font-bold tracking-widest">Запущено</span>
                <span className="text-[10px] text-on-surface-variant font-mono">
                  до {new Date(container.expires_at).toLocaleString('ru-RU')}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <a
                  href={`http://${container.domain}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[10px] text-secondary hover:text-primary font-mono flex items-center gap-1 transition-colors"
                >
                  <Icon name="open_in_new" size="sm" />
                  открыть в новом табе
                </a>
                <button
                  onClick={reloadTerminal}
                  className="text-[10px] text-on-surface-variant hover:text-on-surface flex items-center gap-1 transition-colors px-2 py-1 border border-outline-variant/20 hover:border-outline-variant/40"
                  title="Перезагрузить терминал"
                >
                  <Icon name="refresh" size="sm" />
                </button>
                <Button variant="danger" size="sm" onClick={stopContainer} disabled={loading}>
                  Остановить
                </Button>
              </div>
            </div>

            {/* Terminal */}
            <div className="border border-outline-variant/20 bg-[#0d1117] relative" style={{ height: '520px' }}>
              {!terminalReady ? (
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
                  <span className="text-primary animate-pulse font-mono text-sm">Запуск контейнера...</span>
                  <span className="text-[10px] text-on-surface-variant font-mono">инициализация терминала</span>
                </div>
              ) : (
                <iframe
                  key={iframeKey}
                  src={`http://${container.domain}/`}
                  className="w-full h-full border-0"
                  title="Lab Terminal"
                  allow="clipboard-read; clipboard-write"
                />
              )}
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-on-surface-variant">
              Запустите контейнер чтобы получить доступ к терминалу с предустановленными инструментами.
            </p>
            <Button onClick={startContainer} disabled={loading} size="lg" className="w-full">
              <Icon name="play_arrow" size="sm" className="mr-2" />
              {loading ? 'Запуск...' : 'Запустить лабораторию'}
            </Button>
          </div>
        )}
      </section>

      {/* Flag Submission */}
      {container && hasFlag && (
        <section className="bg-surface-container-low p-6">
          <h3 className="text-xs font-bold uppercase tracking-[0.3em] text-primary mb-4 flex items-center gap-2">
            <Icon name="flag" size="sm" />
            Отправить флаг
          </h3>
          <p className="text-xs text-on-surface-variant mb-4">
            Выполните задание в терминале и введите полученный флаг.
          </p>
          <div className="flex gap-3">
            <input
              value={flag}
              onChange={(e) => setFlag(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && submitFlag()}
              placeholder="FLAG{...}"
              className="flex-1 h-12 bg-surface-container-lowest border border-outline-variant/30 text-sm text-on-surface focus:border-primary focus:ring-0 focus:outline-none px-4 font-mono placeholder:text-outline-variant"
            />
            <Button onClick={submitFlag} size="lg">
              Проверить
            </Button>
          </div>
          {flagResult === 'correct' && (
            <div className="mt-3 bg-primary/10 border border-primary/20 px-4 py-2 text-primary text-sm font-bold flex items-center gap-2">
              <Icon name="check_circle" size="sm" filled />
              Флаг верный!
            </div>
          )}
          {flagResult === 'wrong' && (
            <div className="mt-3 bg-tertiary/10 border border-tertiary/20 px-4 py-2 text-tertiary text-sm">
              Неверный флаг
            </div>
          )}
        </section>
      )}

      {error && (
        <div className="bg-error/10 border border-error/20 px-4 py-3 text-error text-sm">
          {error}
        </div>
      )}
    </>
  );
}
