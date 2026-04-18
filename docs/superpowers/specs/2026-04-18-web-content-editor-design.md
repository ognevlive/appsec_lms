# Web UI для редактирования курсов и контента

**Дата:** 2026-04-18
**Статус:** Design approved, pending spec review
**Контекст:** Сейчас весь контент (курсы, модули, таски) живёт в YAML в `tasks/` и заливается в БД через `backend/seed.py` / `scripts/deploy-labs.sh`. Любая правка требует git-коммита и ручного пересеединга. Цель — перевести всё управление контентом в web UI.

## 1. Скоуп и принципы

- **БД — единственный источник правды** после миграции. YAML-файлы в `tasks/` замораживаются и удаляются.
- Через UI редактируется всё: курсы, модули, юниты, таски всех типов (`quiz`, `theory`, `ctf`, `ssh_lab`, `gitlab`).
- **Dockerfile и исходники CTF/ssh_lab в системе не хранятся.** Авторы CTF собирают образы у себя и пушат в registry (Docker Hub / GHCR / приватный). В UI указывается только ссылка на образ (`docker_image`), порт, TTL, flag hash.
- **Публикация:** флаг `Course.is_visible` (default false). Скрытый курс невидим студентам. Внутри видимого курса все правки модулей/юнитов/тасков — live.
- **Импорт/экспорт:** ZIP-бандлы с YAML-манифестами внутри. Два уровня: отдельный task, отдельный course (с опциональным bundle — включением referenced tasks).
- Единственная роль с правами редактирования — `admin`. Новых ролей не вводим.

## 2. Изменения в модели данных

```python
class Course(Base):
    # ... существующие поля ...
    is_visible = Column(Boolean, default=False, nullable=False)

class Task(Base):
    # ... существующие поля ...
    author_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # audit
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

Новая миграция Alembic: `XXXX_add_course_visibility_and_task_audit.py`.

Существующие сущности (`Module`, `ModuleUnit`, `Task.config`, `Task.slug`) — без изменений.

Никаких новых таблиц (draft, version, file_storage) — первая итерация минимальна.

## 3. Backend: новый роутер

**Файл:** `backend/routers/admin_content.py`
**Префикс:** `/api/admin/content`
**Защита:** зависимость `require_admin` (как существующий `admin.py`).

### Courses

| Метод | Путь | Описание |
|---|---|---|
| GET | `/courses` | Список всех курсов (включая скрытые), с агрегатами |
| POST | `/courses` | Создать курс: `{title, slug, description, order, config}` |
| GET | `/courses/{id}` | Детали с модулями и юнитами |
| PATCH | `/courses/{id}` | Правка полей, включая `is_visible` |
| DELETE | `/courses/{id}` | Требует `is_visible=false`. Каскад на модули и юниты |
| POST | `/courses/{id}/reorder-modules` | Body: `[{module_id, order}]` |

### Modules

| Метод | Путь | Описание |
|---|---|---|
| POST | `/courses/{id}/modules` | Создать модуль |
| PATCH | `/modules/{id}` | `title, description, order, estimated_hours, learning_outcomes, config` |
| DELETE | `/modules/{id}` | Каскадно удаляет юниты (таски сохраняются) |
| POST | `/modules/{id}/reorder-units` | Body: `[{unit_id, order}]` |

### Units

| Метод | Путь | Описание |
|---|---|---|
| POST | `/modules/{id}/units` | Body: `{task_id, unit_order, is_required}` |
| PATCH | `/units/{id}` | `unit_order, is_required` |
| DELETE | `/units/{id}` | Удаляет связь, таск сохраняется |

### Tasks

| Метод | Путь | Описание |
|---|---|---|
| GET | `/tasks?type=&search=&unused=` | Фильтры по типу, поиск по title/slug, флаг unused |
| POST | `/tasks` | Создать. Валидация `config` по `type` через Pydantic |
| GET | `/tasks/{id}` | Детали + список курсов, где используется |
| PATCH | `/tasks/{id}` | Правка |
| DELETE | `/tasks/{id}` | 409 если используется. Ответ содержит `usage: [{course_id, module_id, unit_id}]` |

### Import/Export

| Метод | Путь | Описание |
|---|---|---|
| GET | `/tasks/{id}/export` | Возвращает zip (Content-Type: application/zip) |
| POST | `/tasks/import` | `multipart/form-data` zip. Матчинг по slug: create or update |
| GET | `/courses/{id}/export?bundle=true` | Zip с курсом + опционально все referenced таски |
| POST | `/courses/import` | Query: `import_tasks=bool`. Транзакция |

## 4. Формат ZIP-бандлов

### Task bundle (`task-{slug}.zip`)

```
manifest.yaml
```

Структура `manifest.yaml` — все поля `Task`:

```yaml
slug: gitleaks-basic
title: "Gitleaks — первый запуск"
type: ctf
description: "..."
order: 5
config:
  docker_image: myuser/lms-gitleaks-basic:v2
  flag_hash: "a1b2c3..."
  port: 5000
  ttl_minutes: 120
  difficulty: easy
```

Zip как формат сохраняем для всех типов (унификация + запас на будущее — картинки, attachments).

### Course bundle (`course-{slug}.zip`)

```
course.yaml
tasks/{slug}.yaml        # если bundle=true, по одному файлу на таск
```

`course.yaml`:

```yaml
slug: sast-secrets-track
title: "Static Analysis & Secrets Detection"
description: "..."
order: 4
is_visible: false
config:
  icon: search
  progression: linear
modules:
  - title: "Foundations"
    order: 1
    description: ""
    estimated_hours: null
    learning_outcomes: []
    config: {}
    units:
      - task_slug: sast-intro-video
        unit_order: 1
        is_required: true
      # ...
```

### Import-семантика

- Матчинг по **slug**. Slug существует → UPDATE, иначе CREATE.
- Конфликт значений — «импорт выигрывает» (admin-операция).
- `POST /courses/import` с `import_tasks=false`: если какой-то `task_slug` не найден в БД — **400 Bad Request** со списком недостающих slug-ов, ничего не сохраняется (транзакция).
- `is_visible` при импорте курса — всегда `false`, независимо от значения в YAML (защита от случайной публикации).
- Размер zip — лимит 10 MB.
- Zip-slip защита: нормализация путей, отказ на `..` и абсолютные пути.

## 5. Удаление старой логики

В рамках того же PR удаляется:

- `backend/seed.py`
- `backend/tests/test_seed_courses.py`
- `scripts/deploy-labs.sh`
- `scripts/migrate-tracks-to-courses.py` (одноразовая миграция, уже отработала)
- Папка `tasks/` целиком (`ctf/`, `quizzes/`, `theory/`, `tracks/`, `courses/`)
- Разделы «Добавление нового CTF-задания» и «Скрипт deploy-labs.sh» из `README.md` — заменить на «Контент управляется через админ-панель»
- Фикстуры в `backend/tests/`, опирающиеся на YAML из `tasks/`

Остаётся:

- `scripts/smoke-course-flow.sh` — расширить под новые UI-флоу
- Alembic-миграции

### Миграция действующей инсталляции

Чеклист для оператора **перед мёржем PR**:

1. На каждой инсталляции (prod, staging, dev) прогнать текущий `./scripts/deploy-labs.sh` — контент попадёт в БД.
2. Сделать бэкап БД.
3. Накатить этот PR (git pull + docker compose up --build).
4. Применить миграцию: `alembic upgrade head`.
5. Убедиться, что курсы на месте (`GET /api/courses`).
6. Все дальнейшие правки — через UI.

## 6. Frontend: новые страницы

Все под `frontend/src/pages/admin/`.

### `AdminCoursesPage.tsx` — список курсов

- Таблица: title, slug, кол-во модулей/юнитов, toggle `is_visible`, order.
- Кнопки: «Новый курс», «Импорт» (upload zip).
- Клик по строке → `CourseEditorPage`.

### `CourseEditorPage.tsx` — главная страница работы с курсом

- **Левая колонка:** метаданные курса (title, slug, description, order, config.icon, config.progression, `is_visible`). Save-on-blur.
- **Правая колонка:** дерево модулей.
  - Каждый модуль — сворачиваемая карточка. Inline-правка: title, description, estimated_hours, learning_outcomes (chips), config.
  - Внутри модуля — список юнитов. У каждого: task title + type badge, чекбокс `is_required`, «удалить из модуля».
  - Drag-and-drop для модулей и юнитов внутри модуля (`@dnd-kit/core`).
  - Кнопка «+ Добавить юнит» → модалка `TaskPicker` (поиск + фильтр по type + кнопка «Создать новый таск»).
- **Верхний бар:** «Экспорт» (с чекбоксом «bundle»), «Удалить курс».

### `AdminTasksPage.tsx` — библиотека тасков

- Таблица: title, slug, type badge, updated_at, «используется в N курсах» (ссылка на список).
- Фильтры: type, search, only unused.
- Кнопки: «Новый таск», «Импорт».
- Клик → `TaskEditor`.

### `TaskEditor` — форма редактирования (модалка или страница)

**Общая шапка:** title, slug (auto из title, editable), description (markdown + preview), order.

**Type-specific секция:**

- **theory:**
  - `content_kind`: `text | video`.
  - Если `text`: markdown-редактор с preview.
  - Если `video`: поля `video.provider` (youtube/vimeo/url), `video.url`, `video.duration_seconds`.
- **quiz:**
  - Список вопросов — карточки с текстом вопроса + варианты (add/remove/reorder) + флаг правильности.
  - `pass_threshold` (%), `shuffle` (bool).
- **ctf:**
  - `docker_image` (text), `port` (number), `ttl_minutes`, `flag` (password; при save → SHA256 → `flag_hash`; если хэш уже есть — показ «Flag hash set» + «Изменить»), `difficulty` (enum easy/medium/hard).
- **ssh_lab:**
  - `docker_image`, `ttl_minutes`, `flag`, `terminal_port` (default 80), `difficulty`, инструкции (markdown).
- **gitlab:**
  - Существующая `config` gitlab-таска как JSON-форма.

**Кнопки:** Save, Export, Delete (disabled если used in courses — tooltip со списком).

### Навигация

В админский sidebar (сейчас Users / Containers / Results) — добавить «Курсы» и «Таски».

## 7. Валидация и edge cases

- **Slug:** `^[a-z0-9-]{2,100}$`. Auto-generate при создании (транслит + дефисы). При изменении — warning «сломаются внешние ссылки и импорты».
- **Удаление таска, используемого в курсе:** 409 Conflict. Ответ содержит usage-список, UI выводит ссылки на курсы.
- **Удаление модуля с юнитами:** confirm «Удалятся N юнитов (таски сохранятся)».
- **Удаление курса:** требует `is_visible=false` + явное подтверждение.
- **Docker image доступность:** при сохранении `docker pull` не делаем (registry может быть приватным, долго). Ошибка ловится при первом запуске студентом — текущий `docker_manager` её уже обрабатывает.
- **Flag-хэширование:** plaintext `flag` хэшируется в SHA256, plaintext **нигде не сохраняется** (ни в БД, ни в логах).
- **Concurrency:** last-write-wins. Оптимистичных блокировок не делаем в первой итерации. Если станет проблемой — добавим `If-Unmodified-Since` по `updated_at`.
- **Zip-импорт:** 10 MB лимит, zip-slip защита, валидация через те же Pydantic-схемы, что и внутренние API.

## 8. Тестирование

### Backend (pytest + httpx AsyncClient)

- CRUD каждой сущности: права доступа (non-admin → 403).
- Валидация slug, type-specific config, flag-хэширование.
- Export → Import round-trip: контент идентичен после цикла.
- Удаление таска, используемого в курсе — 409 с детализацией usage.
- Course bundle import с отсутствующими `task_slug` — 400, ничего не сохраняется.
- Zip-slip: zip с путём `../evil.yaml` отклоняется.
- Переключение `is_visible` → студенческий `GET /api/courses` отражает изменение.

### Frontend

- Расширить `scripts/smoke-course-flow.sh`: создать курс через UI → добавить модуль → добавить quiz-юнит → опубликовать → студент видит в каталоге.
- Drag-and-drop — юнит-тесты на `POST /reorder-*` API, UI тестится вручную.

## 9. Rollout

- Один PR, одна миграция Alembic.
- Одновременный снос `seed.py` / `deploy-labs.sh` / `tasks/`.
- Жёсткий чеклист в PR description: «PROD OPERATORS: прогнать seed ДО pull этого PR, иначе контент пропадёт».
- Первые пару дней после мёржа — ежедневный бэкап БД (контент теперь живёт только там).

## Out of scope (следующие итерации)

- Черновики / версионирование контента.
- История правок, undo.
- Роль content-author (между student и admin).
- Multi-user concurrent editing с локами или CRDT.
- Встроенная сборка Docker-образов (build-in-app).
- Загрузка медиа (картинки в theory, видео-файлы) — пока только внешние URL.
- Public Docker Hub discovery / шаблоны CTF-тасков.
