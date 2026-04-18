# Design Spec: Course → Module → Unit Hierarchy

**Date:** 2026-04-18
**Author:** brainstorming session with Roman Ognev
**Status:** Approved for planning

---

## 1. Цель и контекст

Текущая модель представления контента в LMS плоская: `Track → TrackStep → Task`. У некоторых треков (SAST, 31 задача) модули уже фактически существуют — но только как комментарии-разделители в YAML. Для студентов нет навигации по модулям, нет описаний модулей, нет прогресса внутри модуля.

Цель — перестроить представление контента в Coursera-подобный формат: **Course → Module → Unit**, где Unit — минимальная единица контента (тест, лаба или теоретический материал: текст/видео), Module объединяет связанные Units, а Course = набор Modules.

### Не в scope

- Админ-UI для создания/редактирования курсов (YAML остаётся источником истины)
- Хостинг видео (задел в схеме есть, реальные провайдеры добавим отдельной итерацией)
- Сертификаты / peer review / обсуждения / оценки преподавателей
- Расписание / дедлайны
- Подписки / биллинг
- Новый верхний уровень над Course (курс остаётся верхом иерархии контента)

---

## 2. Ключевые решения (из брейнсторма)

| № | Вопрос | Выбор |
|---|---|---|
| 1 | Терминология / иерархия | `Track` переименовывается в `Course`. Иерархия `Course → Module → Unit (= Task)`. |
| 2 | Привязка Unit к Module | Unit — самостоятельная сущность. Module → Unit через M:N связь (`module_units`). Переиспользование задач сохраняется. |
| 3 | Прогрессия / разблокировка | Настраивается per-course: `config.progression: linear | free` (default `free`). Внутри модуля всегда свободный порядок. |
| 4 | Обязателен ли Module | Да, всегда. Короткие курсы — один модуль «Основы». |
| 5 | Метаданные модуля | Coursera-like: `title`, `description`, `order`, `estimated_hours`, `learning_outcomes`, `icon`. |
| 6 | Видео-контент | Один `TaskType.theory`, `config.content_kind: text \| video \| mixed`. Задел под провайдеров в `config.video`. |

---

## 3. Модель данных

### 3.1 Новые / изменённые таблицы

```python
class Course(Base):                      # ex-Track
    __tablename__ = "courses"
    id: int (PK)
    title: str(255)
    slug: str(100) UNIQUE
    description: text
    order: int = 0
    config: JSONB = {}
    # config schema:
    #   icon: str (optional)
    #   progression: "linear" | "free" (default "free")
    created_at: datetime

    modules: relationship("Module", order_by="Module.order", cascade="all, delete-orphan")


class Module(Base):
    __tablename__ = "modules"
    id: int (PK)
    course_id: int (FK courses.id, ON DELETE CASCADE)
    title: str(255)
    description: text = ""
    order: int = 0
    estimated_hours: int (nullable)
    learning_outcomes: JSONB = []            # list[str]
    config: JSONB = {}                       # { icon }
    created_at: datetime

    __table_args__ = (UniqueConstraint("course_id", "order"),)

    course: relationship("Course", back_populates="modules")
    units: relationship("ModuleUnit", order_by="ModuleUnit.unit_order",
                        cascade="all, delete-orphan")


class ModuleUnit(Base):                  # ex-TrackStep
    __tablename__ = "module_units"
    id: int (PK)
    module_id: int (FK modules.id, ON DELETE CASCADE)
    task_id: int (FK tasks.id)
    unit_order: int = 0
    is_required: bool = True              # для gating в linear-режиме

    __table_args__ = (UniqueConstraint("module_id", "task_id"),)

    module: relationship("Module", back_populates="units")
    task: relationship("Task")
```

### 3.2 Изменения существующих таблиц

**`tasks`:**
- Добавляется колонка `slug: VARCHAR(150) UNIQUE` — стабильный идентификатор для ссылок из YAML (вместо хрупкого поиска по `title`).
- `TaskType.theory` остаётся, но `config` расширяется:
  - `content_kind: "text" | "video" | "mixed"` (default `"text"`)
  - `video: { provider: "youtube" | "vimeo" | "url", src: str, duration_seconds?: int }` (опционально, для `video`/`mixed`)

**Удаляются:** `tracks`, `track_steps` (после Alembic-миграции).

### 3.3 Индексы

- `modules(course_id, order)` — для упорядоченной загрузки модулей курса
- `module_units(module_id, unit_order)` — для упорядоченной загрузки юнитов модуля
- `tasks(slug)` — уникальный, для lookup из seed
- `task_submissions(user_id, task_id)` — уже существует

### 3.4 Прогрессия: функция `is_module_locked`

Чистая функция в `backend/services/progression.py`:

```python
def is_module_locked(
    course: Course,
    module: Module,
    user_statuses: dict[int, str],   # task_id -> "success" | "fail" | "pending"
) -> bool:
    if course.config.get("progression", "free") != "linear":
        return False
    # найти все модули с order < module.order
    for prev in course.modules:
        if prev.order >= module.order:
            continue
        for mu in prev.units:
            if mu.is_required and user_statuses.get(mu.task_id) != "success":
                return True
    return False
```

Первый модуль всегда разблокирован. Non-required юниты не влияют на unlock.

### 3.5 Просмотр теории как submission

Теория не имеет submit-flow. Чтобы теория засчитывалась в linear-прогрессии, вводится псевдо-submission:

- Фронт на `ChallengeDetailsPage` для юнитов с `task_type = "theory"` вызывает `POST /api/progress/viewed {task_id}` при первом открытии (one-shot, state-флаг)
- Backend создаёт `TaskSubmission` со `status = success` и `details = {"source": "theory_viewed"}`
- Идемпотентность: если у пользователя уже есть success-submission по этой задаче — новая не создаётся

---

## 4. YAML-формат курсов

### 4.1 Новое расположение

`tasks/tracks/` → `tasks/courses/` (после миграции). Новый формат:

```yaml
title: "Static Analysis & Secrets Detection"
slug: "sast-secrets"
description: "От ручного поиска секретов до production DevSecOps pipeline."
order: 4
config:
  icon: "search"
  progression: "linear"    # linear | free (default: free)

modules:
  - title: "Foundations"
    order: 1
    estimated_hours: 2
    learning_outcomes:
      - "Понимать разницу между SAST, DAST и secrets scanning"
      - "Находить секреты в git-истории и слоях Docker-образа"
    config:
      icon: "foundation"
    units:
      - task_slug: "sast-foundations-theory"
        order: 1
        required: true                   # default true
      - task_slug: "sast-lab-git-history-secrets"
        order: 2
      - task_slug: "sast-lab-docker-layer-secrets"
        order: 3

  - title: "Secrets Detection — Основы"
    order: 2
    estimated_hours: 3
    learning_outcomes:
      - "..."
    units:
      - task_slug: "sast-secrets-scanners-theory"
        order: 1
      # ...
```

### 4.2 Ключевые отличия от старого формата

| Старое | Новое |
|---|---|
| `steps: [...]` | `modules: [{units: [...]}, ...]` |
| `task_title: "..."` | `task_slug: "..."` (стабильный id) |
| Модули — только комментарии | Модули — явные YAML-объекты |
| Нет `progression` | `config.progression: linear\|free` |
| Нет `estimated_hours` / `learning_outcomes` | Есть на уровне модуля |

### 4.3 Обработка коротких курсов

Короткие курсы (SQLi, XSS) после миграции получают один модуль `title: "Основы"` без `description`/`learning_outcomes`. Frontend распознаёт такой случай и рендерит плоский список юнитов без аккордеона.

---

## 5. Backend API

### 5.1 Новые эндпоинты

```
GET  /api/courses                          → list[CourseOut]
     # список с агрегированным прогрессом

GET  /api/courses/{slug_or_id}             → CourseDetail
     # курс + вложенные модули + юниты + is_locked + user_status

GET  /api/modules/{id}                     → ModuleOut
     # отдельный эндпоинт для страницы модуля (если понадобится);
     # возвращает тот же DTO, что вложен в CourseDetail.modules

POST /api/progress/viewed                  → {ok: true}
     body: { task_id: int }
     # фиксация просмотра теории; идемпотентно
```

### 5.2 DTO (Pydantic)

```python
class CourseOut(BaseModel):
    id: int
    slug: str
    title: str
    description: str
    order: int
    config: dict
    module_count: int
    unit_count: int                  # required-юниты
    completed_unit_count: int
    progress_pct: int                # 0..100

class CourseDetail(CourseOut):
    modules: list[ModuleOut]

class ModuleOut(BaseModel):
    id: int
    title: str
    description: str
    order: int
    estimated_hours: int | None
    learning_outcomes: list[str]
    config: dict
    is_locked: bool
    unit_count: int                  # число required-юнитов в модуле
    completed_unit_count: int        # число required-юнитов со статусом success
    units: list[UnitOut]             # содержит все юниты, включая is_required=false

class UnitOut(BaseModel):
    id: int                          # = ModuleUnit.id
    task_id: int
    task_slug: str
    task_title: str
    task_type: str                   # quiz | ctf | gitlab | theory | ssh_lab
    task_difficulty: str | None
    content_kind: str | None         # для theory: text | video | mixed
    unit_order: int
    is_required: bool
    user_status: str | None          # success | fail | pending | null
```

### 5.3 Защита от обхода gating

Общий FastAPI-dependency `require_unit_unlocked(task_id)`:
- Загружает `ModuleUnit` → `Module` → `Course`
- Вычисляет `is_module_locked(course, module, user_statuses)`
- Если locked — `HTTPException(403, detail="module_locked")`

Подключается к `/api/quiz/{task_id}/submit`, `/api/ctf/{task_id}/start`, `/api/gitlab/{task_id}/verify`, `/api/ssh-lab/*/submit`.

### 5.4 Обратная совместимость

- `GET /api/tracks` → HTTP 308 redirect `/api/courses`
- `GET /api/tracks/{id}` → HTTP 308 redirect `/api/courses/{id}`
- Удаляются в следующем релизе после того, как фронт полностью переедет.

---

## 6. Frontend

### 6.1 Маршруты

- `/tracks` → redirect `/courses`
- `/tracks/:id` → redirect `/courses/:slug` (по `slug`, резолвится из списка курсов)
- `/courses` — новая `CoursesPage` (ex-`TracksPage`)
- `/courses/:slug` — новая `CourseDetailPage` (ex-`TrackDetailPage`, серьёзно переделана)
- `/challenges/:task_id` — существующая страница детали задачи (минимальные правки для video-theory и `POST /api/progress/viewed`)
- `/catalog` — существующий плоский каталог, остаётся без изменений

### 6.2 Новые / изменённые компоненты

| Компонент | Статус | Назначение |
|---|---|---|
| `CoursesPage` | переименование + правки | Каталог курсов: карточки с прогресс-баром, иконкой, бейджем linear/free |
| `CourseDetailPage` | серьёзная переделка | Хедер курса + аккордеон модулей |
| `ModuleAccordion` | новый | Разворачивание/сворачивание модулей, lock-индикация, состояние первого незавершённого |
| `UnitRow` | вынос из `TrackDetailPage.tsx:20` | Строка юнита (переиспользуется внутри модуля) |
| `LearningOutcomesList` | новый | Bullet-список outcomes модуля |
| `ModuleMetaBar` | новый | `⏱ N часов · 🎯 M outcomes` |
| `CourseCard` | переименование + добавление module_count | Карточка в `/courses` |
| `ChallengeDetailsPage` для theory | правки | Поддержка video/mixed content_kind; `POST /api/progress/viewed` one-shot |

### 6.3 UX-детали `CourseDetailPage`

- **Аккордеон:** первый модуль, где есть незавершённые юниты, раскрыт по умолчанию; остальные свёрнуты
- **Залоченные модули (linear):** серые, не раскрываются, подсказка на hover: «Завершите модуль N, чтобы разблокировать»
- **Прогресс-бар курса:** в хедере, считается как `sum(completed_unit_count) / sum(unit_count)` по всем модулям
- **Суммарное время:** `⏱ ~N часов` — сумма `estimated_hours` по модулям (если хотя бы у половины модулей оно задано; иначе скрыто)
- **Короткий курс (1 модуль без описания):** рендерится плоским списком юнитов без аккордеона

### 6.4 API-клиент и типы

- `src/api.ts`: добавить `getCourses()`, `getCourse(slug)`, `markViewed(taskId)`. Удалить `getTracks`/`getTrack`
- `src/types.ts`: `Track*` → `Course*`, `TrackStepItem` → `UnitItem`, новые `ModuleItem`, `CourseDetail`

---

## 7. Миграция

### 7.1 Подключение Alembic

Сейчас `main.py` использует `Base.metadata.create_all()` в lifespan. Переименование таблиц через `create_all` не работает, поэтому подключаем Alembic:

1. `alembic init backend/alembic` (async-шаблон)
2. `alembic.ini` / `env.py` берут `DATABASE_URL` из `config.settings`
3. Baseline-миграция `0001_initial.py` — авто-генерация из текущих моделей (`alembic revision --autogenerate`)
4. На существующих инстансах: `alembic stamp 0001` (помечаем текущее состояние как baseline)
5. Lifespan в `main.py`: заменяем `create_all()` на программный вызов Alembic API в том же процессе (`alembic.config.Config` + `alembic.command.upgrade(cfg, "head")`), чтобы избежать spawn отдельного subprocess'а и сохранить единый лог-канал

### 7.2 Миграция `0002_courses_modules.py`

Одна транзакция:

1. `CREATE TABLE courses` (клон структуры `tracks`)
2. `INSERT INTO courses (...) SELECT ... FROM tracks` — переносим 4 существующих трека; `config` получает `progression: "free"` если не задан
3. `CREATE TABLE modules` (пустая)
4. `CREATE TABLE module_units` (пустая)
5. `ALTER TABLE tasks ADD COLUMN slug VARCHAR(150)` + `CREATE UNIQUE INDEX`
6. `UPDATE tasks SET slug = <slugify(title)>` inline (SQL-функция или Python в миграции)
7. Для каждого курса создать один модуль «Основы» (`order=1`), перенести `track_steps` → `module_units` с сохранением `step_order` как `unit_order`, `is_required=true`
8. `DROP TABLE track_steps`
9. `DROP TABLE tracks`

### 7.3 Скрипт `scripts/migrate-tracks-to-courses.py`

Генерирует новые YAML из старых:

- Читает `tasks/tracks/*.yaml`
- Парсит комментарии `# ── Модуль N: <Название> ──` в исходнике как границы модулей (регекс `r'#\s*[─—\-]+\s*Модуль\s+\d+:\s*(.+?)\s*[─—\-]+'` — покрывает `─`, `—`, `-`)
- Если разделителей нет — один модуль `title: "Основы"`, `description` = description курса
- Для каждого шага: `task_title` → lookup в БД → берёт/генерирует `slug` → кладёт в `units[].task_slug`
- Генерирует placeholder-поля: `estimated_hours: null`, `learning_outcomes: []`
- Пишет `tasks/courses/<slug>.yaml`
- Идемпотентен: перезапуск перезаписывает файлы

### 7.4 Обновление `seed.py` / `deploy-labs.sh`

- `seed.py` читает `tasks/courses/*.yaml` вместо `tasks/tracks/*.yaml`
- Апсерт: `Course` по `slug`, `Module` по `(course_id, order)`, `ModuleUnit` — **пересобирается полностью** (удаляются существующие, вставляются новые) для идемпотентности
- Юниты (Task) seed-ятся как раньше из `tasks/ctf/` и `tasks/quizzes/` — никаких изменений
- `deploy-labs.sh --seed` вызывает новый код без изменений в самом скрипте

### 7.5 Runbook деплоя

```bash
# 0. Бэкап БД
pg_dump lms > backup-$(date +%F).sql

# 1. Код с миграцией + Alembic
docker compose up --build -d backend

# 2. Применить Alembic-миграцию
docker compose exec backend alembic upgrade head

# 3. Сгенерить новые YAML
python scripts/migrate-tracks-to-courses.py

# 4. Обогатить модули из новых YAML
./scripts/deploy-labs.sh --seed

# 5. Ручная проверка
open http://lms.lab.local/courses
open http://lms.lab.local/courses/sast-secrets

# 6. Через 1 релиз после успешного прода:
#    - удалить /api/tracks/* редиректы
#    - удалить tasks/tracks/
```

### 7.6 Откат

`alembic downgrade 0001`:
- Пересоздаёт `tracks` / `track_steps` из `courses` / `module_units`
- `Module.description` / `estimated_hours` / `learning_outcomes` теряются (в старой модели их нет) — ожидаемо, потеря некритична
- YAML-файлы в `tasks/courses/` остаются, но перестают читаться seed-ом

---

## 8. Тестирование

### 8.1 Backend (pytest)

| Тест | Покрытие |
|---|---|
| `test_migration_0002.py` | Загрузить старую схему с тестовыми данными → `alembic upgrade head` → проверить courses/modules/module_units |
| `test_progression.py` | `is_module_locked()`: free → unlocked; linear + первый модуль → unlocked; linear + предыдущий модуль с unfinished required → locked; non-required игнорируется; unfinished fail-юнит → locked |
| `test_courses_api.py` | e2e: `GET /api/courses`, `GET /api/courses/{slug}`, проверка DTO, `is_locked` для разных пользователей |
| `test_progress_viewed.py` | `POST /api/progress/viewed` создаёт success-submission; повторный вызов идемпотентен |
| `test_unit_unlock_guard.py` | Залоченный модуль → `quiz/submit`, `ctf/start`, `gitlab/verify` возвращают 403 `module_locked` |
| `test_seed_courses.py` | Seed из тестового YAML создаёт Course/Module/ModuleUnit; повторный seed идемпотентен |

### 8.2 Frontend

В проекте сейчас нет тестовой инфраструктуры. Не раздуваем scope. Ручная проверка:

- Пройти 4 курса в `/courses`
- Открыть `/courses/sast-secrets` — проверить 8 модулей, аккордеон, lock-статусы (после того как создадим linear-курс)
- Открыть `/courses/sqli` — проверить «плоский» рендер короткого курса
- Открыть theory-юнит → проверить, что он через несколько секунд отмечен как «Выполнено»
- Открыть залоченный модуль — проверить, что разворот невозможен, tooltip показывается

### 8.3 Smoke

`scripts/smoke-course-flow.sh`:
- login → `/api/courses` (status 200, >= 4 курсов)
- `/api/courses/sast-secrets` (>= 8 модулей)
- `/api/courses/sqli` (1 модуль)

---

## 9. Риски и открытые вопросы

| Риск | Митигация |
|---|---|
| Alembic впервые подключается к проекту — легко сломать миграцию | Тестовый проход на локальной БД до прода; baseline-миграция из current state перед `0002` |
| `slugify(task.title)` может дать коллизии (разные задачи с похожими title) | При коллизии — добавляем суффикс `-2`, `-3`; лог при миграции |
| Парсинг комментариев-разделителей в YAML хрупок (зависит от символов) | Регекс покрывает `─` / `-` / `—`, тест на всех 4 существующих YAML до прода |
| Студенты с in-flight сессиями при деплое увидят 404 на `/tracks/:id` | Redirect `/tracks/:id` → `/courses/:slug` на frontend и backend; сохраняется 1 релиз |

**Открытые вопросы (не блокирующие):**

- Нужен ли в будущем admin-UI для редактирования модулей/outcomes? — пока YAML, решим по фидбеку
- Нужна ли роль «инструктор» с правами на курс? — вне scope, решаем позже

---

## 10. Критерии приёмки

- [ ] Alembic-миграция успешно применяется на тестовой и staging-БД
- [ ] Все 4 существующих курса доступны по `/courses/{slug}` с правильной иерархией модулей (SAST — 8 модулей)
- [ ] SAST-курс работает в режиме `progression: linear`: попытка открыть модуль N+1 без завершения N — блокируется на UI и на API (403)
- [ ] SQLi/XSS — режим `free`, рендерятся плоским списком (один модуль без описания)
- [ ] Просмотр theory-юнита автоматически засчитывается как success (виден в `/my-results`)
- [ ] Прогресс-бар курса корректен: `completed_unit_count / unit_count` по всем required-юнитам
- [ ] Старые ссылки `/tracks/:id` и `/api/tracks/*` работают через redirect
- [ ] `./scripts/deploy-labs.sh --seed` идемпотентен: повторный запуск не создаёт дублей
- [ ] Все новые backend-тесты зелёные

---

## 11. Дальнейшие шаги

После ревью и одобрения этого spec'а — переход к **`writing-plans`**: пошаговый план реализации (Alembic-setup → миграция → модели → API → seed → frontend → тесты → миграция данных на staging → прод).
