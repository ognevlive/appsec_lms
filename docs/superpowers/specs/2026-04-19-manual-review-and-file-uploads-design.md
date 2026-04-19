# Manual Review & File Uploads — Design

**Status:** approved
**Date:** 2026-04-19
**Scope:** расширение модели сабмишенов и UX для задач, требующих ручной проверки преподавателем и/или прикрепления файлов.

## Цель

Сейчас все задачи проверяются автоматически: quiz — по ключам, ctf — по флагу, theory — фактом просмотра. Нужно:

1. Помечать отдельные задачи как «проверяется преподавателем» независимо от типа.
2. Разрешить студенту прикладывать к сабмишену произвольные файлы.
3. Дать преподавателю очередь непроверенных работ, карточку сабмишена, вердикт с комментарием.
4. Поддержать пересдачу после `fail`.

## Нефункциональные требования

- Локальное хранение файлов в volume, без внешних сервисов.
- Лимиты: 5 файлов × 20 МБ, whitelist расширений.
- Файлы отдаются только через auth-роуты (ownership / admin).
- Существующее поведение auto-типов не ломается.

## Модель данных

### Флаги в `task.config`

Без нового `TaskType`. Любой существующий тип (`quiz`, `ctf`, `gitlab`, `theory`, `ssh_lab`) может иметь:

```json
{
  "review_mode": "manual",            // "auto" (default) | "manual"
  "file_upload": {
    "enabled": true,                  // default false
    "max_files": 5,
    "max_size_mb": 20,
    "allowed_ext": ["pdf","png","jpg","zip","txt","md","docx","py","js","ts"],
    "required": true                  // минимум 1 файл обязателен
  },
  "answer_text": {
    "enabled": true,                  // optional текст-ответ
    "required": false
  }
}
```

Если поле `file_upload` отсутствует — загрузка недоступна. Если `review_mode` отсутствует — проверка автоматическая (текущее поведение).

### Изменения схемы

**`task_submissions`** — новые колонки:

| column           | type                    | null | notes                      |
|------------------|-------------------------|------|----------------------------|
| `reviewer_id`    | `integer FK users.id`   | yes  | кто поставил вердикт       |
| `reviewed_at`    | `timestamptz`           | yes  |                            |
| `review_comment` | `text`                  | yes  | текст от преподавателя     |

**Новая таблица `submission_files`** (1:N к `task_submissions`):

| column          | type               | null | notes                              |
|-----------------|--------------------|------|------------------------------------|
| `id`            | `integer PK`       | no   |                                    |
| `submission_id` | `integer FK ON DELETE CASCADE` | no | → task_submissions.id   |
| `filename`      | `varchar(255)`     | no   | оригинальное имя для отображения   |
| `stored_path`   | `varchar(500)`     | no   | относительный путь от `UPLOADS_DIR`|
| `size_bytes`    | `integer`          | no   |                                    |
| `content_type`  | `varchar(100)`     | yes  |                                    |
| `uploaded_at`   | `timestamptz`      | no   | `server_default now()`             |

Миграция: `backend/alembic/versions/0005_manual_review_and_uploads.py`.

### Поведение статусов

Enum `SubmissionStatus` не меняется — `pending/success/fail`. Логика:

- `review_mode=auto` — текущее поведение: сабмишен сразу `success` или `fail`.
- `review_mode=manual` — сабмишен создаётся со статусом `pending`. Для `quiz` автооценка всё равно считается и пишется в `details.auto_score` (`{score, total, correct, wrong}`), но финальный статус ставит преподаватель.
- Пересдача после `fail` — новая строка `task_submissions`. `unlock_guard` и `progress` по-прежнему определяют «задача выполнена» как «есть хотя бы один `success`» — менять не нужно.

## API

### Студент

| Метод | Путь | Назначение |
|-------|------|------------|
| `POST` | `/api/submissions/{task_id}` | multipart/form-data: `answer_text?`, `files[]?`. Валидация по `task.config`. Файлы → `UPLOADS_DIR/{submission_id}/{file_id}_{sanitized_name}`. Для `auto` запускает существующую логику проверки; для `manual` — статус `pending`. |
| `GET` | `/api/submissions/{submission_id}` | свой сабмишен: статус, ответ, файлы (метаданные), `review_comment`, `auto_score`. |
| `GET` | `/api/submissions/{submission_id}/files/{file_id}` | скачать свой файл (attachment). |
| `GET` | `/api/me/submissions?task_id=` | история попыток по задаче. |

Существующий `POST /api/quiz/{id}/submit` оставляем как совместимый shortcut для `review_mode=auto` + без файлов. Для `manual` quiz клиент использует общий `POST /api/submissions/{task_id}`.

`POST /api/me/progress/viewed` продолжает работать для theory без `review_mode=manual` и без `file_upload.enabled`.

### Преподаватель

| Метод | Путь | Назначение |
|-------|------|------------|
| `GET` | `/api/admin/review/queue` | список `pending` сабмишенов задач с `review_mode=manual`; фильтры `course_id`, `user_id`, `task_id`; пагинация. |
| `GET` | `/api/admin/review/queue/count` | число непроверенных — для бейджа в сайдбаре. |
| `GET` | `/api/admin/submissions/{id}` | полная карточка: студент, задача, ответ, файлы, история попыток. |
| `GET` | `/api/admin/submissions/{id}/files/{file_id}` | скачивание любого файла. |
| `POST` | `/api/admin/submissions/{id}/review` | `{status: "success" \| "fail", comment: str}`. Устанавливает `reviewer_id`, `reviewed_at`, `review_comment`, статус. 400 если сабмишен уже проверен. |

Все admin-роуты защищены существующим `require_admin`.

### Валидация загрузки

При `POST /api/submissions/{task_id}`:

- `task.config.file_upload.enabled` должен быть `true`, если файлы переданы.
- Число файлов ≤ `max_files`.
- Каждый размер ≤ `max_size_mb`.
- Расширение из `allowed_ext` (lowercase, fallback `UPLOADS_ALLOWED_EXT_DEFAULT`).
- `content-type` cross-check: `mimetypes.guess_type(filename)` не должен конфликтовать с известным типом (warn-only для MVP).
- Если `file_upload.required=true` — пустой список файлов → 400.
- Если `answer_text.required=true` и пусто — 400.

## Frontend

### Студент

- `ChallengeDetailsPage.tsx` — при `file_upload.enabled || review_mode=manual` рендерит блок «Сдача работы»:
  - `<textarea>` ответа (если `answer_text.enabled`), подсказка об обязательности.
  - `FileUploader.tsx` (новый): drag-and-drop, выбор через кнопку, локальный список с удалением до отправки, подсказка с лимитами.
  - Кнопка «Отправить на проверку» → `api.submitTask(taskId, formData)`.
- После отправки — плашка статуса:
  - `pending` → «На проверке у преподавателя», список файлов.
  - `success` → зелёная плашка + `review_comment` (если есть).
  - `fail` → красная плашка + `review_comment` + кнопка «Отправить ещё раз» (создаёт новый сабмишен).
- `SubmissionHistory.tsx` (новый): свёрнутый список прошлых попыток под текущим статусом.

### Преподаватель

- `/admin/review` → `AdminReviewQueuePage.tsx`:
  - Таблица: студент, задача, курс, дата, кнопка «Проверить».
  - Фильтры: курс, студент, задача.
  - Пагинация через существующий `Pagination.tsx`.
- `/admin/review/:submissionId` → `AdminReviewDetailPage.tsx`:
  - Карточка: студент, задача, ответ, файлы (скачивание), `auto_score` для quiz, история предыдущих попыток.
  - Форма вердикта: радио `success`/`fail`, textarea комментария, кнопка «Сохранить вердикт».
  - После отправки → редирект в очередь.
- `Sidebar.tsx` (admin-режим): пункт «Проверка работ» с бейджом-счётчиком. Polling `GET /queue/count` каждые 30с и при навигации.

### API client (`frontend/src/api.ts`)

Новые методы: `submitTask(taskId, formData)`, `getSubmission(id)`, `getMySubmissions(taskId)`, `getReviewQueue(filters)`, `getReviewQueueCount()`, `getAdminSubmission(id)`, `reviewSubmission(id, {status, comment})`, `downloadSubmissionFile(submissionId, fileId)`.

## Хранение и безопасность

### Хранение

- Volume `./uploads` (хост) → `/app/uploads` (контейнер backend). Добавить volume в `docker-compose.yml`.
- Настройки:
  - `UPLOADS_DIR` (default `/app/uploads`)
  - `UPLOADS_MAX_SIZE_MB` (default 20) — глобальный потолок
  - `UPLOADS_ALLOWED_EXT_DEFAULT` (default список выше) — fallback
- Структура: `{UPLOADS_DIR}/{submission_id}/{file_id}_{sanitized_name}`.
- Санитизация имени: удаление path separators и управляющих символов, NFC-нормализация unicode, обрезка до 200 символов. Оригинальное имя хранится в БД, для отображения в UI.
- Имя на диске формируется как `{secrets.token_hex(8)}_{sanitized}` — защита от коллизий и перезаписей.
- Stream-копирование: `shutil.copyfileobj(upload.file, dst, length=1<<20)` — не читаем всё в память.

### Безопасность

- Скачивание файлов — только через auth-роуты:
  - студент может скачать файл только из своего сабмишена (проверка `submission.user_id == current_user.id`);
  - admin — любой файл.
- Никаких прямых Traefik/nginx-маршрутов на `/uploads`.
- `Content-Disposition: attachment; filename="..."` на выдаче — исключает inline-рендер HTML/SVG.
- Расширение `.html`, `.svg`, исполняемые форматы — по умолчанию не входят в whitelist.
- При удалении сабмишена (каскад через БД) сервисный слой также удаляет директорию `{UPLOADS_DIR}/{submission_id}` через `shutil.rmtree(..., ignore_errors=True)`.

### Сервисы

- `backend/services/uploads.py` — новый модуль: `save_submission_files`, `delete_submission_files`, `stream_submission_file`, санитизация и валидация.
- `backend/routers/submissions.py` — новый роутер для студентских сабмишенов.
- `backend/routers/admin_review.py` — новый роутер для очереди преподавателя.

## Тесты

### Backend (pytest)

- `test_uploads_sanitize.py` — санитизация имён, лимиты, whitelist, MIME cross-check.
- `test_submissions_student.py` — создание сабмишена с файлами; ownership при скачивании; запрет загрузки при `file_upload.enabled=false`; required поля.
- `test_admin_review.py` — очередь с фильтрами и счётчиком; POST вердикта успеха/провала; повторный вердикт → 400; admin-only guard.
- `test_manual_quiz.py` — `review_mode=manual` на quiz: статус остаётся `pending`, `auto_score` в details; после вердикта → корректный статус.
- `test_resubmission.py` — после `fail` студент может создать новый сабмишен; `unlock_guard` и `progress` видят `success`.

### Frontend

- Существующий стек. Минимально: компонентный тест `FileUploader.tsx` (валидация лимитов на клиенте) и smoke на `AdminReviewQueuePage`.

## План миграции данных

- Существующие сабмишены: `reviewer_id = null`, `reviewed_at = null`, `review_comment = null` — безопасные default'ы.
- Existing tasks: без `review_mode` и `file_upload` в `config` → поведение не меняется.

## Out of scope

- E-mail / push-уведомления (бейдж и polling достаточно для MVP).
- Антивирус-сканирование загруженных файлов.
- Общий storage (S3/MinIO) — при росте переносится отдельным проектом.
- Версионность файлов внутри одного сабмишена.
- Частичная оценка (баллы от 0 до max).
