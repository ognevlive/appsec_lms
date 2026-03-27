import { useEffect, useState } from 'react';
import { api } from '../api';
import Button from '../components/Button';
import Icon from '../components/Icon';
import type { QuizQuestion, QuizResult } from '../types';

interface QuizSectionProps {
  taskId: number;
  onSubmit: () => void;
}

export default function QuizSection({ taskId, onSubmit }: QuizSectionProps) {
  const [questions, setQuestions] = useState<QuizQuestion[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<QuizResult | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.getQuestions(taskId).then(setQuestions).catch(() => {});
  }, [taskId]);

  const selectAnswer = (qid: number, option: string) => {
    if (result) return;
    setAnswers((prev) => ({ ...prev, [String(qid)]: option }));
  };

  const submit = async () => {
    setError('');
    setLoading(true);
    try {
      const res = await api.submitQuiz(taskId, answers);
      setResult(res);
      onSubmit();
    } catch (err: any) {
      setError(err.message);
    }
    setLoading(false);
  };

  return (
    <>
      {questions.map((q) => {
        const isCorrect = result?.correct.includes(q.id);
        const isWrong = result?.wrong.includes(q.id);
        return (
          <section key={q.id} className="bg-surface-container-low p-6">
            <h4 className="text-sm font-bold text-on-surface mb-4 flex items-center gap-2">
              <span className="text-on-surface-variant font-mono text-xs">{q.id}.</span>
              {q.text}
              {isCorrect && <Icon name="check_circle" size="sm" className="text-primary" filled />}
              {isWrong && <Icon name="cancel" size="sm" className="text-tertiary" filled />}
            </h4>
            <div className="space-y-2">
              {q.options.map((opt) => {
                const selected = answers[String(q.id)] === opt;
                return (
                  <button
                    key={opt}
                    onClick={() => selectAnswer(q.id, opt)}
                    className={`w-full text-left px-4 py-3 text-sm transition-all ${
                      selected
                        ? 'bg-primary/10 text-primary border-l-2 border-primary'
                        : 'bg-surface-container hover:bg-surface-bright text-on-surface-variant hover:text-on-surface'
                    } ${result ? 'cursor-default' : 'cursor-pointer'}`}
                  >
                    {opt}
                  </button>
                );
              })}
            </div>
          </section>
        );
      })}

      {error && (
        <div className="bg-error/10 border border-error/20 px-4 py-3 text-error text-sm">
          {error}
        </div>
      )}

      {result ? (
        <section className="bg-surface-container-low p-6">
          <h3 className="text-xl font-headline font-bold mb-2">
            Результат: <span className="text-primary">{result.score}</span>/{result.total}
          </h3>
          {result.score === result.total && (
            <p className="text-primary text-sm font-bold">Все ответы верные!</p>
          )}
        </section>
      ) : (
        questions.length > 0 && (
          <Button
            onClick={submit}
            disabled={loading || Object.keys(answers).length !== questions.length}
            size="lg"
            className="w-full"
          >
            {loading ? 'Отправка...' : 'Отправить ответы'}
          </Button>
        )
      )}
    </>
  );
}
