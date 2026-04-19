import { useEffect, useMemo, useRef, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api';
import Breadcrumbs from '../components/Breadcrumbs';
import PulseIndicator from '../components/PulseIndicator';
import DifficultyIndicator from '../components/DifficultyIndicator';
import Icon from '../components/Icon';
import QuizSection from '../sections/QuizSection';
import CtfSection from '../sections/CtfSection';
import GitlabSection from '../sections/GitlabSection';
import TheorySection from '../sections/TheorySection';
import SshLabSection from '../sections/SshLabSection';
import FileUploader from '../components/FileUploader';
import SubmissionHistory from '../components/SubmissionHistory';
import { Md, MdInline } from '../components/Md';
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

  const DEFAULT_EXT = ['pdf', 'png', 'jpg', 'zip', 'txt', 'md', 'docx', 'py', 'js', 'ts'];
  const rawUpload = task?.config?.file_upload as
    | { enabled?: boolean; max_files?: number; max_size_mb?: number; allowed_ext?: string[]; required?: boolean }
    | null
    | undefined;
  const uploadCfg = rawUpload && rawUpload.enabled
    ? {
        enabled: true,
        max_files: rawUpload.max_files ?? 5,
        max_size_mb: rawUpload.max_size_mb ?? 20,
        allowed_ext: rawUpload.allowed_ext?.length ? rawUpload.allowed_ext : DEFAULT_EXT,
        required: !!rawUpload.required,
      }
    : null;
  const answerCfg = (task?.config?.answer_text ?? { enabled: false, required: false }) as
    { enabled: boolean; required: boolean };
  const isManual = task?.config?.review_mode === 'manual';
  const needsReviewBlock = (uploadCfg && uploadCfg.enabled) || isManual;

  const [files, setFiles] = useState<File[]>([]);
  const [answer, setAnswer] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const latestSubmission = useMemo(
    () => (submissions && submissions.length ? submissions[0] : null),
    [submissions]
  );
  const canSubmit = !latestSubmission || latestSubmission.status === 'fail';

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!task) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const form = new FormData();
      if (answer) form.append('answer_text', answer);
      files.forEach((f) => form.append('files', f));
      await api.submitTask(task.id, form);
      // reload
      window.location.reload();
    } catch (err: any) {
      setSubmitError(err.message || 'Ошибка отправки');
    } finally {
      setSubmitting(false);
    }
  }

  const markedRef = useRef(false);
  useEffect(() => {
    if (!task || task.type !== 'theory' || markedRef.current) return;
    markedRef.current = true;
    api.markViewed(task.id).catch(() => {});
  }, [task]);

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
            {task.type === 'theory' ? (
              <>
                <Icon name="menu_book" size="sm" className="text-amber-400" />
                <span className="text-[10px] font-bold text-amber-400 uppercase tracking-widest">
                  Теоретический материал
                </span>
              </>
            ) : (
              <>
                <PulseIndicator color={hasSuccess ? 'primary' : 'secondary'} />
                <span className="text-[10px] font-bold text-primary uppercase tracking-widest">
                  {hasSuccess ? 'Задание пройдено' : 'Активное задание'}
                </span>
              </>
            )}
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
            <Md className="space-y-0">{task.description}</Md>

            {/* Technical requirements if in config */}
            {task.type !== 'theory' && task.config?.requirements && (
              <div className="mt-10">
                <h4 className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-4">
                  Техническое задание
                </h4>
                <ul className="space-y-3 text-sm">
                  {(task.config.requirements as string[]).map((req, i) => (
                    <li key={i} className="flex items-start gap-3">
                      <Icon name="check_circle" size="sm" className="text-primary mt-0.5" />
                      <span><MdInline>{req}</MdInline></span>
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
          {task.type === 'theory' && (
            <TheorySection config={task.config} />
          )}
          {task.type === 'ssh_lab' && (
            <SshLabSection taskId={taskId} config={task.config} onSubmit={refreshSubmissions} />
          )}

          {needsReviewBlock && (
            <section className="mt-6 space-y-3">
              <h3 className="text-lg font-medium">Сдача работы</h3>

              {latestSubmission && (
                <div
                  className={`rounded px-4 py-3 text-sm ${
                    latestSubmission.status === 'pending'
                      ? 'bg-yellow-500/10 text-yellow-300'
                      : latestSubmission.status === 'success'
                      ? 'bg-primary/10 text-primary'
                      : 'bg-red-500/10 text-red-400'
                  }`}
                >
                  {latestSubmission.status === 'pending' && 'Работа отправлена. Ожидает проверки преподавателем.'}
                  {latestSubmission.status === 'success' && 'Зачтено.'}
                  {latestSubmission.status === 'fail' && 'Не зачтено. Можно отправить ещё раз.'}
                  {latestSubmission.review_comment && (
                    <p className="mt-1 whitespace-pre-wrap">{latestSubmission.review_comment}</p>
                  )}
                </div>
              )}

              {canSubmit && (
                <form onSubmit={handleSubmit} className="space-y-3">
                  {answerCfg.enabled && (
                    <textarea
                      className="w-full rounded bg-surface-container-low p-3 text-sm"
                      rows={4}
                      placeholder={answerCfg.required ? 'Ответ (обязательно)' : 'Ответ (опционально)'}
                      value={answer}
                      onChange={(e) => setAnswer(e.target.value)}
                    />
                  )}
                  {uploadCfg && uploadCfg.enabled && (
                    <FileUploader
                      maxFiles={uploadCfg.max_files}
                      maxSizeMb={uploadCfg.max_size_mb}
                      allowedExt={uploadCfg.allowed_ext}
                      required={uploadCfg.required}
                      files={files}
                      onChange={setFiles}
                      disabled={submitting}
                    />
                  )}
                  {submitError && <p className="text-sm text-red-400">{submitError}</p>}
                  <button
                    type="submit"
                    disabled={submitting}
                    className="px-4 py-2 rounded bg-primary text-on-primary text-sm disabled:opacity-50"
                  >
                    {submitting ? 'Отправка…' : 'Отправить на проверку'}
                  </button>
                </form>
              )}

              {submissions && submissions.length > 1 && (
                <SubmissionHistory
                  items={submissions}
                  downloadUrl={(sid, fid) => api.fileDownloadUrl(sid, fid)}
                />
              )}
            </section>
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
                  {task.type === 'quiz' ? 'Тест' : task.type === 'ctf' ? 'CTF' : task.type === 'ssh_lab' ? 'SSH Lab' : task.type === 'gitlab' ? 'GitLab' : 'Теория'}
                </span>
              </div>
              {task.type !== 'theory' && (
                <div>
                  <span className="text-[10px] uppercase font-bold text-on-surface-variant block mb-1">
                    Попыток
                  </span>
                  <span className="text-sm">{submissions.length}</span>
                </div>
              )}
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

          {/* Theory References */}
          {task.theory_refs && task.theory_refs.length > 0 && (
            <div className="bg-surface-container-low p-6 border border-outline-variant/10">
              <h3 className="text-xs font-bold uppercase tracking-[0.3em] text-on-surface-variant mb-4 flex items-center gap-2">
                <Icon name="menu_book" size="sm" />
                Теория
              </h3>
              <div className="space-y-3">
                {task.theory_refs.map((ref) => (
                  <Link
                    key={ref.id}
                    to={`/challenges/${ref.id}`}
                    className="flex items-center gap-2 text-sm text-secondary hover:text-primary transition-colors"
                  >
                    <Icon name="auto_stories" size="sm" />
                    {ref.title}
                  </Link>
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
