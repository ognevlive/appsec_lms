import { useEffect, useState } from 'react';
import { api } from '../api';
import Button from '../components/Button';
import Icon from '../components/Icon';
import type { ContainerInfo, CheckResponse } from '../types';

interface CtfSectionProps {
  taskId: number;
  config: Record<string, any>;
  onSubmit: () => void;
}

export default function CtfSection({ taskId, config, onSubmit }: CtfSectionProps) {
  const [container, setContainer] = useState<ContainerInfo | null>(null);
  const [flag, setFlag] = useState('');
  const [flagResult, setFlagResult] = useState<'correct' | 'wrong' | null>(null);
  const [checks, setChecks] = useState<CheckResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const hasFlag = !!config?.flag_hash;
  const hasChecks = (config?.checks?.length || 0) > 0;

  useEffect(() => {
    api.ctfStatus(taskId).then(setContainer).catch(() => {});
  }, [taskId]);

  const startContainer = async () => {
    setLoading(true);
    setError('');
    try {
      const info = await api.startCtf(taskId);
      setContainer(info);
    } catch (err: any) {
      setError(err.message);
    }
    setLoading(false);
  };

  const stopContainer = async () => {
    setLoading(true);
    try {
      await api.stopCtf(taskId);
      setContainer(null);
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

  const runChecks = async () => {
    setLoading(true);
    setChecks(null);
    setError('');
    try {
      const res = await api.checkContainer(taskId);
      setChecks(res);
      if (res.all_passed) onSubmit();
    } catch (err: any) {
      setError(err.message);
    }
    setLoading(false);
  };

  return (
    <>
      {/* Container Control */}
      <section className="bg-surface-container-low p-6">
        <h3 className="text-xs font-bold uppercase tracking-[0.3em] text-primary mb-4 flex items-center gap-2">
          <Icon name="dns" size="sm" />
          Контейнер
        </h3>
        {container ? (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-2 h-2 rounded-full bg-primary shadow-[0_0_8px_#8eff71]" />
              <span className="text-xs uppercase text-primary font-bold tracking-widest">Запущен</span>
            </div>
            <div className="bg-surface-container-lowest p-4 border border-outline-variant/20">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-[10px] uppercase text-on-surface-variant font-bold block mb-1">
                    Target URL
                  </span>
                  <a
                    href={`http://${container.domain}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-secondary hover:text-primary font-mono text-sm transition-colors"
                  >
                    {container.domain}
                    <Icon name="open_in_new" size="sm" className="ml-1 inline" />
                  </a>
                </div>
                <Button variant="danger" size="sm" onClick={stopContainer} disabled={loading}>
                  Остановить
                </Button>
              </div>
              <p className="text-[10px] text-on-surface-variant mt-2 font-mono">
                Истекает: {new Date(container.expires_at).toLocaleString('ru-RU')}
              </p>
            </div>
          </div>
        ) : (
          <Button onClick={startContainer} disabled={loading} size="lg" className="w-full">
            {loading ? 'Запуск...' : 'Запустить контейнер'}
          </Button>
        )}
      </section>

      {/* Flag Submission */}
      {container && hasFlag && (
        <section className="bg-surface-container-low p-6">
          <h3 className="text-xs font-bold uppercase tracking-[0.3em] text-primary mb-4 flex items-center gap-2">
            <Icon name="flag" size="sm" />
            Отправить флаг
          </h3>
          <div className="flex gap-3">
            <input
              value={flag}
              onChange={(e) => setFlag(e.target.value)}
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

      {/* Auto-checks */}
      {container && hasChecks && (
        <section className="bg-surface-container-low p-6">
          <h3 className="text-xs font-bold uppercase tracking-[0.3em] text-primary mb-4 flex items-center gap-2">
            <Icon name="verified" size="sm" />
            Автопроверка
          </h3>
          <Button onClick={runChecks} disabled={loading} variant="secondary" className="mb-4">
            {loading ? 'Проверка...' : 'Запустить проверку'}
          </Button>

          {checks && (
            <div className="space-y-2">
              {checks.results.map((c, i) => (
                <div
                  key={i}
                  className={`flex items-center gap-3 px-4 py-3 text-sm ${
                    c.passed ? 'bg-primary/5 text-primary' : 'bg-tertiary/5 text-tertiary'
                  }`}
                >
                  <Icon name={c.passed ? 'check_circle' : 'cancel'} size="sm" filled />
                  <span className="font-medium">{c.name}</span>
                  {!c.passed && c.message && (
                    <span className="text-on-surface-variant text-xs ml-auto">{c.message}</span>
                  )}
                </div>
              ))}
              {checks.all_passed && (
                <div className="bg-primary/10 border border-primary/20 px-4 py-3 text-primary font-bold text-sm mt-2">
                  Все проверки пройдены!
                </div>
              )}
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
