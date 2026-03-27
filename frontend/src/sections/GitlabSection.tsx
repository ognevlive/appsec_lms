import { useState } from 'react';
import { api } from '../api';
import Button from '../components/Button';
import Icon from '../components/Icon';
import type { GitLabTaskInfo } from '../types';

interface GitlabSectionProps {
  taskId: number;
}

export default function GitlabSection({ taskId }: GitlabSectionProps) {
  const [repoInfo, setRepoInfo] = useState<GitLabTaskInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const startTask = async () => {
    setLoading(true);
    setError('');
    try {
      const info = await api.startGitlab(taskId);
      setRepoInfo(info);
    } catch (err: any) {
      setError(err.message);
    }
    setLoading(false);
  };

  return (
    <>
      <section className="bg-surface-container-low p-6">
        <h3 className="text-xs font-bold uppercase tracking-[0.3em] text-primary mb-4 flex items-center gap-2">
          <Icon name="code" size="sm" />
          GitLab-задание
        </h3>

        {repoInfo ? (
          <div className="space-y-4">
            <div className="bg-surface-container-lowest p-4 border border-outline-variant/20 space-y-3">
              <div>
                <span className="text-[10px] uppercase text-on-surface-variant font-bold block mb-1">
                  Репозиторий
                </span>
                <a
                  href={repoInfo.repo_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-secondary hover:text-primary font-mono text-sm transition-colors"
                >
                  {repoInfo.repo_url}
                  <Icon name="open_in_new" size="sm" className="ml-1 inline" />
                </a>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <span className="text-[10px] uppercase text-on-surface-variant font-bold block mb-1">
                    Логин
                  </span>
                  <code className="text-sm text-secondary bg-surface-container-highest px-2 py-1">
                    {repoInfo.username}
                  </code>
                </div>
                <div>
                  <span className="text-[10px] uppercase text-on-surface-variant font-bold block mb-1">
                    Пароль
                  </span>
                  <code className="text-sm text-secondary bg-surface-container-highest px-2 py-1">
                    {repoInfo.password}
                  </code>
                </div>
              </div>
            </div>
            <p className="text-xs text-on-surface-variant leading-relaxed">
              Склонируйте репозиторий, выполните задание и сделайте push.
              Результат будет проверен автоматически через GitLab CI.
            </p>
          </div>
        ) : (
          <div>
            <p className="text-sm text-on-surface-variant mb-4">
              Нажмите кнопку чтобы получить персональный репозиторий с заданием.
            </p>
            <Button onClick={startTask} disabled={loading} size="lg" className="w-full">
              {loading ? 'Создание...' : 'Начать задание'}
            </Button>
          </div>
        )}
      </section>

      {error && (
        <div className="bg-error/10 border border-error/20 px-4 py-3 text-error text-sm">
          {error}
        </div>
      )}
    </>
  );
}
