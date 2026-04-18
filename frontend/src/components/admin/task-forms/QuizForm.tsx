import Button from '../../Button';
import FormInput from '../../FormInput';

interface Choice {
  text: string;
  correct: boolean;
}
interface Question {
  id?: number;
  text: string;
  options: Choice[];
}

export default function QuizForm({
  config,
  update,
}: {
  config: Record<string, any>;
  update: (p: Record<string, any>) => void;
}) {
  const questions: Question[] = config.questions || [];
  const setQuestions = (q: Question[]) => update({ questions: q });

  const addQuestion = () =>
    setQuestions([
      ...questions,
      { text: '', options: [{ text: '', correct: true }] },
    ]);
  const patchQuestion = (i: number, patch: Partial<Question>) =>
    setQuestions(questions.map((q, idx) => (idx === i ? { ...q, ...patch } : q)));
  const removeQuestion = (i: number) =>
    setQuestions(questions.filter((_, idx) => idx !== i));

  return (
    <div className="space-y-4">
      <div className="flex gap-4 items-end">
        <FormInput
          label="Pass threshold %"
          type="number"
          value={String(config.pass_threshold ?? 70)}
          onChange={(e) => update({ pass_threshold: Number(e.target.value) })}
        />
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={!!config.shuffle}
            onChange={(e) => update({ shuffle: e.target.checked })}
          />
          Shuffle
        </label>
      </div>

      {questions.map((q, i) => (
        <div key={i} className="border border-outline-variant/30 p-4 space-y-2">
          <div className="flex items-center gap-2">
            <div className="text-sm font-bold">Q{i + 1}</div>
            <div className="flex-1" />
            <Button variant="danger" onClick={() => removeQuestion(i)}>
              Удалить
            </Button>
          </div>
          <div className="space-y-1">
            <label className="text-[10px] uppercase tracking-wider text-on-surface-variant font-bold ml-1">
              Question
            </label>
            <textarea
              className="w-full min-h-[72px] bg-surface-container-lowest border border-outline-variant/30 text-sm text-on-surface focus:border-primary focus:ring-0 focus:outline-none transition-colors placeholder:text-outline-variant px-3 py-2"
              value={q.text}
              onChange={(e) => patchQuestion(i, { text: e.target.value })}
            />
          </div>
          <div className="space-y-1">
            {q.options.map((o, j) => (
              <div key={j} className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={o.correct}
                  onChange={(e) =>
                    patchQuestion(i, {
                      options: q.options.map((oo, jj) =>
                        jj === j ? { ...oo, correct: e.target.checked } : oo,
                      ),
                    })
                  }
                />
                <input
                  className="flex-1 p-1 bg-surface-container-low"
                  value={o.text}
                  onChange={(e) =>
                    patchQuestion(i, {
                      options: q.options.map((oo, jj) =>
                        jj === j ? { ...oo, text: e.target.value } : oo,
                      ),
                    })
                  }
                />
                <Button
                  onClick={() =>
                    patchQuestion(i, {
                      options: q.options.filter((_, jj) => jj !== j),
                    })
                  }
                >
                  ×
                </Button>
              </div>
            ))}
            <Button
              onClick={() =>
                patchQuestion(i, {
                  options: [...q.options, { text: '', correct: false }],
                })
              }
            >
              + Вариант
            </Button>
          </div>
        </div>
      ))}
      <Button onClick={addQuestion}>+ Вопрос</Button>
    </div>
  );
}
