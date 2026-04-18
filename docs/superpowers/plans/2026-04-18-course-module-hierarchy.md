# Course → Module → Unit Hierarchy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild LMS content representation from flat `Track → TrackStep → Task` into Coursera-like `Course → Module → Unit` with progression gating, video-theory support, and Alembic-managed migrations.

**Architecture:** Introduce a `Module` layer between Course (ex-Track) and Unit (= existing Task). Unit stays standalone, attached to modules via `module_units` (M:N). Add Alembic for DB migrations, `Task.slug` for stable YAML references, `is_module_locked` gating. Frontend gets a `CourseDetailPage` with a module accordion.

**Tech Stack:** FastAPI + SQLAlchemy async + Alembic 1.14 + PostgreSQL + React 18 + Vite + Tailwind.

**Spec:** [docs/superpowers/specs/2026-04-18-course-module-hierarchy-design.md](../specs/2026-04-18-course-module-hierarchy-design.md)

---

## File Structure

### Backend — new files

- `backend/alembic.ini` — Alembic config, reads `DATABASE_URL` from env
- `backend/alembic/env.py` — async Alembic env, imports `Base` from `models`
- `backend/alembic/script.py.mako` — default template (from `alembic init`)
- `backend/alembic/versions/0001_initial.py` — baseline migration reflecting current schema (users, tasks, task_submissions, tracks, track_steps, container_instances)
- `backend/alembic/versions/0002_task_slug.py` — add `tasks.slug` column + backfill
- `backend/alembic/versions/0003_courses_modules.py` — restructure tracks → courses/modules/module_units
- `backend/services/progression.py` — `is_module_locked(course, module, user_statuses) -> bool`
- `backend/services/unlock_guard.py` — FastAPI dependency `require_unit_unlocked(task_id)`
- `backend/routers/courses.py` — new GET `/api/courses`, GET `/api/courses/{slug_or_id}`, GET `/api/modules/{id}`
- `backend/tests/__init__.py`
- `backend/tests/conftest.py` — async test DB fixture
- `backend/tests/test_progression.py`
- `backend/tests/test_courses_api.py`
- `backend/tests/test_progress_viewed.py`
- `backend/tests/test_unlock_guard.py`
- `backend/tests/test_seed_courses.py`
- `scripts/migrate-tracks-to-courses.py` — one-shot: read `tasks/tracks/*.yaml`, emit `tasks/courses/*.yaml`
- `scripts/smoke-course-flow.sh` — login → `/api/courses` → `/api/courses/sast-secrets` sanity
- `tasks/courses/.gitkeep` — directory marker until YAML is generated

### Backend — modified files

- `backend/requirements.txt` — add `pytest`, `pytest-asyncio`, `httpx` (already present) for tests
- `backend/models.py` — remove `Track`/`TrackStep`, add `Course`/`Module`/`ModuleUnit`, add `Task.slug`
- `backend/schemas.py` — remove `TrackOut`/`TrackDetail`/`TrackStepOut`, add `CourseOut`/`CourseDetail`/`ModuleOut`/`UnitOut`
- `backend/main.py` — replace `create_all` lifespan block with `alembic.command.upgrade`; mount new `courses` router; drop `tracks` router import, add redirect router
- `backend/routers/tracks.py` — replace implementation with 308 redirects to `/api/courses/*`
- `backend/routers/__init__.py` — export new router
- `backend/routers/quiz.py` — add `Depends(require_unit_unlocked)`
- `backend/routers/ctf.py` — add `Depends(require_unit_unlocked)` on `/start`, `/flag`, `/check`
- `backend/routers/gitlab_tasks.py` — add `Depends(require_unit_unlocked)` on `/start`
- `backend/routers/progress.py` — add `POST /api/me/progress/viewed`
- `backend/seed.py` — read from `tasks/courses/*.yaml`, support slugs, upsert `Course/Module/ModuleUnit`

### Frontend — new files

- `frontend/src/pages/CoursesPage.tsx` — catalog of courses (replacement for `TracksPage.tsx`)
- `frontend/src/pages/CourseDetailPage.tsx` — Coursera-like view (replacement for `TrackDetailPage.tsx`)
- `frontend/src/components/ModuleAccordion.tsx`
- `frontend/src/components/UnitRow.tsx` — extracted from `TrackDetailPage.tsx:20` StepRow
- `frontend/src/components/CourseCard.tsx`
- `frontend/src/components/LearningOutcomesList.tsx`
- `frontend/src/components/ModuleMetaBar.tsx`

### Frontend — modified files

- `frontend/src/types.ts` — remove `TrackItem`/`TrackDetail`/`TrackStepItem`, add `CourseItem`/`CourseDetail`/`ModuleItem`/`UnitItem`
- `frontend/src/api.ts` — remove `listTracks`/`getTrack`, add `listCourses`/`getCourse(slug)`/`getModule(id)`/`markViewed(taskId)`
- `frontend/src/main.tsx` or `frontend/src/App.tsx` — update routes: `/tracks` → redirect `/courses`, `/tracks/:id` → redirect `/courses/:slug`; add new routes; delete old TracksPage/TrackDetailPage routes
- `frontend/src/pages/ChallengeDetailsPage.tsx` — for theory with `content_kind = video | mixed`: render video; call `api.markViewed(taskId)` once when theory unit opens

### Frontend — deleted files

- `frontend/src/pages/TracksPage.tsx`
- `frontend/src/pages/TrackDetailPage.tsx`

---

## Task 1: Wire up Alembic for async SQLAlchemy

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/.gitkeep`
- Modify: `backend/Dockerfile` (add working copy of `alembic/` into image)

- [ ] **Step 1: Verify alembic is installed**

Run: `cd backend && grep '^alembic' requirements.txt`
Expected: `alembic==1.14.0`

- [ ] **Step 2: Create `backend/alembic.ini`**

```ini
[alembic]
script_location = %(here)s/alembic
prepend_sys_path = .
timezone = UTC
version_path_separator = os

[post_write_hooks]

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

Note: we intentionally leave `sqlalchemy.url` out — it's set programmatically in `env.py` from `config.settings`.

- [ ] **Step 3: Create `backend/alembic/env.py`**

```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from config import settings
from models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 4: Create `backend/alembic/script.py.mako`**

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 5: Create empty `backend/alembic/versions/.gitkeep`**

Run: `touch backend/alembic/versions/.gitkeep`

- [ ] **Step 6: Update Dockerfile to include alembic dir**

Read current `backend/Dockerfile`. Confirm it uses `COPY . /app` — if so, alembic files will be picked up automatically. If the Dockerfile copies specific files, add explicit `COPY alembic /app/alembic` and `COPY alembic.ini /app/alembic.ini`.

Run: `grep -E '^COPY' backend/Dockerfile`

If output is `COPY . .` or similar, no change needed. Otherwise add lines near the other COPY statements:

```dockerfile
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini
```

- [ ] **Step 7: Verify alembic CLI works inside container**

Run: `docker compose up -d postgres && sleep 5 && docker compose run --rm backend alembic current`
Expected: output `INFO  [alembic.runtime.migration] ...` with no revision (empty `alembic_version` table auto-created on first call).

- [ ] **Step 8: Commit**

```bash
git add backend/alembic.ini backend/alembic/ backend/Dockerfile
git commit -m "build: wire up alembic with async env for migrations"
```

---

## Task 2: Baseline migration 0001_initial reflecting current schema

**Files:**
- Create: `backend/alembic/versions/0001_initial.py`

**Context:** The current DB already has `users`, `tasks`, `task_submissions`, `tracks`, `track_steps`, `container_instances` created via `Base.metadata.create_all`. We need a baseline migration that represents this state so Alembic can track subsequent changes. Existing instances get `alembic stamp 0001` to mark their state.

- [ ] **Step 1: Generate draft via autogenerate against an empty DB**

Run:
```bash
docker compose down -v && docker compose up -d postgres && sleep 5
docker compose run --rm backend alembic revision --autogenerate -m "initial" --rev-id 0001
```

Expected: file `backend/alembic/versions/0001_initial.py` containing `op.create_table(...)` for all 6 existing tables and enums (`userrole`, `tasktype`, `submissionstatus`, `containerstatus`).

- [ ] **Step 2: Review and clean up the generated file**

Open `backend/alembic/versions/0001_initial.py`. Verify it contains:
- All 4 enums: `userrole`, `tasktype`, `submissionstatus`, `containerstatus`
- All 6 tables with correct columns and FKs
- Indexes on `users.username`

Remove any `op.execute(...)` stubs that autogenerate might add for JSONB defaults. Ensure `downgrade()` drops tables in reverse dependency order (containers → submissions → track_steps → tracks → tasks → users; then enums).

- [ ] **Step 3: Add theory/ssh_lab enum values to upgrade() explicitly**

Since existing prod DB has the `theory` and `ssh_lab` values added via `ALTER TYPE ... ADD VALUE` in the current lifespan, make sure the baseline enum matches. In the generated migration, the `tasktype` enum should already include all 5 values (`quiz`, `ctf`, `gitlab`, `theory`, `ssh_lab`) because `Base.metadata` includes them. Verify:

```python
sa.Enum('quiz', 'ctf', 'gitlab', 'theory', 'ssh_lab', name='tasktype')
```

- [ ] **Step 4: Apply on empty DB to verify**

Run:
```bash
docker compose down -v && docker compose up -d postgres && sleep 5
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend alembic current
```

Expected: `0001 (head)` printed.

- [ ] **Step 5: Verify tables exist**

Run:
```bash
docker compose exec postgres psql -U lms -d lms -c '\dt'
```

Expected: 7 rows including `alembic_version`, `container_instances`, `task_submissions`, `tasks`, `track_steps`, `tracks`, `users`.

- [ ] **Step 6: Commit**

```bash
git add backend/alembic/versions/0001_initial.py
git commit -m "migration: baseline 0001_initial reflecting current schema"
```

---

## Task 3: Replace `create_all()` lifespan block with programmatic Alembic upgrade

**Files:**
- Modify: `backend/main.py:40-49` (lifespan function)

- [ ] **Step 1: Read current lifespan**

Current code (see `backend/main.py:40-49`):
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with engine.begin() as conn:
        await conn.execute(text("ALTER TYPE tasktype ADD VALUE IF NOT EXISTS 'theory'"))
    async with engine.begin() as conn:
        await conn.execute(text("ALTER TYPE tasktype ADD VALUE IF NOT EXISTS 'ssh_lab'"))
    await create_default_admin()
    ...
```

- [ ] **Step 2: Replace with alembic programmatic invocation**

In `backend/main.py`, replace the lifespan schema section with:

```python
import os
from alembic.config import Config as AlembicConfig
from alembic import command as alembic_command

def _run_migrations() -> None:
    ini_path = os.path.join(os.path.dirname(__file__), "alembic.ini")
    cfg = AlembicConfig(ini_path)
    cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "alembic"))
    alembic_command.upgrade(cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Apply DB migrations synchronously on startup
    await asyncio.to_thread(_run_migrations)
    await create_default_admin()

    # GitLab client + scheduler (unchanged)
    gitlab_url = os.getenv("GITLAB_URL")
    gitlab_token = os.getenv("GITLAB_ADMIN_TOKEN")
    if gitlab_url and gitlab_token:
        init_gitlab_client(gitlab_url, gitlab_token)
        logger.info(f"GitLab client initialized: {gitlab_url}")

    scheduler.add_job(cleanup_expired_containers, "interval", minutes=1)
    scheduler.start()
    logger.info("Scheduler started")

    yield
    scheduler.shutdown()
```

Also add `import asyncio` at the top if not already present.

Delete the now-unused imports: `Base` (keep if used elsewhere; check), `text`. Run:
```
grep -n "Base\|text(" backend/main.py
```
If only referenced in the removed block, drop them from imports.

- [ ] **Step 3: Apply on empty DB, verify backend starts**

Run:
```bash
docker compose down -v && docker compose up -d --build postgres backend
sleep 10
docker compose logs backend | grep -E "Running upgrade|INFO"
```

Expected: log line like `INFO [alembic.runtime.migration] Running upgrade -> 0001`.

- [ ] **Step 4: Verify `/api/health` responds**

Run: `curl -s http://localhost/api/health`
Expected: `{"status":"ok"}`

- [ ] **Step 5: Commit**

```bash
git add backend/main.py
git commit -m "build: apply alembic migrations on startup instead of create_all"
```

---

## Task 4: Add `Task.slug` — migration 0002 + model

**Files:**
- Modify: `backend/models.py` (add `slug` column to `Task`)
- Create: `backend/alembic/versions/0002_task_slug.py`

- [ ] **Step 1: Add `slug` column to `Task` model**

Open `backend/models.py:61`. Add after `title`:

```python
class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    slug = Column(String(150), unique=True, nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    type = Column(Enum(TaskType), nullable=False)
    config = Column(JSONB, default=dict)
    order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    submissions = relationship("TaskSubmission", back_populates="task")
```

Note: nullable=True initially so backfill works; we'll make it NOT NULL later if needed (keeping nullable is fine — slug is optional for tasks not referenced from YAML).

- [ ] **Step 2: Create migration file `0002_task_slug.py`**

Content:

```python
"""add task.slug column with backfill

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-18 00:00:00.000000

"""
import re
import unicodedata
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels = None
depends_on = None


def _slugify(text: str) -> str:
    """Minimal slugify: lowercase, strip accents, replace non-alnum with hyphens."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text[:150] or "task"


def upgrade() -> None:
    op.add_column("tasks", sa.Column("slug", sa.String(length=150), nullable=True))
    op.create_index("ix_tasks_slug", "tasks", ["slug"], unique=True)

    # Backfill: generate slug from title, ensure uniqueness by appending numeric suffix
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, title FROM tasks ORDER BY id")).fetchall()
    used: set[str] = set()
    for row in rows:
        base = _slugify(row.title)
        slug = base
        i = 2
        while slug in used:
            slug = f"{base}-{i}"
            i += 1
        used.add(slug)
        conn.execute(
            sa.text("UPDATE tasks SET slug = :slug WHERE id = :id"),
            {"slug": slug, "id": row.id},
        )


def downgrade() -> None:
    op.drop_index("ix_tasks_slug", table_name="tasks")
    op.drop_column("tasks", "slug")
```

- [ ] **Step 3: Apply and verify**

Run:
```bash
docker compose exec backend alembic upgrade head
docker compose exec postgres psql -U lms -d lms -c "SELECT id, slug, title FROM tasks ORDER BY id LIMIT 5"
```

Expected: each task has a slug like `sql-injection-osnovy` / `xss-stored-krazha-cookie` (or similar slugified value); no nulls.

- [ ] **Step 4: Re-run migration (idempotency smoke)**

Run: `docker compose exec backend alembic upgrade head`
Expected: no errors, no-op.

- [ ] **Step 5: Test downgrade**

Run:
```bash
docker compose exec backend alembic downgrade -1
docker compose exec postgres psql -U lms -d lms -c "\d tasks"
```
Expected: no `slug` column. Then re-upgrade: `docker compose exec backend alembic upgrade head`.

- [ ] **Step 6: Commit**

```bash
git add backend/models.py backend/alembic/versions/0002_task_slug.py
git commit -m "migration: add tasks.slug with backfill from title"
```

---

## Task 5: Add `Course`/`Module`/`ModuleUnit` models + migration 0003

**Files:**
- Modify: `backend/models.py` (remove `Track`/`TrackStep`, add `Course`/`Module`/`ModuleUnit`)
- Create: `backend/alembic/versions/0003_courses_modules.py`
- Modify: `backend/main.py` (remove `tracks` from `from routers import` — will be re-added as redirect-only later)

- [ ] **Step 1: Add new models to `backend/models.py`**

Remove the existing `Track` and `TrackStep` classes (lines 89-113 in current file). Add new classes:

```python
class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    description = Column(Text, default="")
    order = Column(Integer, default=0)
    config = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    modules = relationship(
        "Module",
        back_populates="course",
        order_by="Module.order",
        cascade="all, delete-orphan",
    )


class Module(Base):
    __tablename__ = "modules"

    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    order = Column(Integer, default=0, nullable=False)
    estimated_hours = Column(Integer, nullable=True)
    learning_outcomes = Column(JSONB, default=list)
    config = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("course_id", "order", name="uq_modules_course_order"),)

    course = relationship("Course", back_populates="modules")
    units = relationship(
        "ModuleUnit",
        back_populates="module",
        order_by="ModuleUnit.unit_order",
        cascade="all, delete-orphan",
    )


class ModuleUnit(Base):
    __tablename__ = "module_units"

    id = Column(Integer, primary_key=True)
    module_id = Column(Integer, ForeignKey("modules.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    unit_order = Column(Integer, default=0, nullable=False)
    is_required = Column(Boolean, default=True, nullable=False)

    __table_args__ = (UniqueConstraint("module_id", "task_id", name="uq_module_units_module_task"),)

    module = relationship("Module", back_populates="units")
    task = relationship("Task")
```

Add imports at top of `models.py`:
```python
from sqlalchemy import Boolean, UniqueConstraint
```

- [ ] **Step 2: Create `backend/alembic/versions/0003_courses_modules.py`**

```python
"""restructure tracks into courses/modules/module_units

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create courses (clone of tracks)
    op.create_table(
        "courses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("order", sa.Integer(), server_default="0"),
        sa.Column("config", JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("slug", name="uq_courses_slug"),
    )

    # 2. Copy tracks → courses (default progression=free)
    op.execute("""
        INSERT INTO courses (id, title, slug, description, "order", config, created_at)
        SELECT
            id, title, slug, description, "order",
            CASE
                WHEN config ? 'progression' THEN config
                ELSE config || '{"progression": "free"}'::jsonb
            END,
            created_at
        FROM tracks
    """)
    # Reset sequence so new inserts don't collide
    op.execute("SELECT setval('courses_id_seq', COALESCE((SELECT MAX(id) FROM courses), 1))")

    # 3. Create modules
    op.create_table(
        "modules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("estimated_hours", sa.Integer(), nullable=True),
        sa.Column("learning_outcomes", JSONB(), server_default=sa.text("'[]'::jsonb")),
        sa.Column("config", JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("course_id", "order", name="uq_modules_course_order"),
    )
    op.create_index("ix_modules_course_id", "modules", ["course_id"])

    # 4. Create module_units
    op.create_table(
        "module_units",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("module_id", sa.Integer(), sa.ForeignKey("modules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("unit_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_required", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.UniqueConstraint("module_id", "task_id", name="uq_module_units_module_task"),
    )
    op.create_index("ix_module_units_module_id", "module_units", ["module_id"])

    # 5. Seed one "Основы" module per course and move track_steps in
    op.execute("""
        INSERT INTO modules (course_id, title, description, "order", estimated_hours, learning_outcomes, config)
        SELECT id, 'Основы', '', 1, NULL, '[]'::jsonb, '{}'::jsonb FROM courses
    """)

    op.execute("""
        INSERT INTO module_units (module_id, task_id, unit_order, is_required)
        SELECT m.id, ts.task_id, ts.step_order, TRUE
        FROM track_steps ts
        JOIN modules m ON m.course_id = ts.track_id AND m.title = 'Основы' AND m."order" = 1
    """)

    # 6. Drop old tables
    op.drop_table("track_steps")
    op.drop_table("tracks")


def downgrade() -> None:
    # Restore tracks/track_steps from courses/module_units
    op.create_table(
        "tracks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("order", sa.Integer(), server_default="0"),
        sa.Column("config", JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("slug", name="uq_tracks_slug"),
    )
    op.create_table(
        "track_steps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("track_id", sa.Integer(), sa.ForeignKey("tracks.id"), nullable=False),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("step_order", sa.Integer(), server_default="0"),
    )

    op.execute("""
        INSERT INTO tracks (id, title, slug, description, "order", config, created_at)
        SELECT id, title, slug, description, "order", config, created_at FROM courses
    """)
    op.execute("SELECT setval('tracks_id_seq', COALESCE((SELECT MAX(id) FROM tracks), 1))")

    op.execute("""
        INSERT INTO track_steps (track_id, task_id, step_order)
        SELECT m.course_id, mu.task_id, mu.unit_order
        FROM module_units mu
        JOIN modules m ON m.id = mu.module_id
    """)

    op.drop_index("ix_module_units_module_id", table_name="module_units")
    op.drop_table("module_units")
    op.drop_index("ix_modules_course_id", table_name="modules")
    op.drop_table("modules")
    op.drop_table("courses")
```

- [ ] **Step 3: Remove `tracks` router import from `main.py`**

In `backend/main.py`:
- Change `from routers import admin, auth_router, ctf, gitlab_tasks, progress, quiz, tasks, tracks` to drop `tracks`
- Remove `app.include_router(tracks.router)` line

(We'll re-add it as redirect-only in Task 13.)

- [ ] **Step 4: Apply migration on seeded DB**

Run:
```bash
docker compose down && docker compose up -d postgres backend
sleep 5
# Seed first so we have tracks to migrate
./scripts/deploy-labs.sh --seed
docker compose exec backend alembic current
```

Expected: `0002 (head)` at this point (migration 0003 not yet applied because we haven't upgraded).

Then:
```bash
docker compose exec backend alembic upgrade head
docker compose exec postgres psql -U lms -d lms -c "SELECT id, slug, title FROM courses ORDER BY id"
docker compose exec postgres psql -U lms -d lms -c "SELECT course_id, title, \"order\" FROM modules ORDER BY course_id, \"order\""
docker compose exec postgres psql -U lms -d lms -c "SELECT module_id, task_id, unit_order FROM module_units ORDER BY module_id, unit_order LIMIT 20"
```

Expected: 4 courses with correct slugs; 4 modules (one "Основы" per course); module_units rows matching old track_steps.

Verify `tracks` / `track_steps` tables no longer exist:
```bash
docker compose exec postgres psql -U lms -d lms -c "\dt" | grep -E "tracks|track_steps"
```
Expected: no output.

- [ ] **Step 5: Test downgrade round-trip**

```bash
docker compose exec backend alembic downgrade -1
docker compose exec postgres psql -U lms -d lms -c "SELECT COUNT(*) FROM tracks"
docker compose exec backend alembic upgrade head
```
Expected: first SELECT returns 4; after re-upgrade, courses populated again (from tracks).

- [ ] **Step 6: Commit**

```bash
git add backend/models.py backend/alembic/versions/0003_courses_modules.py backend/main.py
git commit -m "migration: restructure tracks into courses/modules/module_units"
```

---

## Task 6: Progression service `is_module_locked` + unit tests

**Files:**
- Create: `backend/services/progression.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_progression.py`
- Modify: `backend/requirements.txt` (add pytest, pytest-asyncio)

- [ ] **Step 1: Add test deps to `requirements.txt`**

Append:
```
pytest==8.3.4
pytest-asyncio==0.25.0
```

Rebuild image: `docker compose build backend`

- [ ] **Step 2: Create `backend/tests/__init__.py` (empty file)**

Run: `touch backend/tests/__init__.py`

- [ ] **Step 3: Create `backend/tests/conftest.py`**

```python
import pytest


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"
```

- [ ] **Step 4: Write failing test `backend/tests/test_progression.py`**

```python
from dataclasses import dataclass
from services.progression import is_module_locked


@dataclass
class FakeUnit:
    task_id: int
    is_required: bool = True


@dataclass
class FakeModule:
    order: int
    units: list[FakeUnit]


@dataclass
class FakeCourse:
    config: dict
    modules: list[FakeModule]


def test_free_course_never_locks():
    course = FakeCourse(
        config={"progression": "free"},
        modules=[
            FakeModule(order=1, units=[FakeUnit(1)]),
            FakeModule(order=2, units=[FakeUnit(2)]),
        ],
    )
    assert is_module_locked(course, course.modules[0], {}) is False
    assert is_module_locked(course, course.modules[1], {}) is False


def test_missing_progression_defaults_to_free():
    course = FakeCourse(
        config={},
        modules=[FakeModule(order=1, units=[]), FakeModule(order=2, units=[FakeUnit(9)])],
    )
    assert is_module_locked(course, course.modules[1], {}) is False


def test_linear_first_module_is_open():
    course = FakeCourse(
        config={"progression": "linear"},
        modules=[FakeModule(order=1, units=[FakeUnit(1)])],
    )
    assert is_module_locked(course, course.modules[0], {}) is False


def test_linear_locked_when_prev_required_unit_unfinished():
    course = FakeCourse(
        config={"progression": "linear"},
        modules=[
            FakeModule(order=1, units=[FakeUnit(1), FakeUnit(2)]),
            FakeModule(order=2, units=[FakeUnit(3)]),
        ],
    )
    # unit 1 success, unit 2 fail
    statuses = {1: "success", 2: "fail"}
    assert is_module_locked(course, course.modules[1], statuses) is True


def test_linear_unlocked_when_all_prev_required_success():
    course = FakeCourse(
        config={"progression": "linear"},
        modules=[
            FakeModule(order=1, units=[FakeUnit(1), FakeUnit(2)]),
            FakeModule(order=2, units=[FakeUnit(3)]),
        ],
    )
    statuses = {1: "success", 2: "success"}
    assert is_module_locked(course, course.modules[1], statuses) is False


def test_linear_non_required_ignored():
    course = FakeCourse(
        config={"progression": "linear"},
        modules=[
            FakeModule(order=1, units=[FakeUnit(1, is_required=True), FakeUnit(2, is_required=False)]),
            FakeModule(order=2, units=[FakeUnit(3)]),
        ],
    )
    statuses = {1: "success"}  # unit 2 (non-required) not touched
    assert is_module_locked(course, course.modules[1], statuses) is False


def test_linear_pending_counts_as_locked():
    course = FakeCourse(
        config={"progression": "linear"},
        modules=[
            FakeModule(order=1, units=[FakeUnit(1)]),
            FakeModule(order=2, units=[FakeUnit(2)]),
        ],
    )
    statuses = {1: "pending"}
    assert is_module_locked(course, course.modules[1], statuses) is True
```

- [ ] **Step 5: Run test, expect failure**

Run: `docker compose run --rm backend pytest tests/test_progression.py -v`
Expected: `ImportError: No module named 'services.progression'`.

- [ ] **Step 6: Implement `backend/services/progression.py`**

```python
"""Progression gating logic for Course → Module → Unit hierarchy."""
from typing import Any


def is_module_locked(course: Any, module: Any, user_statuses: dict[int, str]) -> bool:
    """Return True if `module` is locked for a user with the given submission statuses.

    `course` and `module` are ORM-like objects with the attributes accessed below.
    `user_statuses` maps task_id → best submission status ("success"|"fail"|"pending").
    """
    progression = (course.config or {}).get("progression", "free")
    if progression != "linear":
        return False

    for prev in course.modules:
        if prev.order >= module.order:
            continue
        for unit in prev.units:
            if not unit.is_required:
                continue
            if user_statuses.get(unit.task_id) != "success":
                return True
    return False
```

- [ ] **Step 7: Run tests, expect pass**

Run: `docker compose run --rm backend pytest tests/test_progression.py -v`
Expected: 7 passed.

- [ ] **Step 8: Commit**

```bash
git add backend/requirements.txt backend/services/progression.py backend/tests/
git commit -m "feat(progression): add is_module_locked gating with tests"
```

---

## Task 7: Pydantic schemas for Course/Module/Unit DTOs

**Files:**
- Modify: `backend/schemas.py` (remove `TrackOut`/`TrackDetail`/`TrackStepOut`; add `UnitOut`/`ModuleOut`/`CourseOut`/`CourseDetail`)

- [ ] **Step 1: Delete old Track schemas**

Remove lines defining `TrackStepOut`, `TrackOut`, `TrackDetail` (currently in `backend/schemas.py:129-155`).

- [ ] **Step 2: Add new schemas at the bottom of `schemas.py`**

```python
# --- Course / Module / Unit ---
class UnitOut(BaseModel):
    id: int                           # = ModuleUnit.id
    task_id: int
    task_slug: str
    task_title: str
    task_type: TaskType
    task_difficulty: str | None = None
    content_kind: str | None = None   # text | video | mixed (for theory)
    unit_order: int
    is_required: bool
    user_status: str | None = None    # success | fail | pending | None

    class Config:
        from_attributes = True


class ModuleOut(BaseModel):
    id: int
    title: str
    description: str
    order: int
    estimated_hours: int | None
    learning_outcomes: list[str]
    config: dict
    is_locked: bool
    unit_count: int                   # required-only
    completed_unit_count: int         # required-only
    units: list[UnitOut]

    class Config:
        from_attributes = True


class CourseOut(BaseModel):
    id: int
    slug: str
    title: str
    description: str
    order: int
    config: dict
    module_count: int
    unit_count: int                   # required-only
    completed_unit_count: int         # required-only
    progress_pct: int                 # 0..100


class CourseDetail(CourseOut):
    modules: list[ModuleOut]
```

- [ ] **Step 3: Verify imports still work**

Run: `docker compose run --rm backend python -c "from schemas import CourseOut, CourseDetail, ModuleOut, UnitOut; print('ok')"`
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add backend/schemas.py
git commit -m "feat(schemas): add Course/Module/Unit DTOs, drop Track DTOs"
```

---

## Task 8: `/api/courses` router with list + detail

**Files:**
- Create: `backend/routers/courses.py`
- Modify: `backend/routers/__init__.py` (export `courses`)
- Modify: `backend/main.py` (include courses router)

- [ ] **Step 1: Create `backend/routers/courses.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from auth import get_current_user
from database import get_db
from models import Course, Module, ModuleUnit, TaskSubmission, TaskType, User
from schemas import CourseDetail, CourseOut, ModuleOut, UnitOut
from services.progression import is_module_locked

router = APIRouter(prefix="/api/courses", tags=["courses"], dependencies=[Depends(get_current_user)])

modules_router = APIRouter(prefix="/api/modules", tags=["modules"], dependencies=[Depends(get_current_user)])


async def _user_statuses(user_id: int, db: AsyncSession) -> dict[int, str]:
    """Return best submission status per task_id for a user ('success' wins)."""
    result = await db.execute(
        select(TaskSubmission.task_id, TaskSubmission.status)
        .where(TaskSubmission.user_id == user_id)
        .order_by(TaskSubmission.submitted_at.desc())
    )
    statuses: dict[int, str] = {}
    for task_id, status in result.all():
        val = status.value if hasattr(status, "value") else status
        if task_id not in statuses or val == "success":
            statuses[task_id] = val
    return statuses


def _course_agg(course: Course, statuses: dict[int, str]) -> tuple[int, int, int]:
    """Return (module_count, unit_count_required, completed_unit_count_required)."""
    module_count = len(course.modules)
    unit_count = 0
    completed = 0
    for m in course.modules:
        for u in m.units:
            if u.is_required:
                unit_count += 1
                if statuses.get(u.task_id) == "success":
                    completed += 1
    return module_count, unit_count, completed


def _build_unit_out(mu: ModuleUnit, statuses: dict[int, str]) -> UnitOut:
    cfg = mu.task.config or {}
    content_kind = None
    if mu.task.type == TaskType.theory:
        content_kind = cfg.get("content_kind", "text")
    return UnitOut(
        id=mu.id,
        task_id=mu.task_id,
        task_slug=mu.task.slug or "",
        task_title=mu.task.title,
        task_type=mu.task.type,
        task_difficulty=cfg.get("difficulty"),
        content_kind=content_kind,
        unit_order=mu.unit_order,
        is_required=mu.is_required,
        user_status=statuses.get(mu.task_id),
    )


def _build_module_out(course: Course, module: Module, statuses: dict[int, str]) -> ModuleOut:
    units = [_build_unit_out(mu, statuses) for mu in module.units]
    required = [u for u in units if u.is_required]
    completed = sum(1 for u in required if u.user_status == "success")
    return ModuleOut(
        id=module.id,
        title=module.title,
        description=module.description or "",
        order=module.order,
        estimated_hours=module.estimated_hours,
        learning_outcomes=module.learning_outcomes or [],
        config=module.config or {},
        is_locked=is_module_locked(course, module, statuses),
        unit_count=len(required),
        completed_unit_count=completed,
        units=units,
    )


def _load_course_query():
    return (
        select(Course)
        .options(
            selectinload(Course.modules)
            .selectinload(Module.units)
            .selectinload(ModuleUnit.task)
        )
        .order_by(Course.order, Course.id)
    )


@router.get("", response_model=list[CourseOut])
async def list_courses(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(_load_course_query())
    courses = result.scalars().unique().all()
    statuses = await _user_statuses(user.id, db)
    out: list[CourseOut] = []
    for c in courses:
        module_count, unit_count, completed = _course_agg(c, statuses)
        pct = round(completed / unit_count * 100) if unit_count else 0
        out.append(CourseOut(
            id=c.id,
            slug=c.slug,
            title=c.title,
            description=c.description or "",
            order=c.order,
            config=c.config or {},
            module_count=module_count,
            unit_count=unit_count,
            completed_unit_count=completed,
            progress_pct=pct,
        ))
    return out


@router.get("/{slug_or_id}", response_model=CourseDetail)
async def get_course(
    slug_or_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = _load_course_query()
    if slug_or_id.isdigit():
        q = q.where(Course.id == int(slug_or_id))
    else:
        q = q.where(Course.slug == slug_or_id)
    result = await db.execute(q)
    course = result.scalars().unique().one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    statuses = await _user_statuses(user.id, db)
    module_count, unit_count, completed = _course_agg(course, statuses)
    pct = round(completed / unit_count * 100) if unit_count else 0

    return CourseDetail(
        id=course.id,
        slug=course.slug,
        title=course.title,
        description=course.description or "",
        order=course.order,
        config=course.config or {},
        module_count=module_count,
        unit_count=unit_count,
        completed_unit_count=completed,
        progress_pct=pct,
        modules=[_build_module_out(course, m, statuses) for m in course.modules],
    )


@modules_router.get("/{module_id}", response_model=ModuleOut)
async def get_module(
    module_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Module)
        .options(selectinload(Module.units).selectinload(ModuleUnit.task))
        .where(Module.id == module_id)
    )
    module = result.scalar_one_or_none()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    # load parent course for progression check
    course_result = await db.execute(
        _load_course_query().where(Course.id == module.course_id)
    )
    course = course_result.scalars().unique().one()

    statuses = await _user_statuses(user.id, db)
    return _build_module_out(course, module, statuses)
```

- [ ] **Step 2: Update `backend/routers/__init__.py`**

Add export:
```python
from . import courses  # noqa
```

(Or if `__init__.py` doesn't aggregate, skip and import in main.py directly.)

- [ ] **Step 3: Wire into `main.py`**

In `backend/main.py`, add:

```python
from routers import admin, auth_router, courses, ctf, gitlab_tasks, progress, quiz, tasks
```

And after existing `app.include_router(...)` lines:

```python
app.include_router(courses.router)
app.include_router(courses.modules_router)
```

- [ ] **Step 4: Start backend, smoke-test**

Run:
```bash
docker compose up -d --build backend
sleep 5
TOKEN=$(curl -s -X POST http://localhost/api/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin"}' | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
curl -s -H "Authorization: Bearer $TOKEN" http://localhost/api/courses | python3 -m json.tool
```

Expected: JSON array of 4 courses, each with `module_count: 1`, non-zero `unit_count`, and a `progress_pct`.

Also test:
```bash
curl -s -H "Authorization: Bearer $TOKEN" http://localhost/api/courses/sast-secrets-track | python3 -m json.tool
```
Expected: course detail with 1 module containing all units.

- [ ] **Step 5: Commit**

```bash
git add backend/routers/courses.py backend/routers/__init__.py backend/main.py
git commit -m "feat(api): add /api/courses and /api/modules endpoints"
```

---

## Task 9: Unlock guard dependency + apply to quiz/ctf/gitlab routers

**Files:**
- Create: `backend/services/unlock_guard.py`
- Create: `backend/tests/test_unlock_guard.py`
- Modify: `backend/routers/quiz.py` (add dependency to `/submit`)
- Modify: `backend/routers/ctf.py` (add dependency to `/start`, `/flag`, `/check`)
- Modify: `backend/routers/gitlab_tasks.py` (add dependency to `/start`)

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_unlock_guard.py`:

```python
"""Integration test: guard returns 403 when user tries locked unit."""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.skip(reason="requires full app + DB fixture — placeholder for smoke; real coverage via e2e")
def test_quiz_submit_blocked_when_module_locked():
    # This test is a placeholder. Real coverage is done via the smoke script
    # and test_courses_api.py integration test in a later task, since wiring
    # a full DB fixture here duplicates the integration-test setup.
    pass
```

(We explicitly skip this because integration testing with DB setup is handled in Task 14's test_courses_api.py. The unit coverage for `is_module_locked` logic lives in Task 6.)

- [ ] **Step 2: Create `backend/services/unlock_guard.py`**

```python
"""FastAPI dependency that blocks access to locked units."""
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from auth import get_current_user
from database import get_db
from models import Course, Module, ModuleUnit, TaskSubmission, User
from services.progression import is_module_locked


async def _user_statuses(user_id: int, db: AsyncSession) -> dict[int, str]:
    result = await db.execute(
        select(TaskSubmission.task_id, TaskSubmission.status)
        .where(TaskSubmission.user_id == user_id)
        .order_by(TaskSubmission.submitted_at.desc())
    )
    statuses: dict[int, str] = {}
    for task_id, status in result.all():
        val = status.value if hasattr(status, "value") else status
        if task_id not in statuses or val == "success":
            statuses[task_id] = val
    return statuses


async def require_unit_unlocked(
    task_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Verify that a unit referencing this task is unlocked for the user.

    If the task is not linked to any module (standalone catalog task) — allow.
    If linked and the module is locked by progression rules — raise 403.
    Admins bypass the check.
    """
    if user.role.value == "admin":
        return

    # Find any ModuleUnit referencing this task + load parent module & course
    result = await db.execute(
        select(ModuleUnit)
        .options(
            selectinload(ModuleUnit.module)
            .selectinload(Module.course)
            .selectinload(Course.modules)
            .selectinload(Module.units)
        )
        .where(ModuleUnit.task_id == task_id)
    )
    mus = result.scalars().unique().all()
    if not mus:
        return  # standalone task, no gating

    statuses = await _user_statuses(user.id, db)
    # If ANY of the linking modules is unlocked, allow (unit is reachable via another path)
    for mu in mus:
        module = mu.module
        course = module.course
        if not is_module_locked(course, module, statuses):
            return

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="module_locked")
```

- [ ] **Step 3: Apply dependency to quiz router**

Edit `backend/routers/quiz.py:30`:

```python
from services.unlock_guard import require_unit_unlocked

@router.post("/{task_id}/submit", response_model=QuizResult, dependencies=[Depends(require_unit_unlocked)])
async def submit_quiz(
    task_id: int,
    body: QuizSubmit,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ...
```

- [ ] **Step 4: Apply to CTF router**

Edit `backend/routers/ctf.py`. Add import `from services.unlock_guard import require_unit_unlocked`.
Add `dependencies=[Depends(require_unit_unlocked)]` to the `@router.post` decorators on `/start`, `/flag`, `/check` (search for `@router.post` lines with path containing `/start`, `/flag`, `/check` and `{task_id}`).

- [ ] **Step 5: Apply to gitlab_tasks router**

Edit `backend/routers/gitlab_tasks.py`. Same pattern on `/start`.

- [ ] **Step 6: Smoke test**

Create a linear course in DB manually to test: pick `sast-secrets-track`, set `progression: linear`:

```bash
docker compose exec postgres psql -U lms -d lms -c "UPDATE courses SET config = config || '{\"progression\": \"linear\"}'::jsonb WHERE slug = 'sast-secrets-track'"
```

Then as a fresh student user, try submitting quiz for the second unit's task_id:

```bash
# Create a student
curl -s -X POST http://localhost/api/admin/users -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"username":"student1","password":"pass","full_name":"Student","role":"student"}'
STOKEN=$(curl -s -X POST http://localhost/api/auth/login -H 'Content-Type: application/json' -d '{"username":"student1","password":"pass"}' | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')

# Find a task_id in the second module; attempt submit (quiz, just to exercise)
# For now any quiz task works because module 1 has prerequisite tasks
# We'll use one from the SAST track (e.g. task with slug sast-lab-git-history-secrets once module split happens, or any task that's not first)
# For smoke: just hit /api/ctf/N/start with an arbitrary id that's behind the gate
curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $STOKEN" -X POST http://localhost/api/ctf/999/start
```

At this stage, since all existing courses have 1 module ("Основы"), no module is locked, so smoke may show 200/404. The real gating test happens after Task 11 when SAST gets split into 8 modules. Skip detailed smoke until then.

- [ ] **Step 7: Commit**

```bash
git add backend/services/unlock_guard.py backend/routers/quiz.py backend/routers/ctf.py backend/routers/gitlab_tasks.py backend/tests/test_unlock_guard.py
git commit -m "feat(api): block locked units via require_unit_unlocked dep"
```

---

## Task 10: `POST /api/me/progress/viewed` for theory auto-submission

**Files:**
- Modify: `backend/routers/progress.py` (add endpoint)
- Create: `backend/tests/test_progress_viewed.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_progress_viewed.py`:

```python
"""Test POST /api/me/progress/viewed creates an idempotent success submission for theory."""
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from database import async_session
from main import app
from models import SubmissionStatus, Task, TaskSubmission, TaskType, User, UserRole
from auth import hash_password, create_access_token

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _make_user_and_theory(db) -> tuple[int, int, str]:
    user = User(username=f"t_{pytest.__version__}", password_hash=hash_password("x"),
                full_name="t", role=UserRole.student)
    db.add(user)
    task = Task(slug=f"t-{pytest.__version__}-theory", title="T theory",
                description="", type=TaskType.theory, config={"content_kind": "text"})
    db.add(task)
    await db.flush()
    token = create_access_token({"sub": user.username})
    return user.id, task.id, token


async def test_progress_viewed_creates_success_submission():
    async with async_session() as db:
        user_id, task_id, token = await _make_user_and_theory(db)
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as ac:
        r = await ac.post("/api/me/progress/viewed",
                          headers={"Authorization": f"Bearer {token}"},
                          json={"task_id": task_id})
        assert r.status_code == 200
        assert r.json()["ok"] is True

    async with async_session() as db:
        subs = (await db.execute(
            select(TaskSubmission).where(TaskSubmission.user_id == user_id, TaskSubmission.task_id == task_id)
        )).scalars().all()
        assert len(subs) == 1
        assert subs[0].status == SubmissionStatus.success


async def test_progress_viewed_is_idempotent():
    async with async_session() as db:
        user_id, task_id, token = await _make_user_and_theory(db)
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as ac:
        headers = {"Authorization": f"Bearer {token}"}
        for _ in range(3):
            r = await ac.post("/api/me/progress/viewed", headers=headers, json={"task_id": task_id})
            assert r.status_code == 200

    async with async_session() as db:
        count = (await db.execute(
            select(TaskSubmission).where(TaskSubmission.user_id == user_id, TaskSubmission.task_id == task_id)
        )).scalars().all()
        assert len(count) == 1
```

- [ ] **Step 2: Run test, expect failure**

Run: `docker compose run --rm backend pytest tests/test_progress_viewed.py -v`
Expected: 404 / endpoint missing.

- [ ] **Step 3: Add endpoint to `backend/routers/progress.py`**

At the top, add imports if missing:
```python
from pydantic import BaseModel
from models import TaskType
```

Add new request schema just above the router instantiation (or inline):
```python
class ViewedRequest(BaseModel):
    task_id: int
```

Add endpoint inside existing router:

```python
@router.post("/progress/viewed")
async def mark_viewed(
    body: ViewedRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Idempotently record a theory view as a success submission."""
    task_result = await db.execute(select(Task).where(Task.id == body.task_id))
    task = task_result.scalar_one_or_none()
    if not task or task.type != TaskType.theory:
        raise HTTPException(status_code=404, detail="Theory task not found")

    existing = await db.execute(
        select(TaskSubmission).where(
            TaskSubmission.user_id == user.id,
            TaskSubmission.task_id == body.task_id,
            TaskSubmission.status == SubmissionStatus.success,
        )
    )
    if existing.scalar_one_or_none():
        return {"ok": True}

    db.add(TaskSubmission(
        user_id=user.id,
        task_id=body.task_id,
        status=SubmissionStatus.success,
        details={"source": "theory_viewed"},
    ))
    await db.commit()
    return {"ok": True}
```

Add `HTTPException` to imports: `from fastapi import APIRouter, Depends, HTTPException`.

- [ ] **Step 4: Run tests, expect pass**

Run: `docker compose run --rm backend pytest tests/test_progress_viewed.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/routers/progress.py backend/tests/test_progress_viewed.py
git commit -m "feat(api): add POST /api/me/progress/viewed for theory auto-submission"
```

---

## Task 11: Backward-compat redirects `/api/tracks/*` → `/api/courses/*`

**Files:**
- Modify: `backend/routers/tracks.py` (replace entire content with redirects)
- Modify: `backend/main.py` (re-add `tracks` import + include router)

- [ ] **Step 1: Replace `backend/routers/tracks.py` with a redirect-only router**

```python
"""Legacy /api/tracks/* endpoints — temporary 308 redirects to /api/courses/*.

Delete this file + its import after one release cycle.
"""
from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from auth import get_current_user
from database import get_db
from models import Course

router = APIRouter(prefix="/api/tracks", tags=["tracks-legacy"])


@router.get("", include_in_schema=False)
async def list_tracks_redirect():
    return RedirectResponse(url="/api/courses", status_code=308)


@router.get("/{track_id}", include_in_schema=False)
async def get_track_redirect(
    track_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    # Resolve the same id in courses (since ids were preserved in migration 0003)
    result = await db.execute(select(Course.slug).where(Course.id == track_id))
    slug = result.scalar_one_or_none()
    if not slug:
        return RedirectResponse(url="/api/courses", status_code=308)
    return RedirectResponse(url=f"/api/courses/{slug}", status_code=308)
```

- [ ] **Step 2: Re-add `tracks` to main.py**

In `backend/main.py`, restore:
```python
from routers import admin, auth_router, courses, ctf, gitlab_tasks, progress, quiz, tasks, tracks
...
app.include_router(tracks.router)
```

- [ ] **Step 3: Smoke**

```bash
docker compose up -d --build backend && sleep 5
TOKEN=$(curl -s -X POST http://localhost/api/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin"}' | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
curl -s -o /dev/null -w "%{http_code} -> %{redirect_url}\n" -H "Authorization: Bearer $TOKEN" http://localhost/api/tracks
curl -s -o /dev/null -w "%{http_code} -> %{redirect_url}\n" -H "Authorization: Bearer $TOKEN" http://localhost/api/tracks/1
```

Expected: both lines start with `308`; first redirects to `/api/courses`, second to `/api/courses/<slug>` (e.g. `/api/courses/xss-track`).

- [ ] **Step 4: Commit**

```bash
git add backend/routers/tracks.py backend/main.py
git commit -m "feat(api): temporary 308 redirects /api/tracks -> /api/courses"
```

---

## Task 12: Script `migrate-tracks-to-courses.py` — generate new YAML

**Files:**
- Create: `scripts/migrate-tracks-to-courses.py`
- Create: `tasks/courses/.gitkeep`

- [ ] **Step 1: Create directory marker**

```bash
mkdir -p tasks/courses
touch tasks/courses/.gitkeep
```

- [ ] **Step 2: Write the migration script**

Create `scripts/migrate-tracks-to-courses.py`:

```python
#!/usr/bin/env python3
"""One-shot: convert tasks/tracks/*.yaml into tasks/courses/*.yaml with explicit modules.

Logic:
  - Read each tasks/tracks/*.yaml
  - Scan the raw source for '# ── Модуль N: <title> ──' comment separators
    (accepts — and - as well). Each separator starts a new module.
  - If no separators found, wrap all steps in a single "Основы" module.
  - Each unit gets a task_slug (generated from task_title if Task.slug is unknown).
  - Placeholder estimated_hours (null) and empty learning_outcomes.
  - Writes tasks/courses/<slug>.yaml (overwrites). Script is idempotent.
"""
import glob
import os
import re
import sys
import unicodedata

import yaml

SEPARATOR_RE = re.compile(r"#\s*[─—\-]+\s*Модуль\s+\d+:\s*(.+?)\s*[─—\-]+\s*$")


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text[:150] or "task"


def parse_modules_from_source(source: str, steps: list[dict]) -> list[dict]:
    """Use the raw YAML text to detect '# ── Модуль N: <title> ──' separators
    and partition `steps` into modules accordingly.

    Each step in `steps` has a `task_title` and `order`. We walk the source
    line-by-line, tracking the current module; when we encounter a line that
    contains `task_title: "..."`, we assign that step to the current module.
    """
    # Build title -> step map (steps may repeat titles in theory; we index by order)
    if not steps:
        return []

    lines = source.splitlines()
    current_module_title: str | None = None
    modules: list[dict] = []
    current_module: dict | None = None
    step_idx = 0

    title_re = re.compile(r'^\s*-\s*task_title:\s*"([^"]+)"')

    for line in lines:
        sep = SEPARATOR_RE.search(line)
        if sep:
            current_module_title = sep.group(1).strip()
            current_module = {
                "title": current_module_title,
                "order": len(modules) + 1,
                "estimated_hours": None,
                "learning_outcomes": [],
                "units": [],
            }
            modules.append(current_module)
            continue

        m = title_re.search(line)
        if m and step_idx < len(steps):
            step = steps[step_idx]
            step_idx += 1
            if current_module is None:
                current_module = {
                    "title": "Основы",
                    "order": 1,
                    "estimated_hours": None,
                    "learning_outcomes": [],
                    "units": [],
                }
                modules.append(current_module)
            current_module["units"].append({
                "task_slug": slugify(step["task_title"]),
                "task_title": step["task_title"],  # kept only for debugging; stripped before write
                "order": len(current_module["units"]) + 1,
                "required": step.get("required", True),
            })

    if not modules:
        # No separators, no titles detected (empty steps list?) — still emit one module
        modules = [{
            "title": "Основы",
            "order": 1,
            "estimated_hours": None,
            "learning_outcomes": [],
            "units": [
                {
                    "task_slug": slugify(s["task_title"]),
                    "task_title": s["task_title"],
                    "order": s.get("order", i + 1),
                    "required": True,
                }
                for i, s in enumerate(steps)
            ],
        }]
    return modules


def strip_debug_fields(modules: list[dict]) -> list[dict]:
    for m in modules:
        for u in m["units"]:
            u.pop("task_title", None)
    return modules


def convert(src_path: str, dst_dir: str) -> str:
    with open(src_path) as f:
        source = f.read()
    data = yaml.safe_load(source)

    modules = parse_modules_from_source(source, data.get("steps", []))
    modules = strip_debug_fields(modules)

    out = {
        "title": data["title"],
        "slug": data["slug"],
        "description": data.get("description", ""),
        "order": data.get("order", 0),
        "config": data.get("config", {}),
        "modules": modules,
    }

    dst = os.path.join(dst_dir, f"{data['slug']}.yaml")
    with open(dst, "w") as f:
        yaml.safe_dump(out, f, allow_unicode=True, sort_keys=False)
    return dst


def main(argv: list[str]) -> int:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tracks_dir = os.path.join(repo_root, "tasks", "tracks")
    courses_dir = os.path.join(repo_root, "tasks", "courses")
    os.makedirs(courses_dir, exist_ok=True)

    files = sorted(glob.glob(os.path.join(tracks_dir, "*.yaml")))
    if not files:
        print(f"No track YAMLs in {tracks_dir}", file=sys.stderr)
        return 1

    for src in files:
        dst = convert(src, courses_dir)
        print(f"  {os.path.basename(src)} -> {os.path.basename(dst)}")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

- [ ] **Step 3: Run the script**

```bash
python3 scripts/migrate-tracks-to-courses.py
ls -1 tasks/courses/
```

Expected: `owasp-top10-track.yaml`, `sast-secrets-track.yaml`, `sqli-track.yaml`, `xss-track.yaml`.

- [ ] **Step 4: Inspect output for SAST (the important one)**

```bash
grep -E '^  - title:' tasks/courses/sast-secrets-track.yaml
```

Expected: 8 lines, one per module:
```
  - title: Foundations
  - title: Secrets Detection — Основы
  ...
```

(Exact titles depend on what's in the comments.)

- [ ] **Step 5: Inspect output for short course (SQLi)**

```bash
cat tasks/courses/sqli-track.yaml
```

Expected: one module `title: Основы` with 2 units.

- [ ] **Step 6: Commit**

```bash
git add scripts/migrate-tracks-to-courses.py tasks/courses/
git commit -m "feat(scripts): add migrate-tracks-to-courses.py and emit generated YAML"
```

---

## Task 13: Rewrite `backend/seed.py` to load courses/modules/units from `tasks/courses/*.yaml`

**Files:**
- Modify: `backend/seed.py`
- Create: `backend/tests/test_seed_courses.py`

- [ ] **Step 1: Rewrite `backend/seed.py`**

```python
"""Load tasks and courses from YAML files into the database."""
import asyncio
import glob
import os
import re
import sys
import unicodedata

import yaml
from sqlalchemy import delete, select

from database import async_session, engine
from models import Base, Course, Module, ModuleUnit, Task, TaskType


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text[:150] or "task"


async def seed_tasks(tasks_dir: str = "/tasks"):
    # Tables are managed by alembic in production, but in the seed CLI we still
    # ensure metadata is present (create_all is a no-op on already-migrated DB).
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    task_patterns = [
        os.path.join(tasks_dir, "quizzes", "*.yaml"),
        os.path.join(tasks_dir, "ctf", "*", "task.yaml"),
        os.path.join(tasks_dir, "theory", "*.yaml"),
    ]

    files: list[str] = []
    for pattern in task_patterns:
        files.extend(glob.glob(pattern))

    if files:
        async with async_session() as db:
            for filepath in sorted(files):
                with open(filepath) as f:
                    data = yaml.safe_load(f)

                title = data["title"]
                task_type = TaskType(data["type"])
                slug = data.get("slug") or slugify(title)
                config = data.get("config", {})

                # Upsert by title (existing behavior) + ensure slug is set.
                existing = (await db.execute(
                    select(Task).where(Task.title == title)
                )).scalar_one_or_none()

                if existing:
                    existing.description = data.get("description", "")
                    existing.type = task_type
                    existing.config = config
                    existing.order = data.get("order", 0)
                    if not existing.slug:
                        existing.slug = slug
                    print(f"  Updated: {title}")
                else:
                    db.add(Task(
                        title=title,
                        slug=slug,
                        description=data.get("description", ""),
                        type=task_type,
                        config=config,
                        order=data.get("order", 0),
                    ))
                    print(f"  Created: {title}")
            await db.commit()

    # Load courses
    course_files = glob.glob(os.path.join(tasks_dir, "courses", "*.yaml"))
    if course_files:
        async with async_session() as db:
            for filepath in sorted(course_files):
                with open(filepath) as f:
                    data = yaml.safe_load(f)

                slug = data["slug"]
                course = (await db.execute(
                    select(Course).where(Course.slug == slug)
                )).scalar_one_or_none()

                if course:
                    course.title = data["title"]
                    course.description = data.get("description", "")
                    course.order = data.get("order", 0)
                    course.config = data.get("config", {})
                    print(f"  Updated course: {data['title']}")
                else:
                    course = Course(
                        title=data["title"],
                        slug=slug,
                        description=data.get("description", ""),
                        order=data.get("order", 0),
                        config=data.get("config", {}),
                    )
                    db.add(course)
                    await db.flush()
                    print(f"  Created course: {data['title']}")

                # Rebuild modules from scratch (cascades to module_units)
                await db.execute(delete(Module).where(Module.course_id == course.id))
                await db.flush()

                for mod_data in data.get("modules", []):
                    module = Module(
                        course_id=course.id,
                        title=mod_data["title"],
                        description=mod_data.get("description", ""),
                        order=mod_data["order"],
                        estimated_hours=mod_data.get("estimated_hours"),
                        learning_outcomes=mod_data.get("learning_outcomes", []),
                        config=mod_data.get("config", {}),
                    )
                    db.add(module)
                    await db.flush()

                    for unit_data in mod_data.get("units", []):
                        task_slug = unit_data["task_slug"]
                        task = (await db.execute(
                            select(Task).where(Task.slug == task_slug)
                        )).scalar_one_or_none()
                        if not task:
                            print(f"    WARNING: task slug not found: {task_slug}")
                            continue
                        db.add(ModuleUnit(
                            module_id=module.id,
                            task_id=task.id,
                            unit_order=unit_data.get("order", 0),
                            is_required=unit_data.get("required", True),
                        ))
            await db.commit()

    print("Done!")


if __name__ == "__main__":
    tasks_dir = sys.argv[1] if len(sys.argv) > 1 else "/tasks"
    asyncio.run(seed_tasks(tasks_dir))
```

- [ ] **Step 2: Write a light test for seeding**

Create `backend/tests/test_seed_courses.py`:

```python
"""Smoke test: seed runs without error on the actual repo YAML and creates courses."""
import os
import pytest
from sqlalchemy import select

from database import async_session
from models import Course, Module, ModuleUnit
from seed import seed_tasks

pytestmark = pytest.mark.asyncio(loop_scope="session")

REPO_TASKS = os.path.join(os.path.dirname(__file__), "..", "..", "tasks")


async def test_seed_creates_courses():
    if not os.path.isdir(os.path.join(REPO_TASKS, "courses")):
        pytest.skip("tasks/courses not generated yet in this environment")
    await seed_tasks(REPO_TASKS)
    async with async_session() as db:
        courses = (await db.execute(select(Course))).scalars().all()
        assert len(courses) >= 4

        sast = next((c for c in courses if c.slug == "sast-secrets-track"), None)
        assert sast is not None

        modules = (await db.execute(
            select(Module).where(Module.course_id == sast.id).order_by(Module.order)
        )).scalars().all()
        assert len(modules) >= 1  # at least the "Основы" fallback; 8 after migrate script


async def test_seed_is_idempotent():
    if not os.path.isdir(os.path.join(REPO_TASKS, "courses")):
        pytest.skip("tasks/courses not generated yet in this environment")
    await seed_tasks(REPO_TASKS)
    await seed_tasks(REPO_TASKS)  # should not raise or duplicate
    async with async_session() as db:
        mus_a = (await db.execute(select(ModuleUnit))).scalars().all()
        await seed_tasks(REPO_TASKS)
        mus_b = (await db.execute(select(ModuleUnit))).scalars().all()
        assert len(mus_a) == len(mus_b)
```

- [ ] **Step 3: Run seeding end-to-end**

```bash
./scripts/deploy-labs.sh --seed
docker compose exec postgres psql -U lms -d lms -c "SELECT course_id, COUNT(*) FROM modules GROUP BY course_id ORDER BY course_id"
```

Expected: `sast-secrets-track` has ~8 modules; others have 1.

```bash
docker compose exec postgres psql -U lms -d lms -c "SELECT COUNT(*) FROM module_units WHERE module_id IN (SELECT id FROM modules WHERE course_id = (SELECT id FROM courses WHERE slug = 'sast-secrets-track'))"
```
Expected: count ~31 (all SAST units).

- [ ] **Step 4: Run tests**

Run: `docker compose run --rm backend pytest tests/test_seed_courses.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/seed.py backend/tests/test_seed_courses.py
git commit -m "feat(seed): load courses/modules/units from tasks/courses YAML"
```

---

## Task 14: E2E test for /api/courses with linear progression

**Files:**
- Create: `backend/tests/test_courses_api.py`

- [ ] **Step 1: Write the test**

```python
"""E2E: /api/courses list + detail, linear progression locking."""
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from auth import create_access_token, hash_password
from database import async_session
from main import app
from models import (
    Course, Module, ModuleUnit, SubmissionStatus, Task,
    TaskSubmission, TaskType, User, UserRole,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _seed_linear_course():
    async with async_session() as db:
        course = Course(
            title="T Linear", slug="t-linear",
            description="", order=99,
            config={"progression": "linear", "icon": "x"},
        )
        db.add(course)
        await db.flush()

        t1 = Task(slug="t-linear-theory", title="T1", type=TaskType.theory,
                  config={"content_kind": "text"})
        t2 = Task(slug="t-linear-quiz", title="T2", type=TaskType.quiz,
                  config={"questions": []})
        db.add_all([t1, t2])
        await db.flush()

        m1 = Module(course_id=course.id, title="M1", order=1,
                    estimated_hours=1, learning_outcomes=["o1"])
        m2 = Module(course_id=course.id, title="M2", order=2,
                    estimated_hours=1, learning_outcomes=["o2"])
        db.add_all([m1, m2])
        await db.flush()

        db.add_all([
            ModuleUnit(module_id=m1.id, task_id=t1.id, unit_order=1, is_required=True),
            ModuleUnit(module_id=m2.id, task_id=t2.id, unit_order=1, is_required=True),
        ])

        user = User(username="linstudent", password_hash=hash_password("x"),
                    full_name="Lin", role=UserRole.student)
        db.add(user)
        await db.commit()
        return course.id, t1.id, t2.id, user.id


async def test_linear_course_module_is_locked_for_fresh_user():
    course_id, t1, t2, user_id = await _seed_linear_course()
    async with async_session() as db:
        user = (await db.execute(select(User).where(User.id == user_id))).scalar_one()
    token = create_access_token({"sub": user.username})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as ac:
        r = await ac.get("/api/courses/t-linear",
                         headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()
        assert data["slug"] == "t-linear"
        modules = {m["order"]: m for m in data["modules"]}
        assert modules[1]["is_locked"] is False
        assert modules[2]["is_locked"] is True


async def test_linear_course_unlocks_after_success_submission():
    course_id, t1, t2, user_id = await _seed_linear_course()
    async with async_session() as db:
        db.add(TaskSubmission(user_id=user_id, task_id=t1, status=SubmissionStatus.success))
        user = (await db.execute(select(User).where(User.id == user_id))).scalar_one()
        await db.commit()
    token = create_access_token({"sub": user.username})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as ac:
        r = await ac.get("/api/courses/t-linear",
                         headers={"Authorization": f"Bearer {token}"})
        data = r.json()
        modules = {m["order"]: m for m in data["modules"]}
        assert modules[2]["is_locked"] is False
        assert data["completed_unit_count"] == 1
        assert data["unit_count"] == 2
        assert data["progress_pct"] == 50
```

- [ ] **Step 2: Run tests**

Run: `docker compose run --rm backend pytest tests/test_courses_api.py -v`
Expected: 2 passed.

If failures are due to JWT decoding — check that `create_access_token({"sub": username})` matches the shape expected by `get_current_user` in `auth.py`. Adjust if the auth helper expects different claim names.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_courses_api.py
git commit -m "test: e2e for /api/courses list, detail, linear locking"
```

---

## Task 15: Frontend types update

**Files:**
- Modify: `frontend/src/types.ts` (remove Track*, add Course*)

- [ ] **Step 1: Delete old Track interfaces**

Remove `TrackStepItem`, `TrackItem`, `TrackDetail` (currently at `frontend/src/types.ts:108-131`).

- [ ] **Step 2: Add new interfaces**

Append to `frontend/src/types.ts`:

```typescript
export type TaskKind = 'quiz' | 'ctf' | 'gitlab' | 'theory' | 'ssh_lab';

export interface UnitItem {
  id: number;
  task_id: number;
  task_slug: string;
  task_title: string;
  task_type: TaskKind;
  task_difficulty: string | null;
  content_kind: 'text' | 'video' | 'mixed' | null;
  unit_order: number;
  is_required: boolean;
  user_status: 'success' | 'fail' | 'pending' | null;
}

export interface ModuleItem {
  id: number;
  title: string;
  description: string;
  order: number;
  estimated_hours: number | null;
  learning_outcomes: string[];
  config: Record<string, any>;
  is_locked: boolean;
  unit_count: number;
  completed_unit_count: number;
  units: UnitItem[];
}

export interface CourseItem {
  id: number;
  slug: string;
  title: string;
  description: string;
  order: number;
  config: Record<string, any>;
  module_count: number;
  unit_count: number;
  completed_unit_count: number;
  progress_pct: number;
}

export interface CourseDetail extends CourseItem {
  modules: ModuleItem[];
}
```

- [ ] **Step 3: Confirm `tsc` still passes (no uses of removed types yet)**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -40`
Expected: errors pointing at `TracksPage.tsx` / `TrackDetailPage.tsx` / `api.ts` referencing removed types — that's fine, we fix them in next tasks.

Log the errors (e.g., to stdout) and move on.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types.ts
git commit -m "feat(frontend-types): add Course/Module/Unit interfaces, drop Track types"
```

---

## Task 16: Frontend API client update

**Files:**
- Modify: `frontend/src/api.ts`

- [ ] **Step 1: Add imports**

Top of file — if not already importing types, leave as-is (`api.ts` uses `any`/inline types mostly). We'll add type-safe methods for new endpoints.

- [ ] **Step 2: Remove `listTracks` and `getTrack`**

Delete these two lines (currently at `frontend/src/api.ts:112-113`).

- [ ] **Step 3: Add new methods**

Insert in the `api` object:

```typescript
  // Courses
  listCourses: () => request<import('./types').CourseItem[]>('/courses'),
  getCourse: (slugOrId: string | number) =>
    request<import('./types').CourseDetail>(`/courses/${slugOrId}`),
  getModule: (id: number) =>
    request<import('./types').ModuleItem>(`/modules/${id}`),

  markViewed: (taskId: number) =>
    request<{ ok: boolean }>('/me/progress/viewed', {
      method: 'POST',
      body: JSON.stringify({ task_id: taskId }),
    }),
```

- [ ] **Step 4: Verify**

Run: `cd frontend && npx tsc --noEmit 2>&1 | grep -E 'api\.ts' | head -20`
Expected: no errors in `api.ts` itself (errors elsewhere are handled by later tasks).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api.ts
git commit -m "feat(frontend-api): add listCourses/getCourse/getModule/markViewed"
```

---

## Task 17: Extract `UnitRow` component + create `CoursesPage`/`CourseCard`

**Files:**
- Create: `frontend/src/components/UnitRow.tsx`
- Create: `frontend/src/components/CourseCard.tsx`
- Create: `frontend/src/pages/CoursesPage.tsx`
- Read-only reference: `frontend/src/pages/TracksPage.tsx` (not modified yet — kept until Task 21 deletes it)

- [ ] **Step 1: Create `UnitRow.tsx` by copying logic from `TrackDetailPage.tsx:20-101` and renaming**

```tsx
import { useNavigate } from 'react-router-dom';
import type { UnitItem } from '../types';

const TYPE_LABELS: Record<string, string> = {
  quiz: 'ТЕСТ',
  ctf: 'ЛАБ',
  gitlab: 'GITLAB',
  theory: 'ТЕОРИЯ',
  ssh_lab: 'SSH',
};

const DIFFICULTY_LABELS: Record<string, string> = {
  low: 'Низкая',
  medium: 'Средняя',
  hard: 'Высокая',
  advanced: 'Продвинутый',
};

interface UnitRowProps {
  unit: UnitItem;
  index: number;   // display index (1-based for non-theory)
  locked?: boolean;
}

export default function UnitRow({ unit, index, locked = false }: UnitRowProps) {
  const navigate = useNavigate();
  const isTheory = unit.task_type === 'theory';
  const isDone = unit.user_status === 'success';
  const isFail = unit.user_status === 'fail';
  const typeLabel = TYPE_LABELS[unit.task_type] || unit.task_type.toUpperCase();

  const handleClick = () => {
    if (locked) return;
    navigate(`/challenges/${unit.task_id}`);
  };

  return (
    <button
      onClick={handleClick}
      disabled={locked}
      className={`w-full text-left flex items-center gap-4 px-5 py-4 border transition-all duration-150 group
        ${locked
          ? 'border-outline-variant/10 bg-surface-container-low/30 opacity-60 cursor-not-allowed'
          : isTheory
            ? 'border-amber-500/15 hover:border-amber-500/40 hover:bg-surface-container bg-surface-container-low/60'
            : 'border-outline-variant/15 hover:border-primary/40 hover:bg-surface-container bg-surface-container-low'
        }`}
    >
      <div className={`w-8 h-8 flex-shrink-0 flex items-center justify-center border text-xs font-mono font-bold
        ${isTheory
          ? 'border-amber-500/30 text-amber-400'
          : isDone
            ? 'border-primary bg-primary/10 text-primary'
            : 'border-outline-variant/30 text-on-surface-variant'
        }`}>
        {isTheory ? (
          <span className="material-symbols-outlined text-base">menu_book</span>
        ) : isDone ? (
          <span className="material-symbols-outlined text-base" style={{ fontVariationSettings: "'FILL' 1" }}>check</span>
        ) : (
          String(index).padStart(2, '0')
        )}
      </div>

      <span className={`flex-shrink-0 text-[9px] font-mono font-bold uppercase tracking-widest px-2 py-0.5 border
        ${isTheory
          ? 'border-amber-500/40 text-amber-400 bg-amber-500/5'
          : unit.task_type === 'quiz'
            ? 'border-blue-500/40 text-blue-400 bg-blue-500/5'
            : 'border-primary/40 text-primary bg-primary/5'
        }`}>
        {typeLabel}
      </span>

      <span className={`flex-1 font-body font-medium text-sm truncate transition-colors
        ${isTheory
          ? 'text-on-surface-variant group-hover:text-amber-400'
          : 'text-on-surface group-hover:text-primary'
        }`}>
        {unit.task_title}
      </span>

      {!isTheory && unit.task_difficulty && (
        <span className="flex-shrink-0 text-[10px] font-mono text-on-surface-variant hidden sm:block">
          {DIFFICULTY_LABELS[unit.task_difficulty] || unit.task_difficulty}
        </span>
      )}

      {!isTheory && (
        <div className="flex-shrink-0 w-20 text-right">
          {isDone && (
            <span className="text-[10px] font-mono uppercase tracking-widest text-primary">Выполнено</span>
          )}
          {isFail && (
            <span className="text-[10px] font-mono uppercase tracking-widest text-error">Неверно</span>
          )}
          {!isDone && !isFail && (
            <span className="text-[10px] font-mono uppercase tracking-widest text-on-surface-variant">—</span>
          )}
        </div>
      )}

      {locked ? (
        <span className="material-symbols-outlined text-on-surface-variant text-base flex-shrink-0">lock</span>
      ) : (
        <span className="material-symbols-outlined text-on-surface-variant text-base flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
          chevron_right
        </span>
      )}
    </button>
  );
}
```

- [ ] **Step 2: Create `CourseCard.tsx`**

```tsx
import { Link } from 'react-router-dom';
import type { CourseItem } from '../types';

interface Props {
  course: CourseItem;
}

export default function CourseCard({ course }: Props) {
  const icon = (course.config?.icon as string) || 'school';
  const progression = (course.config?.progression as string) || 'free';
  return (
    <Link
      to={`/courses/${course.slug}`}
      className="block p-5 border border-outline-variant/20 bg-surface-container-low hover:border-primary/40 hover:bg-surface-container transition-all duration-150 group"
    >
      <div className="flex items-start gap-4 mb-3">
        <span className="material-symbols-outlined text-primary text-3xl">{icon}</span>
        <div className="flex-1 min-w-0">
          <h3 className="font-headline font-bold text-lg text-on-surface group-hover:text-primary transition-colors truncate">
            {course.title}
          </h3>
          <p className="text-[10px] font-mono uppercase tracking-widest text-on-surface-variant mt-1">
            {course.module_count} {course.module_count === 1 ? 'модуль' : 'модулей'} · {progression === 'linear' ? 'последовательно' : 'свободно'}
          </p>
        </div>
      </div>
      <p className="text-sm text-on-surface-variant line-clamp-2 mb-4">{course.description}</p>
      <div className="space-y-1.5">
        <div className="flex justify-between text-[10px] font-mono uppercase tracking-widest">
          <span className="text-on-surface-variant">Прогресс</span>
          <span className="text-primary">{course.completed_unit_count}/{course.unit_count}</span>
        </div>
        <div className="h-1.5 bg-surface-container-high">
          <div className="h-full bg-primary transition-all duration-500" style={{ width: `${course.progress_pct}%` }} />
        </div>
      </div>
    </Link>
  );
}
```

- [ ] **Step 3: Create `CoursesPage.tsx`**

```tsx
import { useEffect, useState } from 'react';
import { api } from '../api';
import type { CourseItem } from '../types';
import CourseCard from '../components/CourseCard';

export default function CoursesPage() {
  const [courses, setCourses] = useState<CourseItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listCourses().then(setCourses).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <span className="text-primary animate-pulse font-headline text-xl">Загрузка...</span>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl md:text-4xl font-headline font-bold text-on-surface tracking-tighter uppercase mb-2">
          Курсы
        </h1>
        <p className="text-on-surface-variant text-sm max-w-2xl">
          Структурированные программы по безопасной разработке.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {courses.map(c => <CourseCard key={c.id} course={c} />)}
      </div>

      {courses.length === 0 && (
        <div className="text-center py-20 text-on-surface-variant">Нет доступных курсов</div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/UnitRow.tsx frontend/src/components/CourseCard.tsx frontend/src/pages/CoursesPage.tsx
git commit -m "feat(frontend): add UnitRow, CourseCard, CoursesPage components"
```

---

## Task 18: `ModuleAccordion` + `CourseDetailPage`

**Files:**
- Create: `frontend/src/components/LearningOutcomesList.tsx`
- Create: `frontend/src/components/ModuleMetaBar.tsx`
- Create: `frontend/src/components/ModuleAccordion.tsx`
- Create: `frontend/src/pages/CourseDetailPage.tsx`

- [ ] **Step 1: Create `LearningOutcomesList.tsx`**

```tsx
interface Props { outcomes: string[]; }

export default function LearningOutcomesList({ outcomes }: Props) {
  if (!outcomes.length) return null;
  return (
    <ul className="space-y-1.5 mb-3">
      {outcomes.map((o, i) => (
        <li key={i} className="flex items-start gap-2 text-sm text-on-surface-variant">
          <span className="material-symbols-outlined text-primary text-base mt-0.5">check_circle</span>
          <span>{o}</span>
        </li>
      ))}
    </ul>
  );
}
```

- [ ] **Step 2: Create `ModuleMetaBar.tsx`**

```tsx
interface Props {
  estimatedHours: number | null;
  outcomesCount: number;
}

export default function ModuleMetaBar({ estimatedHours, outcomesCount }: Props) {
  const parts: string[] = [];
  if (estimatedHours !== null && estimatedHours !== undefined) {
    parts.push(`⏱ ~${estimatedHours} ${estimatedHours === 1 ? 'час' : 'часа/часов'}`);
  }
  if (outcomesCount > 0) {
    parts.push(`🎯 ${outcomesCount} ${outcomesCount === 1 ? 'цель' : 'цели'}`);
  }
  if (!parts.length) return null;
  return (
    <div className="text-[10px] font-mono uppercase tracking-widest text-on-surface-variant mb-3">
      {parts.join(' · ')}
    </div>
  );
}
```

- [ ] **Step 3: Create `ModuleAccordion.tsx`**

```tsx
import { useState } from 'react';
import type { ModuleItem } from '../types';
import UnitRow from './UnitRow';
import LearningOutcomesList from './LearningOutcomesList';
import ModuleMetaBar from './ModuleMetaBar';

interface Props {
  module: ModuleItem;
  defaultOpen: boolean;
}

export default function ModuleAccordion({ module, defaultOpen }: Props) {
  const [open, setOpen] = useState(defaultOpen && !module.is_locked);

  const pct = module.unit_count > 0
    ? Math.round((module.completed_unit_count / module.unit_count) * 100)
    : 0;

  const icon = (module.config?.icon as string) || 'folder';

  return (
    <div className={`border transition-colors
      ${module.is_locked ? 'border-outline-variant/10 bg-surface-container-low/20' : 'border-outline-variant/20 bg-surface-container-low'}`}>
      <button
        onClick={() => !module.is_locked && setOpen(o => !o)}
        disabled={module.is_locked}
        className={`w-full flex items-center gap-3 px-5 py-4 text-left transition-colors
          ${module.is_locked ? 'cursor-not-allowed' : 'hover:bg-surface-container'}`}
      >
        <span className={`material-symbols-outlined ${module.is_locked ? 'text-on-surface-variant/50' : 'text-primary'} text-xl`}>
          {module.is_locked ? 'lock' : icon}
        </span>
        <div className="flex-1 min-w-0">
          <div className={`font-headline font-bold uppercase tracking-tight text-sm truncate
            ${module.is_locked ? 'text-on-surface-variant' : 'text-on-surface'}`}>
            Модуль {module.order}: {module.title}
          </div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-on-surface-variant mt-0.5">
            {module.is_locked
              ? 'Заблокирован — завершите предыдущие модули'
              : `${module.completed_unit_count}/${module.unit_count} выполнено · ${pct}%`}
          </div>
        </div>
        {!module.is_locked && (
          <span className="material-symbols-outlined text-on-surface-variant">
            {open ? 'expand_less' : 'expand_more'}
          </span>
        )}
      </button>

      {open && !module.is_locked && (
        <div className="border-t border-outline-variant/15 px-5 pt-4 pb-5">
          {module.description && (
            <p className="text-sm text-on-surface-variant mb-3 max-w-3xl">{module.description}</p>
          )}
          <ModuleMetaBar estimatedHours={module.estimated_hours} outcomesCount={module.learning_outcomes.length} />
          <LearningOutcomesList outcomes={module.learning_outcomes} />

          <div className="space-y-2 mt-4">
            {module.units.map((unit, i) => (
              <UnitRow
                key={unit.id}
                unit={unit}
                index={unit.task_type === 'theory' ? 0 : i + 1}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Create `CourseDetailPage.tsx`**

```tsx
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../api';
import type { CourseDetail } from '../types';
import ModuleAccordion from '../components/ModuleAccordion';
import UnitRow from '../components/UnitRow';

export default function CourseDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const [course, setCourse] = useState<CourseDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!slug) return;
    api.getCourse(slug).then(setCourse).finally(() => setLoading(false));
  }, [slug]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <span className="text-primary animate-pulse font-headline text-xl">Загрузка...</span>
      </div>
    );
  }

  if (!course) {
    return <div className="text-center py-20 text-on-surface-variant">Курс не найден</div>;
  }

  // Short-course flat render: single module without description
  const flatRender = course.modules.length === 1 && !course.modules[0].description;

  // Pick which module to open by default: first one with unfinished required units
  const defaultOpenIdx = course.modules.findIndex(m => !m.is_locked && m.completed_unit_count < m.unit_count);

  const totalHours = course.modules.reduce((sum, m) => sum + (m.estimated_hours || 0), 0);
  const hoursKnown = course.modules.filter(m => m.estimated_hours !== null && m.estimated_hours !== undefined).length;
  const showHours = hoursKnown >= Math.ceil(course.modules.length / 2);

  return (
    <div>
      <div className="mb-6 flex items-center gap-2 text-[10px] font-mono uppercase tracking-widest text-on-surface-variant">
        <Link to="/courses" className="hover:text-primary transition-colors">Курсы</Link>
        <span>/</span>
        <span className="text-on-surface">{course.title}</span>
      </div>

      <div className="mb-8">
        <h1 className="text-3xl md:text-4xl font-headline font-bold text-on-surface tracking-tighter uppercase mb-3">
          {course.title}
        </h1>
        <p className="text-on-surface-variant text-sm max-w-2xl mb-6">{course.description}</p>

        <div className="flex items-center gap-6 flex-wrap">
          <div className="flex items-center gap-4 max-w-sm min-w-[16rem]">
            <div className="flex-1 space-y-1.5">
              <div className="flex justify-between text-[10px] font-mono uppercase tracking-widest">
                <span className="text-on-surface-variant">Прогресс</span>
                <span className="text-primary">{course.completed_unit_count}/{course.unit_count}</span>
              </div>
              <div className="h-1.5 bg-surface-container-high">
                <div className="h-full bg-primary transition-all duration-500" style={{ width: `${course.progress_pct}%` }} />
              </div>
            </div>
            <span className="text-2xl font-headline font-bold text-primary">{course.progress_pct}%</span>
          </div>

          {showHours && totalHours > 0 && (
            <div className="text-[10px] font-mono uppercase tracking-widest text-on-surface-variant">
              ⏱ ~{totalHours} часов суммарно
            </div>
          )}
        </div>
      </div>

      {flatRender ? (
        <div className="space-y-2">
          {course.modules[0].units.map((unit, i) => (
            <UnitRow key={unit.id} unit={unit} index={unit.task_type === 'theory' ? 0 : i + 1} />
          ))}
        </div>
      ) : (
        <div className="space-y-3">
          {course.modules.map((m, idx) => (
            <ModuleAccordion
              key={m.id}
              module={m}
              defaultOpen={idx === defaultOpenIdx}
            />
          ))}
        </div>
      )}

      {course.modules.length === 0 && (
        <div className="text-center py-20 text-on-surface-variant">В этом курсе нет модулей</div>
      )}
    </div>
  );
}
```

- [ ] **Step 5: `tsc --noEmit` check**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -40`
Expected: no errors in any of the new files. (Errors in old `TracksPage.tsx` / `TrackDetailPage.tsx` are expected — fixed in Task 20.)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/ModuleAccordion.tsx frontend/src/components/LearningOutcomesList.tsx frontend/src/components/ModuleMetaBar.tsx frontend/src/pages/CourseDetailPage.tsx
git commit -m "feat(frontend): add ModuleAccordion and CourseDetailPage"
```

---

## Task 19: Theory `content_kind` rendering + `markViewed` one-shot

**Files:**
- Modify: `frontend/src/pages/ChallengeDetailsPage.tsx`

- [ ] **Step 1: Read current ChallengeDetailsPage to locate theory rendering**

Run: `grep -n "theory\|content_kind\|video" frontend/src/pages/ChallengeDetailsPage.tsx`

Identify where the theory task is rendered (probably an `{task.type === 'theory' && ...}` branch).

- [ ] **Step 2: Add `markViewed` effect**

At the top of `ChallengeDetailsPage`, after the task is loaded successfully AND when `task.type === 'theory'`, call `api.markViewed(task.id)` exactly once per mount. Example pattern:

```tsx
import { useEffect, useRef } from 'react';
// ...
const markedRef = useRef(false);
useEffect(() => {
  if (!task || task.type !== 'theory' || markedRef.current) return;
  markedRef.current = true;
  api.markViewed(task.id).catch(() => {/* no-op */});
}, [task]);
```

- [ ] **Step 3: Add video rendering for `content_kind: 'video' | 'mixed'`**

In the theory render branch, read `content_kind = task.config?.content_kind ?? 'text'`. When `'video'` or `'mixed'`, render:

```tsx
const video = task.config?.video as { provider?: string; src?: string } | undefined;
if (contentKind === 'video' || contentKind === 'mixed') {
  if (video?.provider === 'youtube' && video.src) {
    // Handle both full URLs and raw IDs
    const id = video.src.includes('youtube.com') || video.src.includes('youtu.be')
      ? new URL(video.src).searchParams.get('v') || video.src.split('/').pop() || ''
      : video.src;
    return (
      <div className="aspect-video bg-black mb-6">
        <iframe
          className="w-full h-full"
          src={`https://www.youtube.com/embed/${id}`}
          title={task.title}
          allowFullScreen
        />
      </div>
    );
  }
  if (video?.src) {
    return (
      <video controls className="w-full mb-6 bg-black" src={video.src} />
    );
  }
}
```

Place this block immediately above (or alongside) the markdown rendering so that `mixed` shows both.

- [ ] **Step 4: Manual smoke — open a theory task**

Run:
```bash
docker compose up -d --build frontend backend
```

Open `http://lms.lab.local/challenges/<theory_task_id>` in a browser (use an existing theory task id from the DB, e.g. the one from `sast-foundations-theory`). Verify:
- Page renders
- Network tab shows `POST /api/me/progress/viewed` fired once
- Re-mounting the page doesn't fire additional requests if already marked success on backend (it does fire once per mount from frontend; backend is idempotent — both are fine)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/ChallengeDetailsPage.tsx
git commit -m "feat(frontend): theory content_kind rendering + markViewed on open"
```

---

## Task 20: Wire routes, redirect `/tracks/*`, delete old pages

**Files:**
- Modify: `frontend/src/main.tsx` or wherever React Router is configured (find by `grep -rn 'createBrowserRouter\|BrowserRouter\|useRoutes' frontend/src`)
- Delete: `frontend/src/pages/TracksPage.tsx`
- Delete: `frontend/src/pages/TrackDetailPage.tsx`

- [ ] **Step 1: Locate router setup**

Run: `grep -rn 'TracksPage\|TrackDetailPage\|"/tracks"\|path: *"tracks' frontend/src`

Expected: hits in `main.tsx` or `App.tsx`.

- [ ] **Step 2: Replace routes**

In the router config, replace references to `TracksPage`/`TrackDetailPage` with new `CoursesPage`/`CourseDetailPage`. Add redirects for old paths. Example (for `createBrowserRouter`):

```tsx
import CoursesPage from './pages/CoursesPage';
import CourseDetailPage from './pages/CourseDetailPage';
import { Navigate } from 'react-router-dom';

// ...
{ path: 'courses', element: <CoursesPage /> },
{ path: 'courses/:slug', element: <CourseDetailPage /> },

// Redirects
{ path: 'tracks', element: <Navigate to="/courses" replace /> },
// Old /tracks/:id — the track id equals the new course id (preserved by migration),
// but the route key for new page is slug. Redirect by id to /courses/:id — backend
// accepts both slug and id.
{ path: 'tracks/:id', element: <Navigate to="/courses/:id" replace /> },
```

Note on the dynamic redirect: `<Navigate to="/courses/:id" replace />` does NOT substitute `:id` automatically. Use a small wrapper:

```tsx
function TrackIdRedirect() {
  const { id } = useParams<{ id: string }>();
  return <Navigate to={`/courses/${id}`} replace />;
}
// then: { path: 'tracks/:id', element: <TrackIdRedirect /> },
```

- [ ] **Step 3: Update nav links**

Run: `grep -rn '"/tracks"\|>Треки<\|to="/tracks"' frontend/src`

Each hit (sidebars, top nav) should be updated: `/tracks` → `/courses`, `Треки` → `Курсы`.

- [ ] **Step 4: Delete old pages**

```bash
rm frontend/src/pages/TracksPage.tsx frontend/src/pages/TrackDetailPage.tsx
```

- [ ] **Step 5: `tsc --noEmit` must pass cleanly**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 6: Manual smoke**

```bash
docker compose up -d frontend
```

Open `http://lms.lab.local/tracks` — should redirect to `/courses`.
Open `http://lms.lab.local/tracks/1` — should redirect to `/courses/1`.
Open `http://lms.lab.local/courses` — list renders.
Open `http://lms.lab.local/courses/sast-secrets-track` — accordion renders 1 module (before Task 21's reseed, this is still the post-migration "Основы" module).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/main.tsx frontend/src
git rm frontend/src/pages/TracksPage.tsx frontend/src/pages/TrackDetailPage.tsx
git commit -m "feat(frontend): wire /courses routes, redirect /tracks, delete old pages"
```

---

## Task 21: Apply generated YAML — reseed to get 8 SAST modules

**Files:**
- No new files; runs existing scripts to replace the "Основы" fallback modules with real ones parsed from track YAML comments.

- [ ] **Step 1: Generate new YAMLs if not already present**

```bash
python3 scripts/migrate-tracks-to-courses.py
ls -1 tasks/courses/
```

Expected: 4 files.

- [ ] **Step 2: Reseed**

```bash
./scripts/deploy-labs.sh --seed
```

Expected log: `Updated course: Static Analysis & Secrets Detection` etc.

- [ ] **Step 3: Verify module counts**

```bash
docker compose exec postgres psql -U lms -d lms -c "
  SELECT c.slug, COUNT(m.id) AS module_count,
         (SELECT COUNT(*) FROM module_units mu JOIN modules m2 ON mu.module_id = m2.id WHERE m2.course_id = c.id) AS unit_count
  FROM courses c LEFT JOIN modules m ON m.course_id = c.id
  GROUP BY c.id ORDER BY c.id
"
```

Expected: `sast-secrets-track` has 8 modules and ~31 units; others have 1 module with 2-9 units.

- [ ] **Step 4: Manual browser smoke**

Open `http://lms.lab.local/courses/sast-secrets-track`. Verify:
- 8 module accordions
- First unfinished module expanded
- Learning outcomes (empty for now — placeholders)
- Progress bar reflects current user's completions

Open `http://lms.lab.local/courses/sqli-track`. Verify:
- Flat list (no accordion) because single module "Основы" with no description

- [ ] **Step 5: Commit (no code change; commit if YAMLs changed)**

```bash
git add tasks/courses/
git diff --cached --stat
git commit -m "chore: regenerate tasks/courses YAML with per-module split"
```

If `git diff --cached` is empty (already committed in Task 12), skip the commit.

---

## Task 22: Add linear progression to SAST + smoke gating

**Files:**
- Modify: `tasks/courses/sast-secrets-track.yaml` (set `config.progression: "linear"`)

- [ ] **Step 1: Edit YAML**

Open `tasks/courses/sast-secrets-track.yaml`. Under `config:` add (or update) `progression: linear`:

```yaml
config:
  icon: search
  progression: linear
```

- [ ] **Step 2: Reseed**

```bash
./scripts/deploy-labs.sh --seed
```

- [ ] **Step 3: Verify in DB**

```bash
docker compose exec postgres psql -U lms -d lms -c "SELECT slug, config FROM courses WHERE slug = 'sast-secrets-track'"
```

Expected: `config` contains `"progression": "linear"`.

- [ ] **Step 4: Smoke gating as fresh student**

```bash
# Create a fresh student
TOKEN=$(curl -s -X POST http://localhost/api/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin"}' | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
curl -s -X POST http://localhost/api/admin/users -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"username":"lintester","password":"pass","full_name":"Lin Tester","role":"student"}'
STOKEN=$(curl -s -X POST http://localhost/api/auth/login -H 'Content-Type: application/json' -d '{"username":"lintester","password":"pass"}' | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')

curl -s -H "Authorization: Bearer $STOKEN" http://localhost/api/courses/sast-secrets-track | python3 -c 'import json,sys; d=json.load(sys.stdin); [print(m["order"], m["title"], "locked=", m["is_locked"]) for m in d["modules"]]'
```

Expected: module 1 `locked=False`, modules 2–8 `locked=True`.

- [ ] **Step 5: Attempt to submit a quiz from module 2 as `lintester` — expect 403**

Find a task_id inside module 2:
```bash
docker compose exec postgres psql -U lms -d lms -c "
  SELECT mu.task_id, t.title, t.type
  FROM module_units mu JOIN modules m ON mu.module_id = m.id JOIN tasks t ON mu.task_id = t.id
  WHERE m.course_id = (SELECT id FROM courses WHERE slug = 'sast-secrets-track') AND m.order = 2
  ORDER BY mu.unit_order LIMIT 1
"
```

Let's say it returns `task_id = 42, type = quiz`. Then:

```bash
curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $STOKEN" -X POST http://localhost/api/quiz/42/submit -H 'Content-Type: application/json' -d '{"answers":{}}'
```

Expected: `403`.

- [ ] **Step 6: Commit**

```bash
git add tasks/courses/sast-secrets-track.yaml
git commit -m "content: enable linear progression for SAST track"
```

---

## Task 23: Smoke script

**Files:**
- Create: `scripts/smoke-course-flow.sh`

- [ ] **Step 1: Write script**

```bash
#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-http://localhost}"
USERNAME="${USERNAME:-admin}"
PASSWORD="${PASSWORD:-admin}"

echo "1. Login"
TOKEN=$(curl -sf -X POST "$HOST/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')

echo "2. List courses"
COUNT=$(curl -sf -H "Authorization: Bearer $TOKEN" "$HOST/api/courses" \
  | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))')
echo "   got $COUNT courses"
if [ "$COUNT" -lt 4 ]; then echo "FAIL: expected >= 4 courses"; exit 1; fi

echo "3. SAST detail"
MODS=$(curl -sf -H "Authorization: Bearer $TOKEN" "$HOST/api/courses/sast-secrets-track" \
  | python3 -c 'import json,sys; print(len(json.load(sys.stdin)["modules"]))')
echo "   sast has $MODS modules"
if [ "$MODS" -lt 8 ]; then echo "FAIL: expected >= 8 modules in sast"; exit 1; fi

echo "4. SQLi detail (short course)"
SMODS=$(curl -sf -H "Authorization: Bearer $TOKEN" "$HOST/api/courses/sqli-track" \
  | python3 -c 'import json,sys; print(len(json.load(sys.stdin)["modules"]))')
echo "   sqli has $SMODS modules"
if [ "$SMODS" -ne 1 ]; then echo "FAIL: expected 1 module in sqli"; exit 1; fi

echo "5. Redirect /api/tracks"
CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" "$HOST/api/tracks")
echo "   /api/tracks -> $CODE"
if [ "$CODE" != "308" ]; then echo "FAIL: expected 308 on /api/tracks"; exit 1; fi

echo ""
echo "ALL SMOKE TESTS PASSED"
```

- [ ] **Step 2: Make executable and run**

```bash
chmod +x scripts/smoke-course-flow.sh
./scripts/smoke-course-flow.sh
```

Expected: `ALL SMOKE TESTS PASSED`.

- [ ] **Step 3: Commit**

```bash
git add scripts/smoke-course-flow.sh
git commit -m "test: smoke script for course flow"
```

---

## Task 24: Full test suite run + final verification

**Files:** none

- [ ] **Step 1: Run all backend tests**

```bash
docker compose run --rm backend pytest tests/ -v
```

Expected: all tests pass (test_progression, test_progress_viewed, test_courses_api, test_seed_courses; test_unlock_guard has skipped placeholder).

- [ ] **Step 2: Frontend typecheck**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Full app smoke**

```bash
./scripts/smoke-course-flow.sh
```

Expected: `ALL SMOKE TESTS PASSED`.

- [ ] **Step 4: Manual browser walkthrough**

Open `http://lms.lab.local` as `admin`/`admin`:
- `/courses` — list shows 4 courses with progress bars
- `/courses/sast-secrets-track` — 8 modules, first open
- `/courses/sqli-track` — flat list (no accordion), 2 units
- `/challenges/<theory_id>` — theory unit marked as success after open (re-visit `/courses/sast-secrets-track` and confirm unit shows ✓ Выполнено)

Login as a fresh student:
- `/courses/sast-secrets-track` — modules 2-8 show lock icon and don't expand

- [ ] **Step 5: Verify git log**

```bash
git log --oneline main..HEAD | head -30
```

Expected: ~20 commits with a clean narrative (alembic setup → models → migrations → services → api → frontend components → pages → routing → content).

No commit for this step.

---

## Post-implementation cleanup (follow-up, not part of this plan)

After one release cycle in production, a follow-up PR should:

- Delete `backend/routers/tracks.py` entirely
- Remove `tracks` include from `main.py`
- Remove `tasks/tracks/` directory
- Delete `scripts/migrate-tracks-to-courses.py` (one-shot, no longer needed)

This is tracked as a future task, not included in the current plan.
