import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api';
import Breadcrumbs from '../components/Breadcrumbs';
import PulseIndicator from '../components/PulseIndicator';
import DifficultyIndicator from '../components/DifficultyIndicator';
import Icon from '../components/Icon';
import QuizSection from '../sections/QuizSection';
import CtfSection from '../sections/CtfSection';
import GitlabSection from '../sections/GitlabSection';
import type { TaskDetail, Submission } from '../types';

export default function ChallengeDetailsPage() {
  const { id } = useParams<{ id: string }>();
  const taskId = Number(id);
  const [task, setTask] = useState<TaskDetail | null>(null);
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.getTask(taskId),
      api.mySubmissions(taskId),
    ])
      .then(([t, s]) => {
        setTask(t);
        setSubmissions(s);
      })
      .finally(() => setLoading(false));
  }, [taskId]);

  const refreshSubmissions = () => {
    api.mySubmissions(taskId).then(setSubmissions).catch(() => {});
  };

  if (loading || !task) {
    return (
      <div className="flex items-center justify-center h-64">
        <span className="text-primary animate-pulse font-headline text-xl">Загрузка...</span>
      </div>
    );
  }

  const difficulty = task.config?.difficulty || task.difficulty;
  const maxPoints = task.config?.max_points || task.max_points;
  const materials = task.config?.materials as { title: string; url: string }[] | undefined;
  const hasSuccess = submissions.some((s) => s.status === 'success');

  return (
    <div className="max-w-[1400px] mx-auto">
      {/* Breadcrumbs */}
      <Breadcrumbs
        items={[
          { label: 'Задания', to: '/challenges' },
          { label: task.title },
        ]}
      />

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <PulseIndicator color={hasSuccess ? 'primary' : 'secondary'} />
            <span className="text-[10px] font-bold text-primary uppercase tracking-widest">
              {hasSuccess ? 'Задание пройдено' : 'Активное задание'}
            </span>
          </div>
          <h1 className="text-4xl md:text-6xl font-headline font-bold tracking-tighter leading-none">
            {task.title}
          </h1>
        </div>
      </div>

      {/* Bento Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-10 gap-6">
        {/* Left Column (70%) */}
        <div className="lg:col-span-7 space-y-6">
          {/* Task Description */}
          <section className="bg-surface-container-low p-8 relative overflow-hidden">
            <div className="absolute top-0 right-0 p-4 opacity-5 pointer-events-none">
              <span className="material-symbols-outlined text-[120px]">database</span>
            </div>
            <h3 className="text-xs font-bold uppercase tracking-[0.3em] text-primary mb-6 flex items-center gap-2">
              <Icon name="description" size="sm" />
              Описание задания
            </h3>
            <div className="space-y-4 text-on-surface/80 leading-relaxed">
              {task.description.split('\n').map((p, i) => (
                <p key={i}>{p}</p>
              ))}
            </div>

            {/* Technical requirements if in config */}
            {task.config?.requirements && (
              <div className="mt-10">
                <h4 className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-4">
                  Техническое задание
                </h4>
                <ul className="space-y-3 text-sm">
                  {(task.config.requirements as string[]).map((req, i) => (
                    <li key={i} className="flex items-start gap-3">
                      <Icon name="check_circle" size="sm" className="text-primary mt-0.5" />
                      <span>{req}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </section>

          {/* Type-specific section */}
          {task.type === 'quiz' && (
            <QuizSection taskId={taskId} onSubmit={refreshSubmissions} />
          )}
          {task.type === 'ctf' && (
            <CtfSection taskId={taskId} config={task.config} onSubmit={refreshSubmissions} />
          )}
          {task.type === 'gitlab' && (
            <GitlabSection taskId={taskId} />
          )}
        </div>

        {/* Right Column (30%) */}
        <div className="lg:col-span-3 space-y-6">
          {/* Info Panel */}
          <div className="bg-surface-container-low p-6 border border-outline-variant/10">
            <h3 className="text-xs font-bold uppercase tracking-[0.3em] text-on-surface-variant mb-6">
              Информация
            </h3>
            <div className="space-y-5">
              <div>
                <DifficultyIndicator level={difficulty} />
              </div>
              {maxPoints && (
                <div>
                  <span className="text-[10px] uppercase font-bold text-on-surface-variant block mb-1">
                    Максимум баллов
                  </span>
                  <span className="text-2xl font-headline font-bold text-primary">{maxPoints}</span>
                  <span className="text-xs text-on-surface-variant ml-1">XP</span>
                </div>
              )}
              <div>
                <span className="text-[10px] uppercase font-bold text-on-surface-variant block mb-1">
                  Тип
                </span>
                <span className="text-sm font-bold uppercase text-secondary">
                  {task.type === 'quiz' ? 'Тест' : task.type === 'ctf' ? 'CTF' : 'GitLab'}
                </span>
              </div>
              <div>
                <span className="text-[10px] uppercase font-bold text-on-surface-variant block mb-1">
                  Попыток
                </span>
                <span className="text-sm">{submissions.length}</span>
              </div>
            </div>
          </div>

          {/* Materials */}
          {materials && materials.length > 0 && (
            <div className="bg-surface-container-low p-6 border border-outline-variant/10">
              <h3 className="text-xs font-bold uppercase tracking-[0.3em] text-on-surface-variant mb-4">
                Материалы
              </h3>
              <div className="space-y-3">
                {materials.map((m, i) => (
                  <a
                    key={i}
                    href={m.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 text-sm text-secondary hover:text-primary transition-colors"
                  >
                    <Icon name="link" size="sm" />
                    {m.title}
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* Recent Submissions */}
          {submissions.length > 0 && (
            <div className="bg-surface-container-low p-6 border border-outline-variant/10">
              <h3 className="text-xs font-bold uppercase tracking-[0.3em] text-on-surface-variant mb-4">
                История попыток
              </h3>
              <div className="space-y-2">
                {submissions.slice(0, 5).map((s) => (
                  <div key={s.id} className="flex justify-between items-center text-xs py-1">
                    <span className="text-on-surface-variant font-mono">
                      {new Date(s.submitted_at).toLocaleString('ru-RU')}
                    </span>
                    <span
                      className={`font-bold uppercase ${
                        s.status === 'success' ? 'text-primary' : s.status === 'fail' ? 'text-tertiary' : 'text-secondary'
                      }`}
                    >
                      {s.status === 'success' ? 'Успех' : s.status === 'fail' ? 'Ошибка' : 'Ожидание'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
