# Web UI Content Editor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Перевести управление курсами/модулями/юнитами/тасками из YAML-файлов в админ-веб-интерфейс, сделать БД единственным источником правды, удалить старый seed-пайплайн.

**Architecture:** Новый роутер `backend/routers/admin_content.py` с CRUD-эндпоинтами под `/api/admin/content`, защищён `require_admin`. Импорт/экспорт через ZIP-бандлы с YAML-манифестами. На фронте — новые страницы под `/admin/courses` и `/admin/tasks`. В конце — снос `seed.py`, `deploy-labs.sh`, `tasks/`.

**Tech Stack:** FastAPI 0.115, SQLAlchemy async, Alembic, Pydantic v2, PyYAML, React 18, Vite, Tailwind, @dnd-kit/core, @dnd-kit/sortable.

**Spec:** `docs/superpowers/specs/2026-04-18-web-content-editor-design.md`

---

## Files overview

**Backend — new:**
- `backend/alembic/versions/0004_course_visibility_task_audit.py` — миграция
- `backend/routers/admin_content.py` — все админ-эндпоинты
- `backend/services/slug.py` — генерация/валидация slug
- `backend/services/flag_hash.py` — SHA256-хэширование
- `backend/services/bundle.py` — pack/unpack ZIP-бандлов
- `backend/schemas_admin.py` — Pydantic-схемы для админ-API (type-specific configs)
- `backend/tests/test_admin_content_*.py` — тесты (по файлу на домен)

**Backend — modified:**
- `backend/models.py` — `Course.is_visible`, `Task.author_id`, `Task.updated_at`
- `backend/schemas.py` — расширение `CourseOut` полем `is_visible`
- `backend/routers/courses.py` — фильтр `is_visible=true` для студентов
- `backend/main.py` — подключить роутер `admin_content`
- `backend/requirements.txt` — добавить `pyyaml`

**Backend — deleted (Phase 10):**
- `backend/seed.py`
- `backend/tests/test_seed_courses.py`
- `scripts/deploy-labs.sh`
- `scripts/migrate-tracks-to-courses.py`
- `tasks/` (вся папка)

**Frontend — new:**
- `frontend/src/pages/admin/AdminCoursesPage.tsx`
- `frontend/src/pages/admin/CourseEditorPage.tsx`
- `frontend/src/pages/admin/AdminTasksPage.tsx`
- `frontend/src/pages/admin/TaskEditorPage.tsx`
- `frontend/src/components/admin/TaskPicker.tsx`
- `frontend/src/components/admin/ModuleCard.tsx`
- `frontend/src/components/admin/UnitRow.tsx`
- `frontend/src/components/admin/task-forms/TheoryForm.tsx`
- `frontend/src/components/admin/task-forms/QuizForm.tsx`
- `frontend/src/components/admin/task-forms/CtfForm.tsx`
- `frontend/src/components/admin/task-forms/SshLabForm.tsx`
- `frontend/src/components/admin/task-forms/GitlabForm.tsx`
- `frontend/src/components/admin/MarkdownEditor.tsx`

**Frontend — modified:**
- `frontend/src/api.ts` — новая секция `api.adminContent`
- `frontend/src/main.tsx` — новые маршруты
- `frontend/src/components/Sidebar.tsx` — пункты «Курсы» и «Таски»
- `frontend/src/types.ts` — типы админских ресурсов
- `frontend/package.json` — `@dnd-kit/core`, `@dnd-kit/sortable`

**Docs/scripts — modified:**
- `README.md` — убрать разделы про YAML и `deploy-labs.sh`
- `scripts/smoke-course-flow.sh` — расширить под UI-флоу

---

# Phase 1 — Data model

### Task 1: Alembic-миграция — add Course.is_visible, Task.author_id, Task.updated_at

**Files:**
- Create: `backend/alembic/versions/0004_course_visibility_task_audit.py`

- [ ] **Step 1: Создать файл миграции**

```python
"""add course visibility and task audit fields

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-18 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "courses",
        sa.Column("is_visible", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    # Все существующие курсы делаем видимыми (уже в проде — не ломаем)
    op.execute("UPDATE courses SET is_visible = TRUE")

    op.add_column(
        "tasks",
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
    )
    op.add_column(
        "tasks",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("tasks", "updated_at")
    op.drop_column("tasks", "author_id")
    op.drop_column("courses", "is_visible")
```

- [ ] **Step 2: Прогнать миграцию в докере**

Run: `docker compose exec backend alembic upgrade head`
Expected: `INFO  [alembic.runtime.migration] Running upgrade 0003 -> 0004`

- [ ] **Step 3: Проверить схему**

Run: `docker compose exec postgres psql -U lms -d lms -c '\d courses' | grep is_visible`
Expected: строка `is_visible | boolean | not null default false`

- [ ] **Step 4: Commit**

```bash
git add backend/alembic/versions/0004_course_visibility_task_audit.py
git commit -m "feat(db): add course visibility and task audit fields"
```

---

### Task 2: Обновить SQLAlchemy-модели

**Files:**
- Modify: `backend/models.py`

- [ ] **Step 1: Добавить поля в Course**

В `backend/models.py` в классе `Course`, после строки `config = Column(JSONB, default=dict)`:

```python
    is_visible = Column(Boolean, default=False, nullable=False)
```

- [ ] **Step 2: Добавить поля в Task**

В классе `Task`, после строки `created_at = Column(...)`:

```python
    author_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
```

- [ ] **Step 3: Повторно перезапустить backend и убедиться что поднимается**

Run: `docker compose restart backend && sleep 3 && docker compose logs backend --tail=20`
Expected: строка `Uvicorn running on http://0.0.0.0:8000` без traceback.

- [ ] **Step 4: Commit**

```bash
git add backend/models.py
git commit -m "feat(models): Course.is_visible, Task.author_id, Task.updated_at"
```

---

### Task 3: Pydantic-схемы админа

**Files:**
- Create: `backend/schemas_admin.py`

- [ ] **Step 1: Написать схемы**

```python
"""Pydantic-схемы для /api/admin/content.

Type-specific конфиги (theory/quiz/ctf/ssh_lab/gitlab) валидируются дискриминированным
союзом через поле `type` на уровне TaskCreate/TaskUpdate.
"""
from datetime import datetime
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from models import TaskType

SLUG_RE = r"^[a-z0-9-]{2,100}$"


# --- Task configs per type ---

class TheoryVideo(BaseModel):
    provider: Literal["youtube", "url"]
    src: str


class TheoryConfig(BaseModel):
    content_kind: Literal["text", "video", "mixed"] = "text"
    tags: list[str] = Field(default_factory=list)
    content: str = ""
    video: TheoryVideo | None = None


class QuizChoice(BaseModel):
    text: str
    correct: bool = False


class QuizQuestion(BaseModel):
    id: int | None = None
    text: str
    options: list[QuizChoice]


class QuizConfig(BaseModel):
    questions: list[QuizQuestion] = Field(default_factory=list)
    pass_threshold: int = 70
    shuffle: bool = False


class CtfConfig(BaseModel):
    docker_image: str
    port: int = 5000
    ttl_minutes: int = 120
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    flag_hash: str = ""
    # plaintext flag — write-only, никогда не возвращается наружу
    flag: str | None = None


class SshLabConfig(BaseModel):
    docker_image: str
    terminal_port: int = 80
    ttl_minutes: int = 120
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    instructions: str = ""
    flag_hash: str = ""
    flag: str | None = None


class GitlabConfig(BaseModel):
    # Пропускаем все поля существующей gitlab-конфигурации как есть
    model_config = ConfigDict(extra="allow")


# --- Task create/update ---

class TaskBase(BaseModel):
    slug: str = Field(pattern=SLUG_RE)
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    order: int = 0


class TaskCreate(TaskBase):
    type: TaskType
    config: dict = Field(default_factory=dict)


class TaskUpdate(BaseModel):
    slug: str | None = Field(default=None, pattern=SLUG_RE)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    order: int | None = None
    config: dict | None = None


class TaskUsage(BaseModel):
    course_id: int
    course_slug: str
    module_id: int
    unit_id: int


class TaskOutAdmin(TaskBase):
    id: int
    type: TaskType
    config: dict
    author_id: int | None
    updated_at: datetime
    usage: list[TaskUsage] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# --- Course/Module/Unit ---

class CourseCreate(BaseModel):
    slug: str = Field(pattern=SLUG_RE)
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    order: int = 0
    config: dict = Field(default_factory=dict)


class CourseUpdate(BaseModel):
    slug: str | None = Field(default=None, pattern=SLUG_RE)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    order: int | None = None
    config: dict | None = None
    is_visible: bool | None = None


class ModuleCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    order: int = 0
    estimated_hours: int | None = None
    learning_outcomes: list[str] = Field(default_factory=list)
    config: dict = Field(default_factory=dict)


class ModuleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    order: int | None = None
    estimated_hours: int | None = None
    learning_outcomes: list[str] | None = None
    config: dict | None = None


class UnitCreate(BaseModel):
    task_id: int
    unit_order: int = 0
    is_required: bool = True


class UnitUpdate(BaseModel):
    unit_order: int | None = None
    is_required: bool | None = None


class ReorderItem(BaseModel):
    id: int
    order: int
```

- [ ] **Step 2: Smoke import**

Run: `docker compose exec backend python -c "import schemas_admin; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add backend/schemas_admin.py
git commit -m "feat(schemas): admin content Pydantic schemas"
```

---

# Phase 2 — Utilities

### Task 4: Slug-утилита

**Files:**
- Create: `backend/services/slug.py`
- Test: `backend/tests/test_slug.py`

- [ ] **Step 1: Написать тест**

```python
import pytest

from services.slug import slugify, is_valid_slug


@pytest.mark.parametrize("given,expected", [
    ("Hello World", "hello-world"),
    ("Что такое SAST", "chto-takoe-sast"),
    ("Gitleaks — первый запуск", "gitleaks-pervyy-zapusk"),
    ("Lab 1: Найди секреты", "lab-1-naydi-sekrety"),
    ("  spaces   ", "spaces"),
    ("!!!", ""),
])
def test_slugify(given, expected):
    assert slugify(given) == expected


@pytest.mark.parametrize("slug,ok", [
    ("foo", True),
    ("foo-bar-2", True),
    ("a" * 100, True),
    ("A", False),          # uppercase
    ("foo_bar", False),    # underscore
    ("a", False),          # too short
    ("a" * 101, False),    # too long
    ("foo bar", False),    # space
])
def test_is_valid_slug(slug, ok):
    assert is_valid_slug(slug) is ok
```

- [ ] **Step 2: Запустить, убедиться что падает**

Run: `docker compose exec backend pytest tests/test_slug.py -v`
Expected: FAIL — `ModuleNotFoundError: services.slug`

- [ ] **Step 3: Реализация**

```python
"""Slug generation and validation.

Handles Cyrillic via a minimal transliteration table — достаточно для русских title'ов
контента. Если встретится другой алфавит (китайский, арабский) — добавить позже.
"""
import re

_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}

_SLUG_RE = re.compile(r"^[a-z0-9-]{2,100}$")


def slugify(text: str) -> str:
    text = text.strip().lower()
    out = []
    for ch in text:
        if ch in _TRANSLIT:
            out.append(_TRANSLIT[ch])
        elif ch.isalnum() and ch.isascii():
            out.append(ch)
        elif ch in " -_":
            out.append("-")
        # прочее (пунктуация, эмодзи) — выкидываем
    result = "".join(out)
    # сжать серии дефисов и обрезать
    result = re.sub(r"-+", "-", result).strip("-")
    return result[:100]


def is_valid_slug(slug: str) -> bool:
    return bool(_SLUG_RE.match(slug))
```

- [ ] **Step 4: Прогнать тесты**

Run: `docker compose exec backend pytest tests/test_slug.py -v`
Expected: все PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/services/slug.py backend/tests/test_slug.py
git commit -m "feat(services): slug generator and validator"
```

---

### Task 5: Flag-hashing утилита

**Files:**
- Create: `backend/services/flag_hash.py`
- Test: `backend/tests/test_flag_hash.py`

- [ ] **Step 1: Тест**

```python
from services.flag_hash import hash_flag, apply_flag_to_config


def test_hash_flag_is_sha256_hex():
    h = hash_flag("FLAG{secret}")
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_hash_flag_deterministic():
    assert hash_flag("x") == hash_flag("x")
    assert hash_flag("x") != hash_flag("y")


def test_apply_flag_to_config_replaces_plaintext_with_hash():
    cfg = {"docker_image": "a", "flag": "FLAG{abc}"}
    out = apply_flag_to_config(cfg)
    assert "flag" not in out
    assert out["flag_hash"] == hash_flag("FLAG{abc}")
    assert out["docker_image"] == "a"


def test_apply_flag_to_config_preserves_existing_hash_if_no_plaintext():
    cfg = {"docker_image": "a", "flag_hash": "deadbeef" * 8}
    out = apply_flag_to_config(cfg)
    assert out["flag_hash"] == "deadbeef" * 8
    assert "flag" not in out


def test_apply_flag_to_config_plaintext_takes_precedence():
    cfg = {"flag": "new", "flag_hash": "old"}
    out = apply_flag_to_config(cfg)
    assert out["flag_hash"] == hash_flag("new")
```

- [ ] **Step 2: Реализация**

```python
"""SHA256-хэширование флагов для CTF/ssh_lab.

Plaintext `flag` в API — write-only: при сохранении заменяется на `flag_hash`,
plaintext нигде не остаётся (ни в БД, ни в логах, ни в ответах API).
"""
import hashlib


def hash_flag(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode()).hexdigest()


def apply_flag_to_config(config: dict) -> dict:
    """Вернуть новый config: если есть plaintext `flag` — хэшировать и выбросить plaintext."""
    out = dict(config)
    plaintext = out.pop("flag", None)
    if plaintext:
        out["flag_hash"] = hash_flag(plaintext)
    return out
```

- [ ] **Step 3: Прогнать**

Run: `docker compose exec backend pytest tests/test_flag_hash.py -v`
Expected: 4 PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/services/flag_hash.py backend/tests/test_flag_hash.py
git commit -m "feat(services): SHA256 flag hashing helper"
```

---

### Task 6: Добавить pyyaml и создать bundle-сервис (скелет)

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/services/bundle.py`

- [ ] **Step 1: Проверить, есть ли уже pyyaml**

Run: `grep -i yaml backend/requirements.txt`
Expected: если пусто — добавить. Если есть — пропустить следующий шаг.

- [ ] **Step 2: Добавить зависимость (если отсутствует)**

В `backend/requirements.txt` добавить строку:

```
PyYAML==6.0.2
```

- [ ] **Step 3: Создать скелет bundle.py**

```python
"""ZIP-бандлы для экспорта/импорта тасков и курсов.

Формат:
- task bundle: zip с `manifest.yaml`
- course bundle: zip с `course.yaml` и, при bundle=true, `tasks/{slug}.yaml`

Импорт защищён от zip-slip (отказ на `..` и абсолютные пути) и лимитом 10 MB.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import PurePosixPath

import yaml

MAX_BUNDLE_BYTES = 10 * 1024 * 1024


class BundleError(ValueError):
    pass


def _safe_name(name: str) -> str:
    """Принимает имя файла внутри архива, отказывает на попытках выхода за пределы."""
    p = PurePosixPath(name)
    if p.is_absolute() or ".." in p.parts:
        raise BundleError(f"unsafe path in bundle: {name}")
    return str(p)


def read_yaml(zf: zipfile.ZipFile, name: str) -> dict:
    safe = _safe_name(name)
    with zf.open(safe) as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise BundleError(f"{name}: expected YAML mapping")
    return data


def list_task_files(zf: zipfile.ZipFile) -> list[str]:
    """Список файлов под tasks/ в бандле курса. Каждое имя проверяется."""
    out = []
    for info in zf.infolist():
        if info.is_dir():
            continue
        safe = _safe_name(info.filename)
        if safe.startswith("tasks/") and safe.endswith(".yaml"):
            out.append(safe)
    return out


def open_bundle(raw: bytes) -> zipfile.ZipFile:
    if len(raw) > MAX_BUNDLE_BYTES:
        raise BundleError(f"bundle too large ({len(raw)} > {MAX_BUNDLE_BYTES})")
    try:
        return zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile as e:
        raise BundleError(f"not a valid zip: {e}")


def pack_task(manifest: dict) -> bytes:
    """Создать zip с одним manifest.yaml."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.yaml", yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False))
    return buf.getvalue()


def pack_course(course: dict, tasks: dict[str, dict] | None = None) -> bytes:
    """Создать zip с course.yaml и опционально tasks/{slug}.yaml."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("course.yaml", yaml.safe_dump(course, allow_unicode=True, sort_keys=False))
        for slug, task in (tasks or {}).items():
            zf.writestr(f"tasks/{slug}.yaml", yaml.safe_dump(task, allow_unicode=True, sort_keys=False))
    return buf.getvalue()
```

- [ ] **Step 4: Пересобрать backend с новой зависимостью**

Run: `docker compose up -d --build backend && sleep 3 && docker compose exec backend python -c "import yaml, services.bundle; print('ok')"`
Expected: `ok`.

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt backend/services/bundle.py
git commit -m "feat(services): ZIP bundle packer/unpacker skeleton"
```

---

### Task 7: Zip-slip тест

**Files:**
- Create: `backend/tests/test_bundle.py`

- [ ] **Step 1: Тест**

```python
import io
import zipfile

import pytest

from services.bundle import BundleError, open_bundle, pack_task, read_yaml


def test_pack_task_roundtrip():
    raw = pack_task({"slug": "x", "title": "X"})
    zf = open_bundle(raw)
    data = read_yaml(zf, "manifest.yaml")
    assert data == {"slug": "x", "title": "X"}


def test_zipslip_rejected():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../evil.yaml", "slug: x")
    zf = open_bundle(buf.getvalue())
    with pytest.raises(BundleError, match="unsafe"):
        read_yaml(zf, "../evil.yaml")


def test_size_limit():
    big = b"x" * (10 * 1024 * 1024 + 1)
    with pytest.raises(BundleError, match="too large"):
        open_bundle(big)


def test_not_a_zip():
    with pytest.raises(BundleError, match="not a valid zip"):
        open_bundle(b"not a zip")
```

- [ ] **Step 2: Прогнать**

Run: `docker compose exec backend pytest tests/test_bundle.py -v`
Expected: 4 PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_bundle.py
git commit -m "test(bundle): zip-slip, size limit, roundtrip"
```

---

# Phase 3 — Admin router scaffold + auth

### Task 8: Создать пустой роутер admin_content с проверкой прав

**Files:**
- Create: `backend/routers/admin_content.py`
- Create: `backend/tests/test_admin_content_auth.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Тест прав**

```python
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from auth import create_token, hash_password
from database import async_session, engine
from main import app
from models import User, UserRole

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
async def _dispose_engine():
    await engine.dispose()
    yield
    await engine.dispose()


async def _mk_user(role: UserRole) -> tuple[int, str]:
    async with async_session() as db:
        u = User(
            username=f"t-{uuid.uuid4().hex[:8]}",
            password_hash=hash_password("x"),
            role=role,
        )
        db.add(u)
        await db.commit()
        await db.refresh(u)
        return u.id, create_token(u.id, role.value)


async def test_admin_content_requires_admin():
    _, student_token = await _mk_user(UserRole.student)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/admin/content/courses",
                        headers={"Authorization": f"Bearer {student_token}"})
        assert r.status_code == 403


async def test_admin_content_admin_ok():
    _, admin_token = await _mk_user(UserRole.admin)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/admin/content/courses",
                        headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200
```

- [ ] **Step 2: Запустить — должен упасть (роутер не подключён)**

Run: `docker compose exec backend pytest tests/test_admin_content_auth.py -v`
Expected: 404 или 403 на admin-токен, т.к. роутер отсутствует → FAIL.

- [ ] **Step 3: Создать роутер-заглушку**

`backend/routers/admin_content.py`:

```python
"""Admin CRUD for courses, modules, units, tasks + import/export.

Защищён require_admin. Все endpoints под /api/admin/content.
"""
from fastapi import APIRouter, Depends

from auth import require_admin

router = APIRouter(
    prefix="/api/admin/content",
    tags=["admin-content"],
    dependencies=[Depends(require_admin)],
)


@router.get("/courses")
async def list_courses_admin():
    return []
```

- [ ] **Step 4: Подключить роутер в main.py**

В `backend/main.py`, после строки `from routers import admin, ...`:

```python
from routers import admin, admin_content, auth_router, courses, ctf, gitlab_tasks, progress, quiz, tasks, tracks
```

И после `app.include_router(tracks.router)`:

```python
app.include_router(admin_content.router)
```

- [ ] **Step 5: Перезапустить + прогнать**

Run: `docker compose restart backend && sleep 3 && docker compose exec backend pytest tests/test_admin_content_auth.py -v`
Expected: 2 PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/routers/admin_content.py backend/main.py backend/tests/test_admin_content_auth.py
git commit -m "feat(admin): content router scaffold with admin-only guard"
```

---

# Phase 4 — Tasks CRUD

### Task 9: POST /tasks — создание таска

**Files:**
- Modify: `backend/routers/admin_content.py`
- Create: `backend/tests/test_admin_content_tasks.py`

- [ ] **Step 1: Тест create**

```python
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from auth import create_token, hash_password
from database import async_session, engine
from main import app
from models import User, UserRole

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
async def _dispose_engine():
    await engine.dispose()
    yield
    await engine.dispose()


async def _admin_token() -> str:
    async with async_session() as db:
        u = User(username=f"a-{uuid.uuid4().hex[:6]}",
                 password_hash=hash_password("x"), role=UserRole.admin)
        db.add(u)
        await db.commit()
        await db.refresh(u)
        return create_token(u.id, "admin")


async def test_create_theory_task():
    token = await _admin_token()
    suffix = uuid.uuid4().hex[:6]
    body = {
        "slug": f"theory-{suffix}",
        "title": "Theory T",
        "description": "d",
        "order": 1,
        "type": "theory",
        "config": {"content_kind": "text", "content": "# hi"},
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/admin/content/tasks", json=body,
                         headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 201, r.text
        out = r.json()
        assert out["slug"] == body["slug"]
        assert out["type"] == "theory"
        assert out["config"]["content_kind"] == "text"
        assert out["id"] > 0


async def test_create_ctf_task_hashes_plaintext_flag():
    token = await _admin_token()
    suffix = uuid.uuid4().hex[:6]
    body = {
        "slug": f"ctf-{suffix}",
        "title": "Ctf",
        "type": "ctf",
        "config": {
            "docker_image": "myuser/img:1",
            "port": 5000,
            "ttl_minutes": 60,
            "difficulty": "easy",
            "flag": "FLAG{secret}",
        },
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/admin/content/tasks", json=body,
                         headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 201, r.text
        cfg = r.json()["config"]
        assert "flag" not in cfg  # plaintext not echoed
        assert len(cfg["flag_hash"]) == 64


async def test_create_task_invalid_slug():
    token = await _admin_token()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/admin/content/tasks",
                         json={"slug": "UPPER", "title": "x", "type": "theory", "config": {}},
                         headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 422


async def test_create_task_duplicate_slug_409():
    token = await _admin_token()
    slug = f"dup-{uuid.uuid4().hex[:6]}"
    body = {"slug": slug, "title": "x", "type": "theory", "config": {}}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r1 = await c.post("/api/admin/content/tasks", json=body,
                          headers={"Authorization": f"Bearer {token}"})
        assert r1.status_code == 201
        r2 = await c.post("/api/admin/content/tasks", json=body,
                          headers={"Authorization": f"Bearer {token}"})
        assert r2.status_code == 409
```

- [ ] **Step 2: Запустить — упадёт (эндпоинта нет)**

Run: `docker compose exec backend pytest tests/test_admin_content_tasks.py -v`
Expected: 4 FAIL / ERROR.

- [ ] **Step 3: Реализовать POST /tasks**

В `backend/routers/admin_content.py` добавить импорты и эндпоинт:

```python
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Task, TaskType, User
from schemas_admin import TaskCreate, TaskOutAdmin
from services.flag_hash import apply_flag_to_config


def _task_out(task: Task, usage: list[dict] | None = None) -> dict:
    return {
        "id": task.id,
        "slug": task.slug,
        "title": task.title,
        "description": task.description or "",
        "order": task.order,
        "type": task.type,
        "config": task.config or {},
        "author_id": task.author_id,
        "updated_at": task.updated_at,
        "usage": usage or [],
    }


@router.post("/tasks", status_code=status.HTTP_201_CREATED, response_model=TaskOutAdmin)
async def create_task(
    body: TaskCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    config = apply_flag_to_config(body.config or {})
    task = Task(
        slug=body.slug,
        title=body.title,
        description=body.description,
        order=body.order,
        type=body.type,
        config=config,
        author_id=admin.id,
    )
    db.add(task)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Slug already exists")
    await db.refresh(task)
    return _task_out(task)
```

Заменить строку `dependencies=[Depends(require_admin)],` — оставляем как есть, но конкретный эндпоинт тоже имеет `Depends(require_admin)` чтобы получить `admin.id`.

- [ ] **Step 4: Прогнать**

Run: `docker compose exec backend pytest tests/test_admin_content_tasks.py -v`
Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/routers/admin_content.py backend/tests/test_admin_content_tasks.py
git commit -m "feat(admin): POST /tasks with validation and flag hashing"
```

---

### Task 10: GET /tasks — список с фильтрами

**Files:**
- Modify: `backend/routers/admin_content.py`
- Modify: `backend/tests/test_admin_content_tasks.py`

- [ ] **Step 1: Тест list**

В тот же файл добавить:

```python
async def test_list_tasks_filter_by_type():
    token = await _admin_token()
    suffix = uuid.uuid4().hex[:6]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post("/api/admin/content/tasks",
                     json={"slug": f"th-{suffix}", "title": "T", "type": "theory", "config": {}},
                     headers={"Authorization": f"Bearer {token}"})
        await c.post("/api/admin/content/tasks",
                     json={"slug": f"qz-{suffix}", "title": "Q", "type": "quiz", "config": {}},
                     headers={"Authorization": f"Bearer {token}"})

        r = await c.get("/api/admin/content/tasks?type=theory",
                        headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        slugs = [t["slug"] for t in r.json()]
        assert f"th-{suffix}" in slugs
        assert f"qz-{suffix}" not in slugs


async def test_list_tasks_search_by_title():
    token = await _admin_token()
    unique = f"NEEDLE-{uuid.uuid4().hex[:6]}"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post("/api/admin/content/tasks",
                     json={"slug": unique.lower(), "title": unique, "type": "theory", "config": {}},
                     headers={"Authorization": f"Bearer {token}"})
        r = await c.get(f"/api/admin/content/tasks?search={unique}",
                        headers={"Authorization": f"Bearer {token}"})
        titles = [t["title"] for t in r.json()]
        assert unique in titles
```

- [ ] **Step 2: Запустить — падает**

Run: `docker compose exec backend pytest tests/test_admin_content_tasks.py::test_list_tasks_filter_by_type tests/test_admin_content_tasks.py::test_list_tasks_search_by_title -v`
Expected: FAIL (пустой list, или падение).

- [ ] **Step 3: Реализовать GET /tasks**

Добавить в `admin_content.py`:

```python
from sqlalchemy import or_

from models import ModuleUnit


@router.get("/tasks", response_model=list[TaskOutAdmin])
async def list_tasks(
    type: TaskType | None = None,
    search: str | None = None,
    unused: bool = False,
    db: AsyncSession = Depends(get_db),
):
    q = select(Task)
    if type is not None:
        q = q.where(Task.type == type)
    if search:
        like = f"%{search}%"
        q = q.where(or_(Task.title.ilike(like), Task.slug.ilike(like)))
    if unused:
        used_ids = select(ModuleUnit.task_id).distinct()
        q = q.where(Task.id.notin_(used_ids))
    q = q.order_by(Task.updated_at.desc())
    result = await db.execute(q)
    return [_task_out(t) for t in result.scalars().all()]
```

- [ ] **Step 4: Прогнать все тесты tasks**

Run: `docker compose exec backend pytest tests/test_admin_content_tasks.py -v`
Expected: все PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/routers/admin_content.py backend/tests/test_admin_content_tasks.py
git commit -m "feat(admin): GET /tasks with type/search/unused filters"
```

---

### Task 11: GET /tasks/{id} — детали с usage

**Files:**
- Modify: `backend/routers/admin_content.py`
- Modify: `backend/tests/test_admin_content_tasks.py`

- [ ] **Step 1: Тест**

```python
from models import Course, Module, ModuleUnit


async def test_get_task_detail_with_usage():
    token = await _admin_token()
    suffix = uuid.uuid4().hex[:6]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        cr = await c.post("/api/admin/content/tasks",
                          json={"slug": f"used-{suffix}", "title": "U", "type": "theory", "config": {}},
                          headers={"Authorization": f"Bearer {token}"})
        task_id = cr.json()["id"]

    # привязать к курсу/модулю/юниту напрямую через БД
    async with async_session() as db:
        course = Course(slug=f"c-{suffix}", title="C", order=0, config={})
        db.add(course)
        await db.commit()
        await db.refresh(course)
        module = Module(course_id=course.id, title="M", order=1, learning_outcomes=[], config={})
        db.add(module)
        await db.commit()
        await db.refresh(module)
        unit = ModuleUnit(module_id=module.id, task_id=task_id, unit_order=1, is_required=True)
        db.add(unit)
        await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"/api/admin/content/tasks/{task_id}",
                        headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        body = r.json()
        assert len(body["usage"]) == 1
        assert body["usage"][0]["course_slug"] == f"c-{suffix}"


async def test_get_task_404():
    token = await _admin_token()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/admin/content/tasks/999999",
                        headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 404
```

- [ ] **Step 2: Реализовать**

```python
from models import Course, Module

async def _usage_for_task(task_id: int, db: AsyncSession) -> list[dict]:
    rows = await db.execute(
        select(Course.id, Course.slug, Module.id, ModuleUnit.id)
        .join(Module, Module.course_id == Course.id)
        .join(ModuleUnit, ModuleUnit.module_id == Module.id)
        .where(ModuleUnit.task_id == task_id)
    )
    return [
        {"course_id": c_id, "course_slug": c_slug, "module_id": m_id, "unit_id": u_id}
        for c_id, c_slug, m_id, u_id in rows.all()
    ]


@router.get("/tasks/{task_id}", response_model=TaskOutAdmin)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return _task_out(task, usage=await _usage_for_task(task_id, db))
```

- [ ] **Step 3: Прогнать**

Run: `docker compose exec backend pytest tests/test_admin_content_tasks.py -v`
Expected: все PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/routers/admin_content.py backend/tests/test_admin_content_tasks.py
git commit -m "feat(admin): GET /tasks/{id} with usage info"
```

---

### Task 12: PATCH /tasks/{id}

**Files:**
- Modify: `backend/routers/admin_content.py`
- Modify: `backend/tests/test_admin_content_tasks.py`

- [ ] **Step 1: Тест**

```python
async def test_patch_task_updates_fields_and_hashes_flag():
    token = await _admin_token()
    suffix = uuid.uuid4().hex[:6]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        cr = await c.post("/api/admin/content/tasks",
                          json={"slug": f"p-{suffix}", "title": "Before", "type": "ctf",
                                "config": {"docker_image": "a", "flag_hash": "old"}},
                          headers={"Authorization": f"Bearer {token}"})
        tid = cr.json()["id"]
        r = await c.patch(f"/api/admin/content/tasks/{tid}",
                          json={"title": "After",
                                "config": {"docker_image": "a", "flag": "newflag"}},
                          headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        out = r.json()
        assert out["title"] == "After"
        assert "flag" not in out["config"]
        assert out["config"]["flag_hash"] != "old"
```

- [ ] **Step 2: Реализовать**

```python
from schemas_admin import TaskUpdate


@router.patch("/tasks/{task_id}", response_model=TaskOutAdmin)
async def update_task(
    task_id: int,
    body: TaskUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    data = body.model_dump(exclude_unset=True)
    if "config" in data:
        data["config"] = apply_flag_to_config(data["config"])
    for field, value in data.items():
        setattr(task, field, value)
    task.author_id = admin.id
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Slug already exists")
    await db.refresh(task)
    return _task_out(task, usage=await _usage_for_task(task_id, db))
```

- [ ] **Step 3: Прогнать + commit**

Run: `docker compose exec backend pytest tests/test_admin_content_tasks.py -v` → PASS.

```bash
git add backend/routers/admin_content.py backend/tests/test_admin_content_tasks.py
git commit -m "feat(admin): PATCH /tasks/{id}"
```

---

### Task 13: DELETE /tasks/{id} — 409 если used

**Files:**
- Modify: `backend/routers/admin_content.py`
- Modify: `backend/tests/test_admin_content_tasks.py`

- [ ] **Step 1: Тест**

```python
async def test_delete_task_used_returns_409_with_usage():
    token = await _admin_token()
    suffix = uuid.uuid4().hex[:6]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        cr = await c.post("/api/admin/content/tasks",
                          json={"slug": f"del-{suffix}", "title": "D", "type": "theory", "config": {}},
                          headers={"Authorization": f"Bearer {token}"})
        tid = cr.json()["id"]

    async with async_session() as db:
        course = Course(slug=f"cd-{suffix}", title="C", order=0, config={})
        db.add(course); await db.commit(); await db.refresh(course)
        module = Module(course_id=course.id, title="M", order=1, learning_outcomes=[], config={})
        db.add(module); await db.commit(); await db.refresh(module)
        db.add(ModuleUnit(module_id=module.id, task_id=tid, unit_order=1, is_required=True))
        await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.delete(f"/api/admin/content/tasks/{tid}",
                           headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 409
        assert len(r.json()["detail"]["usage"]) == 1


async def test_delete_task_unused_ok():
    token = await _admin_token()
    suffix = uuid.uuid4().hex[:6]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        cr = await c.post("/api/admin/content/tasks",
                          json={"slug": f"free-{suffix}", "title": "F", "type": "theory", "config": {}},
                          headers={"Authorization": f"Bearer {token}"})
        tid = cr.json()["id"]
        r = await c.delete(f"/api/admin/content/tasks/{tid}",
                           headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 204
        r2 = await c.get(f"/api/admin/content/tasks/{tid}",
                         headers={"Authorization": f"Bearer {token}"})
        assert r2.status_code == 404
```

- [ ] **Step 2: Реализовать**

```python
@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    usage = await _usage_for_task(task_id, db)
    if usage:
        raise HTTPException(status_code=409, detail={"message": "Task is in use", "usage": usage})
    await db.delete(task)
    await db.commit()
```

- [ ] **Step 3: Прогнать + commit**

```bash
docker compose exec backend pytest tests/test_admin_content_tasks.py -v
git add backend/routers/admin_content.py backend/tests/test_admin_content_tasks.py
git commit -m "feat(admin): DELETE /tasks/{id} blocked when task is in use"
```

---

# Phase 5 — Courses CRUD

### Task 14: POST / GET / PATCH / DELETE courses + is_visible

**Files:**
- Modify: `backend/routers/admin_content.py`
- Create: `backend/tests/test_admin_content_courses.py`

- [ ] **Step 1: Тесты (все операции сразу — один домен)**

```python
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from auth import create_token, hash_password
from database import async_session, engine
from main import app
from models import Course, User, UserRole

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
async def _dispose_engine():
    await engine.dispose()
    yield
    await engine.dispose()


async def _admin_token():
    async with async_session() as db:
        u = User(username=f"a-{uuid.uuid4().hex[:6]}",
                 password_hash=hash_password("x"), role=UserRole.admin)
        db.add(u); await db.commit(); await db.refresh(u)
        return create_token(u.id, "admin")


async def test_create_course_defaults_to_hidden():
    token = await _admin_token()
    suffix = uuid.uuid4().hex[:6]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/admin/content/courses",
                         json={"slug": f"c-{suffix}", "title": "C", "order": 1, "config": {}},
                         headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 201
        assert r.json()["is_visible"] is False


async def test_patch_course_toggle_visibility():
    token = await _admin_token()
    suffix = uuid.uuid4().hex[:6]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        cr = await c.post("/api/admin/content/courses",
                          json={"slug": f"v-{suffix}", "title": "V"},
                          headers={"Authorization": f"Bearer {token}"})
        cid = cr.json()["id"]
        r = await c.patch(f"/api/admin/content/courses/{cid}",
                          json={"is_visible": True},
                          headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["is_visible"] is True


async def test_delete_visible_course_blocked():
    token = await _admin_token()
    suffix = uuid.uuid4().hex[:6]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        cr = await c.post("/api/admin/content/courses",
                          json={"slug": f"del-{suffix}", "title": "D"},
                          headers={"Authorization": f"Bearer {token}"})
        cid = cr.json()["id"]
        # сразу делаем видимым и пытаемся удалить
        await c.patch(f"/api/admin/content/courses/{cid}", json={"is_visible": True},
                      headers={"Authorization": f"Bearer {token}"})
        r = await c.delete(f"/api/admin/content/courses/{cid}",
                           headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 409


async def test_delete_hidden_course_ok():
    token = await _admin_token()
    suffix = uuid.uuid4().hex[:6]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        cr = await c.post("/api/admin/content/courses",
                          json={"slug": f"hid-{suffix}", "title": "H"},
                          headers={"Authorization": f"Bearer {token}"})
        cid = cr.json()["id"]
        r = await c.delete(f"/api/admin/content/courses/{cid}",
                           headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 204
```

- [ ] **Step 2: Реализовать**

В `admin_content.py` добавить:

```python
from models import Course, Module, ModuleUnit
from schemas_admin import CourseCreate, CourseUpdate


class CourseOutAdmin(BaseModel):
    id: int
    slug: str
    title: str
    description: str
    order: int
    config: dict
    is_visible: bool

    model_config = ConfigDict(from_attributes=True)
```

(импортировать `BaseModel, ConfigDict` из pydantic)

```python
@router.post("/courses", status_code=201, response_model=CourseOutAdmin)
async def create_course(body: CourseCreate, db: AsyncSession = Depends(get_db)):
    course = Course(
        slug=body.slug, title=body.title, description=body.description,
        order=body.order, config=body.config, is_visible=False,
    )
    db.add(course)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Slug already exists")
    await db.refresh(course)
    return course


@router.get("/courses", response_model=list[CourseOutAdmin])
async def list_courses_admin(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(select(Course).order_by(Course.order, Course.id))
    return rows.scalars().all()


@router.patch("/courses/{course_id}", response_model=CourseOutAdmin)
async def update_course(course_id: int, body: CourseUpdate,
                         db: AsyncSession = Depends(get_db)):
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(course, k, v)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Slug already exists")
    await db.refresh(course)
    return course


@router.delete("/courses/{course_id}", status_code=204)
async def delete_course(course_id: int, db: AsyncSession = Depends(get_db)):
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    if course.is_visible:
        raise HTTPException(409, "Course must be hidden before deletion")
    await db.delete(course)
    await db.commit()
```

- [ ] **Step 3: Прогнать + commit**

```bash
docker compose exec backend pytest tests/test_admin_content_courses.py -v
git add backend/routers/admin_content.py backend/tests/test_admin_content_courses.py
git commit -m "feat(admin): courses CRUD with visibility guard"
```

---

### Task 15: POST/PATCH/DELETE modules + units + reorder

**Files:**
- Modify: `backend/routers/admin_content.py`
- Create: `backend/tests/test_admin_content_modules.py`

- [ ] **Step 1: Тесты**

```python
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from auth import create_token, hash_password
from database import async_session, engine
from main import app
from models import User, UserRole

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
async def _dispose_engine():
    await engine.dispose()
    yield
    await engine.dispose()


async def _setup_course_with_task():
    async with async_session() as db:
        u = User(username=f"a-{uuid.uuid4().hex[:6]}",
                 password_hash=hash_password("x"), role=UserRole.admin)
        db.add(u); await db.commit(); await db.refresh(u)
    token = create_token(u.id, "admin")
    suffix = uuid.uuid4().hex[:6]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = {"Authorization": f"Bearer {token}"}
        cr = await c.post("/api/admin/content/courses",
                          json={"slug": f"c-{suffix}", "title": "C"}, headers=h)
        cid = cr.json()["id"]
        tr = await c.post("/api/admin/content/tasks",
                          json={"slug": f"t-{suffix}", "title": "T",
                                "type": "theory", "config": {}},
                          headers=h)
        tid = tr.json()["id"]
    return token, cid, tid


async def test_module_unit_lifecycle():
    token, cid, tid = await _setup_course_with_task()
    h = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        mr = await c.post(f"/api/admin/content/courses/{cid}/modules",
                          json={"title": "M1", "order": 1}, headers=h)
        assert mr.status_code == 201
        mid = mr.json()["id"]

        ur = await c.post(f"/api/admin/content/modules/{mid}/units",
                          json={"task_id": tid, "unit_order": 1, "is_required": True},
                          headers=h)
        assert ur.status_code == 201
        uid = ur.json()["id"]

        # patch module
        pm = await c.patch(f"/api/admin/content/modules/{mid}",
                           json={"title": "M1-new", "estimated_hours": 2}, headers=h)
        assert pm.status_code == 200
        assert pm.json()["title"] == "M1-new"

        # patch unit
        pu = await c.patch(f"/api/admin/content/units/{uid}",
                           json={"is_required": False}, headers=h)
        assert pu.json()["is_required"] is False

        # delete unit
        du = await c.delete(f"/api/admin/content/units/{uid}", headers=h)
        assert du.status_code == 204

        # delete module
        dm = await c.delete(f"/api/admin/content/modules/{mid}", headers=h)
        assert dm.status_code == 204


async def test_reorder_modules():
    token, cid, tid = await _setup_course_with_task()
    h = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        m1 = (await c.post(f"/api/admin/content/courses/{cid}/modules",
                           json={"title": "A", "order": 1}, headers=h)).json()
        m2 = (await c.post(f"/api/admin/content/courses/{cid}/modules",
                           json={"title": "B", "order": 2}, headers=h)).json()

        r = await c.post(f"/api/admin/content/courses/{cid}/reorder-modules",
                         json=[{"id": m1["id"], "order": 2},
                               {"id": m2["id"], "order": 1}], headers=h)
        assert r.status_code == 200

        # verify through student course detail
        # (list_courses_admin сортирует по order)
        lst = await c.get("/api/admin/content/courses", headers=h)
        # Порядок модулей наружу админ-list не отдаёт — проверим напрямую
        from sqlalchemy import select
        from models import Module
        async with async_session() as db:
            rows = await db.execute(
                select(Module.id, Module.order).where(Module.course_id == cid).order_by(Module.order)
            )
            pairs = list(rows.all())
        assert pairs[0][0] == m2["id"]
        assert pairs[1][0] == m1["id"]
```

- [ ] **Step 2: Реализовать**

Добавить в `admin_content.py`:

```python
from schemas_admin import ModuleCreate, ModuleUpdate, UnitCreate, UnitUpdate, ReorderItem


class ModuleOutAdmin(BaseModel):
    id: int
    course_id: int
    title: str
    description: str
    order: int
    estimated_hours: int | None
    learning_outcomes: list[str]
    config: dict

    model_config = ConfigDict(from_attributes=True)


class UnitOutAdmin(BaseModel):
    id: int
    module_id: int
    task_id: int
    unit_order: int
    is_required: bool

    model_config = ConfigDict(from_attributes=True)


@router.post("/courses/{course_id}/modules", status_code=201, response_model=ModuleOutAdmin)
async def create_module(course_id: int, body: ModuleCreate,
                         db: AsyncSession = Depends(get_db)):
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    m = Module(course_id=course_id, **body.model_dump())
    db.add(m)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Duplicate module order in this course")
    await db.refresh(m)
    return m


@router.patch("/modules/{module_id}", response_model=ModuleOutAdmin)
async def update_module(module_id: int, body: ModuleUpdate,
                         db: AsyncSession = Depends(get_db)):
    m = await db.get(Module, module_id)
    if not m:
        raise HTTPException(404, "Module not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(m, k, v)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Duplicate module order")
    await db.refresh(m)
    return m


@router.delete("/modules/{module_id}", status_code=204)
async def delete_module(module_id: int, db: AsyncSession = Depends(get_db)):
    m = await db.get(Module, module_id)
    if not m:
        raise HTTPException(404, "Module not found")
    await db.delete(m)
    await db.commit()


@router.post("/courses/{course_id}/reorder-modules")
async def reorder_modules(course_id: int, items: list[ReorderItem],
                           db: AsyncSession = Depends(get_db)):
    # Пишем временные значения, потом финальные — чтобы обойти UNIQUE(course_id, order)
    rows = await db.execute(select(Module).where(Module.course_id == course_id))
    by_id = {m.id: m for m in rows.scalars().all()}
    for i, it in enumerate(items):
        m = by_id.get(it.id)
        if not m:
            raise HTTPException(400, f"Module {it.id} not in course {course_id}")
        m.order = -(i + 1)  # temp negative
    await db.flush()
    for it in items:
        by_id[it.id].order = it.order
    await db.commit()
    return {"ok": True}


@router.post("/modules/{module_id}/units", status_code=201, response_model=UnitOutAdmin)
async def create_unit(module_id: int, body: UnitCreate,
                       db: AsyncSession = Depends(get_db)):
    m = await db.get(Module, module_id)
    if not m:
        raise HTTPException(404, "Module not found")
    task = await db.get(Task, body.task_id)
    if not task:
        raise HTTPException(400, f"Task {body.task_id} not found")
    u = ModuleUnit(module_id=module_id, **body.model_dump())
    db.add(u)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Task already in this module")
    await db.refresh(u)
    return u


@router.patch("/units/{unit_id}", response_model=UnitOutAdmin)
async def update_unit(unit_id: int, body: UnitUpdate,
                       db: AsyncSession = Depends(get_db)):
    u = await db.get(ModuleUnit, unit_id)
    if not u:
        raise HTTPException(404, "Unit not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(u, k, v)
    await db.commit()
    await db.refresh(u)
    return u


@router.delete("/units/{unit_id}", status_code=204)
async def delete_unit(unit_id: int, db: AsyncSession = Depends(get_db)):
    u = await db.get(ModuleUnit, unit_id)
    if not u:
        raise HTTPException(404, "Unit not found")
    await db.delete(u)
    await db.commit()


@router.post("/modules/{module_id}/reorder-units")
async def reorder_units(module_id: int, items: list[ReorderItem],
                         db: AsyncSession = Depends(get_db)):
    rows = await db.execute(select(ModuleUnit).where(ModuleUnit.module_id == module_id))
    by_id = {u.id: u for u in rows.scalars().all()}
    for i, it in enumerate(items):
        u = by_id.get(it.id)
        if not u:
            raise HTTPException(400, f"Unit {it.id} not in module {module_id}")
        u.unit_order = -(i + 1)
    await db.flush()
    for it in items:
        by_id[it.id].unit_order = it.order
    await db.commit()
    return {"ok": True}
```

- [ ] **Step 3: Прогнать + commit**

```bash
docker compose exec backend pytest tests/test_admin_content_modules.py -v
git add backend/routers/admin_content.py backend/tests/test_admin_content_modules.py
git commit -m "feat(admin): modules/units CRUD with reorder"
```

---

### Task 16: Student /api/courses фильтрует по is_visible

**Files:**
- Modify: `backend/routers/courses.py`
- Create: `backend/tests/test_courses_visibility.py`

- [ ] **Step 1: Тест**

```python
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from auth import create_token, hash_password
from database import async_session, engine
from main import app
from models import Course, User, UserRole

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
async def _dispose_engine():
    await engine.dispose()
    yield
    await engine.dispose()


async def test_student_sees_only_visible_courses():
    suffix = uuid.uuid4().hex[:6]
    async with async_session() as db:
        student = User(username=f"s-{suffix}", password_hash=hash_password("x"),
                       role=UserRole.student)
        db.add(student)
        db.add(Course(slug=f"hid-{suffix}", title="H", is_visible=False, order=100, config={}))
        db.add(Course(slug=f"vis-{suffix}", title="V", is_visible=True, order=101, config={}))
        await db.commit()
        await db.refresh(student)
    token = create_token(student.id, "student")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/courses",
                        headers={"Authorization": f"Bearer {token}"})
        slugs = [x["slug"] for x in r.json()]
        assert f"vis-{suffix}" in slugs
        assert f"hid-{suffix}" not in slugs
```

- [ ] **Step 2: Модифицировать `_load_course_query`**

В `backend/routers/courses.py`, заменить `_load_course_query`:

```python
def _load_course_query(visible_only: bool = True):
    q = (
        select(Course)
        .options(
            selectinload(Course.modules)
            .selectinload(Module.units)
            .selectinload(ModuleUnit.task)
        )
        .order_by(Course.order, Course.id)
    )
    if visible_only:
        q = q.where(Course.is_visible == True)  # noqa: E712
    return q
```

В `list_courses` и `get_course` — передавать `visible_only=True` (по умолчанию так и есть, править не надо).

- [ ] **Step 3: Прогнать + commit**

```bash
docker compose exec backend pytest tests/test_courses_visibility.py -v
git add backend/routers/courses.py backend/tests/test_courses_visibility.py
git commit -m "feat(courses): filter student view by is_visible"
```

---

# Phase 6 — Import/export

### Task 17: Export / Import tasks

**Files:**
- Modify: `backend/routers/admin_content.py`
- Create: `backend/tests/test_admin_content_io_tasks.py`

- [ ] **Step 1: Тест**

```python
import io
import uuid
import zipfile

import pytest
from httpx import ASGITransport, AsyncClient

from auth import create_token, hash_password
from database import async_session, engine
from main import app
from models import User, UserRole

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
async def _dispose_engine():
    await engine.dispose()
    yield
    await engine.dispose()


async def _admin_token():
    async with async_session() as db:
        u = User(username=f"a-{uuid.uuid4().hex[:6]}",
                 password_hash=hash_password("x"), role=UserRole.admin)
        db.add(u); await db.commit(); await db.refresh(u)
        return create_token(u.id, "admin")


async def test_export_import_task_roundtrip():
    token = await _admin_token()
    h = {"Authorization": f"Bearer {token}"}
    suffix = uuid.uuid4().hex[:6]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        cr = await c.post("/api/admin/content/tasks",
                          json={"slug": f"io-{suffix}", "title": "IO",
                                "type": "theory", "config": {"content_kind": "text",
                                                              "content": "hi"}},
                          headers=h)
        tid = cr.json()["id"]

        er = await c.get(f"/api/admin/content/tasks/{tid}/export", headers=h)
        assert er.status_code == 200
        assert er.headers["content-type"] == "application/zip"
        zf = zipfile.ZipFile(io.BytesIO(er.content))
        assert "manifest.yaml" in zf.namelist()

        # delete original
        await c.delete(f"/api/admin/content/tasks/{tid}", headers=h)

        # import
        files = {"file": ("bundle.zip", er.content, "application/zip")}
        ir = await c.post("/api/admin/content/tasks/import", files=files, headers=h)
        assert ir.status_code == 201
        assert ir.json()["slug"] == f"io-{suffix}"
```

- [ ] **Step 2: Реализовать export/import**

В `admin_content.py`:

```python
from fastapi import File, Response, UploadFile

from services.bundle import BundleError, open_bundle, pack_task, read_yaml


def _task_manifest(task: Task) -> dict:
    return {
        "slug": task.slug,
        "title": task.title,
        "description": task.description or "",
        "type": task.type.value,
        "order": task.order,
        "config": task.config or {},
    }


@router.get("/tasks/{task_id}/export")
async def export_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    blob = pack_task(_task_manifest(task))
    return Response(
        content=blob,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="task-{task.slug}.zip"'},
    )


async def _upsert_task_from_manifest(manifest: dict, admin_id: int,
                                       db: AsyncSession) -> Task:
    from pydantic import ValidationError
    try:
        parsed = TaskCreate.model_validate(manifest)
    except ValidationError as e:
        raise HTTPException(422, f"Invalid task manifest: {e}")
    cfg = apply_flag_to_config(parsed.config or {})
    existing = await db.execute(select(Task).where(Task.slug == parsed.slug))
    task = existing.scalar_one_or_none()
    if task:
        task.title = parsed.title
        task.description = parsed.description
        task.order = parsed.order
        task.type = parsed.type
        task.config = cfg
        task.author_id = admin_id
    else:
        task = Task(
            slug=parsed.slug, title=parsed.title, description=parsed.description,
            order=parsed.order, type=parsed.type, config=cfg, author_id=admin_id,
        )
        db.add(task)
    return task


@router.post("/tasks/import", status_code=201, response_model=TaskOutAdmin)
async def import_task(
    file: UploadFile = File(...),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    raw = await file.read()
    try:
        zf = open_bundle(raw)
        manifest = read_yaml(zf, "manifest.yaml")
    except BundleError as e:
        raise HTTPException(400, str(e))
    task = await _upsert_task_from_manifest(manifest, admin.id, db)
    await db.commit()
    await db.refresh(task)
    return _task_out(task)
```

- [ ] **Step 3: Прогнать + commit**

```bash
docker compose exec backend pytest tests/test_admin_content_io_tasks.py -v
git add backend/routers/admin_content.py backend/tests/test_admin_content_io_tasks.py
git commit -m "feat(admin): import/export single tasks via ZIP"
```

---

### Task 18: Export / Import courses (c опциональным bundle)

**Files:**
- Modify: `backend/routers/admin_content.py`
- Create: `backend/tests/test_admin_content_io_courses.py`

- [ ] **Step 1: Тесты**

```python
import io
import uuid
import zipfile

import pytest
import yaml
from httpx import ASGITransport, AsyncClient

from auth import create_token, hash_password
from database import async_session, engine
from main import app
from models import User, UserRole

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
async def _dispose_engine():
    await engine.dispose()
    yield
    await engine.dispose()


async def _admin_token():
    async with async_session() as db:
        u = User(username=f"a-{uuid.uuid4().hex[:6]}",
                 password_hash=hash_password("x"), role=UserRole.admin)
        db.add(u); await db.commit(); await db.refresh(u)
        return create_token(u.id, "admin")


async def test_course_bundle_export_contains_tasks():
    token = await _admin_token()
    h = {"Authorization": f"Bearer {token}"}
    suffix = uuid.uuid4().hex[:6]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        cr = await c.post("/api/admin/content/courses",
                          json={"slug": f"cb-{suffix}", "title": "Cb"}, headers=h)
        cid = cr.json()["id"]
        tr = await c.post("/api/admin/content/tasks",
                          json={"slug": f"tb-{suffix}", "title": "T",
                                "type": "theory", "config": {}}, headers=h)
        tid = tr.json()["id"]
        mr = await c.post(f"/api/admin/content/courses/{cid}/modules",
                          json={"title": "M", "order": 1}, headers=h)
        mid = mr.json()["id"]
        await c.post(f"/api/admin/content/modules/{mid}/units",
                     json={"task_id": tid, "unit_order": 1, "is_required": True},
                     headers=h)

        er = await c.get(f"/api/admin/content/courses/{cid}/export?bundle=true",
                         headers=h)
        assert er.status_code == 200
        zf = zipfile.ZipFile(io.BytesIO(er.content))
        assert "course.yaml" in zf.namelist()
        task_files = [n for n in zf.namelist() if n.startswith("tasks/")]
        assert len(task_files) == 1


async def test_import_course_missing_task_returns_400():
    token = await _admin_token()
    h = {"Authorization": f"Bearer {token}"}
    suffix = uuid.uuid4().hex[:6]
    course_manifest = {
        "slug": f"imp-{suffix}", "title": "Imp", "description": "", "order": 0,
        "config": {},
        "modules": [{"title": "M", "order": 1, "description": "",
                      "estimated_hours": None, "learning_outcomes": [], "config": {},
                      "units": [{"task_slug": "nonexistent-task",
                                  "unit_order": 1, "is_required": True}]}],
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("course.yaml", yaml.safe_dump(course_manifest))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/admin/content/courses/import",
                         files={"file": ("b.zip", buf.getvalue(), "application/zip")},
                         headers=h)
        assert r.status_code == 400
        assert "nonexistent-task" in r.text
```

- [ ] **Step 2: Реализовать**

В `admin_content.py`:

```python
from sqlalchemy.orm import selectinload

from services.bundle import list_task_files, pack_course


def _module_manifest(m: Module) -> dict:
    return {
        "title": m.title,
        "order": m.order,
        "description": m.description or "",
        "estimated_hours": m.estimated_hours,
        "learning_outcomes": m.learning_outcomes or [],
        "config": m.config or {},
        "units": [
            {"task_slug": u.task.slug, "unit_order": u.unit_order,
             "is_required": u.is_required}
            for u in sorted(m.units, key=lambda x: x.unit_order)
        ],
    }


def _course_manifest(course: Course) -> dict:
    return {
        "slug": course.slug,
        "title": course.title,
        "description": course.description or "",
        "order": course.order,
        "config": course.config or {},
        "modules": [_module_manifest(m) for m in sorted(course.modules, key=lambda x: x.order)],
    }


@router.get("/courses/{course_id}/export")
async def export_course(course_id: int, bundle: bool = False,
                         db: AsyncSession = Depends(get_db)):
    rows = await db.execute(
        select(Course)
        .options(selectinload(Course.modules)
                 .selectinload(Module.units)
                 .selectinload(ModuleUnit.task))
        .where(Course.id == course_id)
    )
    course = rows.scalars().unique().one_or_none()
    if not course:
        raise HTTPException(404, "Course not found")

    tasks_manifest: dict[str, dict] = {}
    if bundle:
        for m in course.modules:
            for u in m.units:
                tasks_manifest[u.task.slug] = _task_manifest(u.task)

    blob = pack_course(_course_manifest(course), tasks_manifest)
    return Response(
        content=blob, media_type="application/zip",
        headers={"Content-Disposition":
                 f'attachment; filename="course-{course.slug}.zip"'},
    )


@router.post("/courses/import", status_code=201, response_model=CourseOutAdmin)
async def import_course(
    file: UploadFile = File(...),
    import_tasks: bool = False,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    raw = await file.read()
    try:
        zf = open_bundle(raw)
        course_data = read_yaml(zf, "course.yaml")
    except BundleError as e:
        raise HTTPException(400, str(e))

    # Опционально импортируем таски ПЕРЕД курсом — нужны для resolve task_slug → task_id
    if import_tasks:
        for name in list_task_files(zf):
            m = read_yaml(zf, name)
            await _upsert_task_from_manifest(m, admin.id, db)
        await db.flush()

    # Resolve task_slug → task_id
    referenced_slugs: set[str] = set()
    for m in course_data.get("modules", []):
        for u in m.get("units", []):
            referenced_slugs.add(u["task_slug"])
    rows = await db.execute(select(Task.slug, Task.id).where(Task.slug.in_(referenced_slugs)))
    slug_to_id = dict(rows.all())
    missing = referenced_slugs - set(slug_to_id)
    if missing:
        await db.rollback()
        raise HTTPException(400, {"message": "Missing tasks", "slugs": sorted(missing)})

    # Upsert course (UPDATE если slug уже есть, CREATE иначе)
    existing = await db.execute(select(Course).where(Course.slug == course_data["slug"]))
    course = existing.scalar_one_or_none()
    if course:
        # сносим старые модули — ON DELETE CASCADE удалит юниты
        for m in list(course.modules):
            await db.delete(m)
        course.title = course_data["title"]
        course.description = course_data.get("description", "")
        course.order = course_data.get("order", 0)
        course.config = course_data.get("config", {})
        # is_visible при импорте всегда False (спека, секция 4)
        course.is_visible = False
    else:
        course = Course(
            slug=course_data["slug"], title=course_data["title"],
            description=course_data.get("description", ""),
            order=course_data.get("order", 0),
            config=course_data.get("config", {}),
            is_visible=False,
        )
        db.add(course)
    await db.flush()

    for m_data in course_data.get("modules", []):
        module = Module(
            course_id=course.id, title=m_data["title"], order=m_data["order"],
            description=m_data.get("description", ""),
            estimated_hours=m_data.get("estimated_hours"),
            learning_outcomes=m_data.get("learning_outcomes", []),
            config=m_data.get("config", {}),
        )
        db.add(module)
        await db.flush()
        for u_data in m_data.get("units", []):
            db.add(ModuleUnit(
                module_id=module.id,
                task_id=slug_to_id[u_data["task_slug"]],
                unit_order=u_data.get("unit_order", 0),
                is_required=u_data.get("is_required", True),
            ))
    await db.commit()
    await db.refresh(course)
    return course
```

- [ ] **Step 3: Прогнать + commit**

```bash
docker compose exec backend pytest tests/test_admin_content_io_courses.py -v
git add backend/routers/admin_content.py backend/tests/test_admin_content_io_courses.py
git commit -m "feat(admin): import/export courses with optional task bundle"
```

---

# Phase 7 — Frontend scaffolding

### Task 19: Добавить @dnd-kit

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Установить**

Run: `docker compose exec frontend npm install @dnd-kit/core@^6.1.0 @dnd-kit/sortable@^8.0.0 @dnd-kit/utilities@^3.2.2`
Expected: пакеты добавлены в `package.json` и `package-lock.json`.

- [ ] **Step 2: Build-smoke**

Run: `docker compose exec frontend npm run build`
Expected: билд проходит.

- [ ] **Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore(frontend): add @dnd-kit for drag-and-drop"
```

---

### Task 20: Типы и API-клиент для admin-content

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api.ts`

- [ ] **Step 1: Добавить типы**

В `frontend/src/types.ts` (в конце файла):

```typescript
export type TaskType = 'quiz' | 'ctf' | 'gitlab' | 'theory' | 'ssh_lab';

export interface AdminTask {
  id: number;
  slug: string;
  title: string;
  description: string;
  type: TaskType;
  order: number;
  config: Record<string, any>;
  author_id: number | null;
  updated_at: string;
  usage?: { course_id: number; course_slug: string; module_id: number; unit_id: number }[];
}

export interface AdminCourse {
  id: number;
  slug: string;
  title: string;
  description: string;
  order: number;
  config: Record<string, any>;
  is_visible: boolean;
}

export interface AdminModule {
  id: number;
  course_id: number;
  title: string;
  description: string;
  order: number;
  estimated_hours: number | null;
  learning_outcomes: string[];
  config: Record<string, any>;
}

export interface AdminUnit {
  id: number;
  module_id: number;
  task_id: number;
  unit_order: number;
  is_required: boolean;
}
```

- [ ] **Step 2: Добавить api.adminContent**

В `frontend/src/api.ts` в объект `api` добавить секцию (вставка перед закрывающей `}`):

```typescript
  adminContent: {
    listCourses: () => request<AdminCourse[]>('/admin/content/courses'),
    createCourse: (body: Partial<AdminCourse>) =>
      request<AdminCourse>('/admin/content/courses',
        { method: 'POST', body: JSON.stringify(body) }),
    patchCourse: (id: number, body: Partial<AdminCourse>) =>
      request<AdminCourse>(`/admin/content/courses/${id}`,
        { method: 'PATCH', body: JSON.stringify(body) }),
    deleteCourse: (id: number) =>
      request<void>(`/admin/content/courses/${id}`, { method: 'DELETE' }),
    reorderModules: (course_id: number, items: {id: number; order: number}[]) =>
      request<{ok: true}>(`/admin/content/courses/${course_id}/reorder-modules`,
        { method: 'POST', body: JSON.stringify(items) }),

    createModule: (course_id: number, body: Partial<AdminModule>) =>
      request<AdminModule>(`/admin/content/courses/${course_id}/modules`,
        { method: 'POST', body: JSON.stringify(body) }),
    patchModule: (id: number, body: Partial<AdminModule>) =>
      request<AdminModule>(`/admin/content/modules/${id}`,
        { method: 'PATCH', body: JSON.stringify(body) }),
    deleteModule: (id: number) =>
      request<void>(`/admin/content/modules/${id}`, { method: 'DELETE' }),
    reorderUnits: (module_id: number, items: {id: number; order: number}[]) =>
      request<{ok: true}>(`/admin/content/modules/${module_id}/reorder-units`,
        { method: 'POST', body: JSON.stringify(items) }),

    createUnit: (module_id: number, body: Partial<AdminUnit>) =>
      request<AdminUnit>(`/admin/content/modules/${module_id}/units`,
        { method: 'POST', body: JSON.stringify(body) }),
    patchUnit: (id: number, body: Partial<AdminUnit>) =>
      request<AdminUnit>(`/admin/content/units/${id}`,
        { method: 'PATCH', body: JSON.stringify(body) }),
    deleteUnit: (id: number) =>
      request<void>(`/admin/content/units/${id}`, { method: 'DELETE' }),

    listTasks: (params: {type?: string; search?: string; unused?: boolean} = {}) => {
      const qs = new URLSearchParams();
      if (params.type) qs.set('type', params.type);
      if (params.search) qs.set('search', params.search);
      if (params.unused) qs.set('unused', 'true');
      const q = qs.toString();
      return request<AdminTask[]>(`/admin/content/tasks${q ? '?' + q : ''}`);
    },
    getTask: (id: number) => request<AdminTask>(`/admin/content/tasks/${id}`),
    createTask: (body: Partial<AdminTask>) =>
      request<AdminTask>('/admin/content/tasks',
        { method: 'POST', body: JSON.stringify(body) }),
    patchTask: (id: number, body: Partial<AdminTask>) =>
      request<AdminTask>(`/admin/content/tasks/${id}`,
        { method: 'PATCH', body: JSON.stringify(body) }),
    deleteTask: (id: number) =>
      request<void>(`/admin/content/tasks/${id}`, { method: 'DELETE' }),

    exportTask: (id: number) =>
      fetch(`${API_BASE}/admin/content/tasks/${id}/export`,
        { headers: { Authorization: `Bearer ${getToken()}` } }).then(r => r.blob()),
    exportCourse: (id: number, bundle: boolean) =>
      fetch(`${API_BASE}/admin/content/courses/${id}/export?bundle=${bundle}`,
        { headers: { Authorization: `Bearer ${getToken()}` } }).then(r => r.blob()),
    importTask: (file: File) => {
      const fd = new FormData();
      fd.append('file', file);
      return fetch(`${API_BASE}/admin/content/tasks/import`,
        { method: 'POST', body: fd,
          headers: { Authorization: `Bearer ${getToken()}` } })
        .then(r => r.json());
    },
    importCourse: (file: File, importTasks: boolean) => {
      const fd = new FormData();
      fd.append('file', file);
      return fetch(`${API_BASE}/admin/content/courses/import?import_tasks=${importTasks}`,
        { method: 'POST', body: fd,
          headers: { Authorization: `Bearer ${getToken()}` } })
        .then(r => r.json());
    },
  },
```

Также добавить импорты типов в начало `api.ts`:

```typescript
import type { AdminCourse, AdminModule, AdminTask, AdminUnit } from './types';
```

- [ ] **Step 2b: `getToken` сейчас внутри модуля, но не экспортируется** — экспортировать его, либо сделать локальную helper-функцию. Проще: экспортировать.

Заменить `function getToken()` на `export function getToken()` в `api.ts`.

- [ ] **Step 3: TypeScript check**

Run: `docker compose exec frontend npx tsc --noEmit`
Expected: без ошибок.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types.ts frontend/src/api.ts
git commit -m "feat(frontend): admin content API client and types"
```

---

### Task 21: Маршруты и sidebar

**Files:**
- Modify: `frontend/src/main.tsx`
- Modify: `frontend/src/components/Sidebar.tsx`
- Create: `frontend/src/pages/admin/AdminCoursesPage.tsx` (заглушка)
- Create: `frontend/src/pages/admin/AdminTasksPage.tsx` (заглушка)
- Create: `frontend/src/pages/admin/CourseEditorPage.tsx` (заглушка)
- Create: `frontend/src/pages/admin/TaskEditorPage.tsx` (заглушка)

- [ ] **Step 1: Страницы-заглушки**

Каждая — минимум, чтобы билд прошёл:

`AdminCoursesPage.tsx`:
```tsx
export default function AdminCoursesPage() {
  return <div className="p-6">Admin Courses (TODO)</div>;
}
```

Аналогично `AdminTasksPage.tsx`, `CourseEditorPage.tsx`, `TaskEditorPage.tsx`.

- [ ] **Step 2: Добавить маршруты**

В `frontend/src/main.tsx`:

```tsx
import AdminCoursesPage from './pages/admin/AdminCoursesPage';
import CourseEditorPage from './pages/admin/CourseEditorPage';
import AdminTasksPage from './pages/admin/AdminTasksPage';
import TaskEditorPage from './pages/admin/TaskEditorPage';
```

В `<Route element={<AdminLayout />}>` добавить:

```tsx
<Route path="/admin/courses" element={<AdminCoursesPage />} />
<Route path="/admin/courses/:id" element={<CourseEditorPage />} />
<Route path="/admin/tasks" element={<AdminTasksPage />} />
<Route path="/admin/tasks/new" element={<TaskEditorPage />} />
<Route path="/admin/tasks/:id" element={<TaskEditorPage />} />
```

- [ ] **Step 3: Пункты в Sidebar**

Открыть `frontend/src/components/Sidebar.tsx`, найти блок admin-пунктов и добавить две ссылки:

```tsx
{ to: '/admin/courses', label: 'Курсы', icon: 'school' },
{ to: '/admin/tasks', label: 'Таски', icon: 'task_alt' },
```

(конкретный формат подбирать по текущему коду Sidebar.tsx)

- [ ] **Step 4: Build smoke**

Run: `docker compose exec frontend npm run build`
Expected: билд проходит.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/main.tsx frontend/src/components/Sidebar.tsx frontend/src/pages/admin/
git commit -m "feat(frontend): admin content routes and sidebar entries"
```

---

# Phase 8 — Task editor UI

### Task 22: AdminTasksPage — список + фильтры + импорт

**Files:**
- Modify: `frontend/src/pages/admin/AdminTasksPage.tsx`

- [ ] **Step 1: Реализация**

```tsx
import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { api } from '../../api';
import Button from '../../components/Button';
import FormInput from '../../components/FormInput';
import FormSelect from '../../components/FormSelect';
import type { AdminTask, TaskType } from '../../types';

const TYPES: (TaskType | '')[] = ['', 'theory', 'quiz', 'ctf', 'ssh_lab', 'gitlab'];

export default function AdminTasksPage() {
  const nav = useNavigate();
  const [tasks, setTasks] = useState<AdminTask[]>([]);
  const [type, setType] = useState<string>('');
  const [search, setSearch] = useState('');
  const [unused, setUnused] = useState(false);
  const [error, setError] = useState('');

  const load = async () => {
    try {
      const t = await api.adminContent.listTasks({
        type: type || undefined,
        search: search || undefined,
        unused: unused || undefined,
      });
      setTasks(t);
    } catch (e: any) {
      setError(e.message);
    }
  };
  useEffect(() => { load(); }, [type, unused]);

  const onImport = async (file: File) => {
    try {
      await api.adminContent.importTask(file);
      await load();
    } catch (e: any) { setError(e.message); }
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center gap-3">
        <h2 className="text-xl font-bold">Таски</h2>
        <div className="flex-1" />
        <Link to="/admin/tasks/new"><Button>Новый таск</Button></Link>
        <label className="inline-block">
          <input type="file" accept=".zip" className="hidden"
                 onChange={e => e.target.files?.[0] && onImport(e.target.files[0])} />
          <span className="px-3 py-2 bg-surface-container-low cursor-pointer">Импорт</span>
        </label>
      </div>

      <div className="flex gap-3 items-end">
        <FormSelect label="Тип" value={type} onChange={setType}
          options={TYPES.map(t => ({ value: t, label: t || 'Все' }))} />
        <FormInput label="Поиск" value={search} onChange={setSearch}
                   onKeyDown={e => e.key === 'Enter' && load()} />
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={unused}
                 onChange={e => setUnused(e.target.checked)} />
          Неиспользуемые
        </label>
        <Button onClick={load}>Обновить</Button>
      </div>

      {error && <div className="text-error">{error}</div>}

      <table className="w-full">
        <thead><tr>
          <th className="text-left">Title</th>
          <th className="text-left">Slug</th>
          <th className="text-left">Type</th>
          <th className="text-left">Updated</th>
        </tr></thead>
        <tbody>
          {tasks.map(t => (
            <tr key={t.id} className="cursor-pointer hover:bg-surface-container-low"
                onClick={() => nav(`/admin/tasks/${t.id}`)}>
              <td>{t.title}</td>
              <td className="font-mono text-sm">{t.slug}</td>
              <td>{t.type}</td>
              <td className="text-sm">{new Date(t.updated_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 2: Build**

Run: `docker compose exec frontend npm run build`
Expected: ok.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/admin/AdminTasksPage.tsx
git commit -m "feat(frontend): AdminTasksPage list, filters, import"
```

---

### Task 23: TaskEditor — shell + общие поля + диспетчер по типу

**Files:**
- Modify: `frontend/src/pages/admin/TaskEditorPage.tsx`

- [ ] **Step 1: Реализация — shell**

```tsx
import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { api } from '../../api';
import Button from '../../components/Button';
import FormInput from '../../components/FormInput';
import FormSelect from '../../components/FormSelect';
import type { AdminTask, TaskType } from '../../types';

const TYPES: TaskType[] = ['theory', 'quiz', 'ctf', 'ssh_lab', 'gitlab'];

export default function TaskEditorPage() {
  const { id } = useParams<{ id: string }>();
  const nav = useNavigate();
  const isNew = !id;
  const [task, setTask] = useState<Partial<AdminTask>>({
    type: 'theory', title: '', slug: '', description: '', order: 0, config: {},
  });
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!isNew && id) {
      api.adminContent.getTask(Number(id)).then(setTask).catch(e => setError(e.message));
    }
  }, [id]);

  const onSave = async () => {
    setSaving(true); setError('');
    try {
      if (isNew) {
        const created = await api.adminContent.createTask(task);
        nav(`/admin/tasks/${created.id}`);
      } else {
        const u = await api.adminContent.patchTask(Number(id), task);
        setTask(u);
      }
    } catch (e: any) { setError(e.message); }
    finally { setSaving(false); }
  };

  const onDelete = async () => {
    if (!id) return;
    if (!confirm('Удалить таск?')) return;
    try {
      await api.adminContent.deleteTask(Number(id));
      nav('/admin/tasks');
    } catch (e: any) { setError(e.message); }
  };

  const onExport = async () => {
    if (!id) return;
    const blob = await api.adminContent.exportTask(Number(id));
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `task-${task.slug}.zip`; a.click();
    URL.revokeObjectURL(url);
  };

  const updateConfig = (patch: Record<string, any>) =>
    setTask(t => ({ ...t, config: { ...(t.config || {}), ...patch } }));

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      <div className="flex items-center gap-3">
        <h2 className="text-xl font-bold">{isNew ? 'Новый таск' : `Таск: ${task.title}`}</h2>
        <div className="flex-1" />
        {!isNew && <Button onClick={onExport}>Экспорт</Button>}
        {!isNew && task.usage && task.usage.length === 0 &&
          <Button onClick={onDelete} variant="danger">Удалить</Button>}
        <Button onClick={onSave} disabled={saving}>
          {saving ? '…' : 'Сохранить'}
        </Button>
      </div>

      {error && <div className="text-error">{error}</div>}

      <FormInput label="Title" value={task.title || ''}
                 onChange={v => setTask(t => ({
                   ...t, title: v,
                   slug: t.slug || slugifyLocal(v),
                 }))} />
      <FormInput label="Slug" value={task.slug || ''}
                 onChange={v => setTask(t => ({ ...t, slug: v }))}
                 hint="a-z, 0-9, '-'; 2-100 chars" />
      <FormSelect label="Type" value={task.type || 'theory'} disabled={!isNew}
                  onChange={v => setTask(t => ({ ...t, type: v as TaskType, config: {} }))}
                  options={TYPES.map(t => ({ value: t, label: t }))} />
      <FormInput label="Description" value={task.description || ''}
                 onChange={v => setTask(t => ({ ...t, description: v }))} multiline />
      <FormInput label="Order" type="number" value={String(task.order ?? 0)}
                 onChange={v => setTask(t => ({ ...t, order: Number(v) }))} />

      <TypeSpecificForm task={task} updateConfig={updateConfig} />
    </div>
  );
}

function slugifyLocal(s: string): string {
  const map: Record<string, string> = {
    а:'a',б:'b',в:'v',г:'g',д:'d',е:'e',ё:'yo',ж:'zh',з:'z',и:'i',й:'y',к:'k',л:'l',м:'m',
    н:'n',о:'o',п:'p',р:'r',с:'s',т:'t',у:'u',ф:'f',х:'h',ц:'c',ч:'ch',ш:'sh',щ:'sch',
    ъ:'',ы:'y',ь:'',э:'e',ю:'yu',я:'ya',
  };
  return s.toLowerCase()
    .split('').map(c => map[c] ?? (/[a-z0-9]/.test(c) ? c : c === ' ' ? '-' : ''))
    .join('').replace(/-+/g, '-').replace(/^-|-$/g, '').slice(0, 100);
}

function TypeSpecificForm({ task, updateConfig }: {
  task: Partial<AdminTask>; updateConfig: (p: Record<string, any>) => void;
}) {
  // Следующие таски добавят конкретные формы; пока — заглушка для каждого типа
  return <pre className="bg-surface-container-low p-4 text-xs">
    {JSON.stringify(task.config, null, 2)}
  </pre>;
}
```

- [ ] **Step 2: Build**

Run: `docker compose exec frontend npm run build`
Expected: ok.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/admin/TaskEditorPage.tsx
git commit -m "feat(frontend): TaskEditor shell with common fields"
```

---

### Task 24: TheoryForm — text/video/mixed

**Files:**
- Create: `frontend/src/components/admin/task-forms/TheoryForm.tsx`
- Create: `frontend/src/components/admin/MarkdownEditor.tsx`
- Modify: `frontend/src/pages/admin/TaskEditorPage.tsx`

- [ ] **Step 1: MarkdownEditor**

```tsx
import { Md } from '../Md';

export default function MarkdownEditor({ value, onChange }: {
  value: string; onChange: (v: string) => void;
}) {
  return (
    <div className="grid grid-cols-2 gap-4">
      <textarea className="h-96 font-mono text-sm p-3 bg-surface-container-low"
        value={value} onChange={e => onChange(e.target.value)} />
      <div className="h-96 overflow-auto p-3 bg-surface-container-low">
        <Md>{value}</Md>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: TheoryForm**

```tsx
import FormInput from '../../FormInput';
import FormSelect from '../../FormSelect';
import MarkdownEditor from '../MarkdownEditor';

export default function TheoryForm({ config, update }: {
  config: Record<string, any>; update: (p: Record<string, any>) => void;
}) {
  const kind = config.content_kind || 'text';
  const video = config.video || { provider: 'youtube', src: '' };

  const showText = kind === 'text' || kind === 'mixed';
  const showVideo = kind === 'video' || kind === 'mixed';

  return (
    <div className="space-y-4">
      <FormSelect label="Content kind" value={kind}
                  onChange={v => update({ content_kind: v })}
                  options={[
                    { value: 'text', label: 'Text' },
                    { value: 'video', label: 'Video' },
                    { value: 'mixed', label: 'Mixed' },
                  ]} />

      {showVideo && <>
        <FormSelect label="Video provider" value={video.provider}
          onChange={v => update({ video: { ...video, provider: v } })}
          options={[{value:'youtube',label:'YouTube'},{value:'url',label:'URL'}]} />
        <FormInput label="Video URL" value={video.src}
          onChange={v => update({ video: { ...video, src: v } })} />
      </>}

      {showText && (
        <div>
          <div className="text-sm mb-2">Content (markdown)</div>
          <MarkdownEditor value={config.content || ''}
                          onChange={v => update({ content: v })} />
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Подключить в TaskEditorPage**

В `TypeSpecificForm` заменить заглушку:

```tsx
import TheoryForm from '../../components/admin/task-forms/TheoryForm';

function TypeSpecificForm({ task, updateConfig }: {
  task: Partial<AdminTask>; updateConfig: (p: Record<string, any>) => void;
}) {
  const cfg = task.config || {};
  switch (task.type) {
    case 'theory': return <TheoryForm config={cfg} update={updateConfig} />;
    default: return <pre className="bg-surface-container-low p-4 text-xs">
      {JSON.stringify(cfg, null, 2)}
    </pre>;
  }
}
```

- [ ] **Step 4: Build + commit**

```bash
docker compose exec frontend npm run build
git add frontend/src/components/admin/MarkdownEditor.tsx frontend/src/components/admin/task-forms/TheoryForm.tsx frontend/src/pages/admin/TaskEditorPage.tsx
git commit -m "feat(frontend): theory form editor (text/video/mixed)"
```

---

### Task 25: QuizForm

**Files:**
- Create: `frontend/src/components/admin/task-forms/QuizForm.tsx`
- Modify: `frontend/src/pages/admin/TaskEditorPage.tsx`

- [ ] **Step 1: QuizForm**

```tsx
import Button from '../../Button';
import FormInput from '../../FormInput';

interface Choice { text: string; correct: boolean; }
interface Question { id?: number; text: string; options: Choice[]; }

export default function QuizForm({ config, update }: {
  config: Record<string, any>; update: (p: Record<string, any>) => void;
}) {
  const questions: Question[] = config.questions || [];
  const setQuestions = (q: Question[]) => update({ questions: q });

  const addQuestion = () => setQuestions([...questions,
    { text: '', options: [{ text: '', correct: true }] }]);
  const patchQuestion = (i: number, patch: Partial<Question>) =>
    setQuestions(questions.map((q, idx) => idx === i ? { ...q, ...patch } : q));
  const removeQuestion = (i: number) =>
    setQuestions(questions.filter((_, idx) => idx !== i));

  return (
    <div className="space-y-4">
      <div className="flex gap-4 items-end">
        <FormInput label="Pass threshold %" type="number"
                   value={String(config.pass_threshold ?? 70)}
                   onChange={v => update({ pass_threshold: Number(v) })} />
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={!!config.shuffle}
                 onChange={e => update({ shuffle: e.target.checked })} />
          Shuffle
        </label>
      </div>

      {questions.map((q, i) => (
        <div key={i} className="border p-4 space-y-2">
          <div className="flex items-center gap-2">
            <div className="text-sm font-bold">Q{i + 1}</div>
            <div className="flex-1" />
            <Button variant="danger" onClick={() => removeQuestion(i)}>Удалить</Button>
          </div>
          <FormInput label="Question" value={q.text}
                     onChange={v => patchQuestion(i, { text: v })} multiline />
          <div className="space-y-1">
            {q.options.map((o, j) => (
              <div key={j} className="flex items-center gap-2">
                <input type="checkbox" checked={o.correct}
                       onChange={e => patchQuestion(i, {
                         options: q.options.map((oo, jj) =>
                           jj === j ? { ...oo, correct: e.target.checked } : oo)
                       })} />
                <input className="flex-1 p-1 bg-surface-container-low"
                       value={o.text}
                       onChange={e => patchQuestion(i, {
                         options: q.options.map((oo, jj) =>
                           jj === j ? { ...oo, text: e.target.value } : oo)
                       })} />
                <Button onClick={() => patchQuestion(i, {
                  options: q.options.filter((_, jj) => jj !== j) })}>×</Button>
              </div>
            ))}
            <Button onClick={() => patchQuestion(i, {
              options: [...q.options, { text: '', correct: false }] })}>
              + Вариант
            </Button>
          </div>
        </div>
      ))}
      <Button onClick={addQuestion}>+ Вопрос</Button>
    </div>
  );
}
```

- [ ] **Step 2: Подключить**

В `TaskEditorPage.tsx` в `TypeSpecificForm`:

```tsx
import QuizForm from '../../components/admin/task-forms/QuizForm';
// ...
case 'quiz': return <QuizForm config={cfg} update={updateConfig} />;
```

- [ ] **Step 3: Build + commit**

```bash
docker compose exec frontend npm run build
git add frontend/src/components/admin/task-forms/QuizForm.tsx frontend/src/pages/admin/TaskEditorPage.tsx
git commit -m "feat(frontend): quiz form editor"
```

---

### Task 26: CtfForm, SshLabForm, GitlabForm

**Files:**
- Create: `frontend/src/components/admin/task-forms/CtfForm.tsx`
- Create: `frontend/src/components/admin/task-forms/SshLabForm.tsx`
- Create: `frontend/src/components/admin/task-forms/GitlabForm.tsx`
- Modify: `frontend/src/pages/admin/TaskEditorPage.tsx`

- [ ] **Step 1: CtfForm**

```tsx
import { useState } from 'react';

import FormInput from '../../FormInput';
import FormSelect from '../../FormSelect';

export default function CtfForm({ config, update }: {
  config: Record<string, any>; update: (p: Record<string, any>) => void;
}) {
  const [changeFlag, setChangeFlag] = useState(false);
  const hasHash = !!config.flag_hash;

  return (
    <div className="space-y-3">
      <FormInput label="Docker image" value={config.docker_image || ''}
                 onChange={v => update({ docker_image: v })}
                 hint="myuser/lms-xyz:v1 — образ должен быть доступен docker pull с хоста" />
      <FormInput label="Port (внутри контейнера)" type="number"
                 value={String(config.port ?? 5000)}
                 onChange={v => update({ port: Number(v) })} />
      <FormInput label="TTL minutes" type="number"
                 value={String(config.ttl_minutes ?? 120)}
                 onChange={v => update({ ttl_minutes: Number(v) })} />
      <FormSelect label="Difficulty" value={config.difficulty || 'medium'}
                  onChange={v => update({ difficulty: v })}
                  options={['easy','medium','hard'].map(x => ({value:x,label:x}))} />
      {hasHash && !changeFlag ? (
        <div className="flex gap-3 items-center">
          <span className="text-sm">Flag hash set</span>
          <button className="underline" onClick={() => setChangeFlag(true)}>Изменить</button>
        </div>
      ) : (
        <FormInput label="Flag (plaintext)" type="password"
                   value={config.flag || ''}
                   onChange={v => update({ flag: v })}
                   hint="Хэшируется в SHA256 при сохранении; plaintext не сохраняется." />
      )}
    </div>
  );
}
```

- [ ] **Step 2: SshLabForm**

```tsx
import { useState } from 'react';

import FormInput from '../../FormInput';
import FormSelect from '../../FormSelect';
import MarkdownEditor from '../MarkdownEditor';

export default function SshLabForm({ config, update }: {
  config: Record<string, any>; update: (p: Record<string, any>) => void;
}) {
  const [changeFlag, setChangeFlag] = useState(false);
  const hasHash = !!config.flag_hash;
  return (
    <div className="space-y-3">
      <FormInput label="Docker image" value={config.docker_image || ''}
                 onChange={v => update({ docker_image: v })} />
      <FormInput label="Terminal port (ttyd)" type="number"
                 value={String(config.terminal_port ?? 80)}
                 onChange={v => update({ terminal_port: Number(v) })} />
      <FormInput label="TTL minutes" type="number"
                 value={String(config.ttl_minutes ?? 120)}
                 onChange={v => update({ ttl_minutes: Number(v) })} />
      <FormSelect label="Difficulty" value={config.difficulty || 'medium'}
                  onChange={v => update({ difficulty: v })}
                  options={['easy','medium','hard'].map(x => ({value:x,label:x}))} />
      <div>
        <div className="text-sm mb-2">Instructions (markdown)</div>
        <MarkdownEditor value={config.instructions || ''}
                        onChange={v => update({ instructions: v })} />
      </div>
      {hasHash && !changeFlag ? (
        <div className="flex gap-3 items-center">
          <span className="text-sm">Flag hash set</span>
          <button className="underline" onClick={() => setChangeFlag(true)}>Изменить</button>
        </div>
      ) : (
        <FormInput label="Flag (plaintext)" type="password"
                   value={config.flag || ''}
                   onChange={v => update({ flag: v })} />
      )}
    </div>
  );
}
```

- [ ] **Step 3: GitlabForm — JSON-редактор для первой итерации**

```tsx
export default function GitlabForm({ config, update }: {
  config: Record<string, any>; update: (p: Record<string, any>) => void;
}) {
  return (
    <div>
      <div className="text-sm mb-2">GitLab task config (JSON)</div>
      <textarea className="w-full h-64 font-mono text-sm p-3 bg-surface-container-low"
        value={JSON.stringify(config, null, 2)}
        onChange={e => {
          try { update(JSON.parse(e.target.value)); }
          catch { /* ignore parse errors while typing */ }
        }} />
    </div>
  );
}
```

- [ ] **Step 4: Подключить все**

В `TaskEditorPage.tsx` → `TypeSpecificForm`:

```tsx
import CtfForm from '../../components/admin/task-forms/CtfForm';
import GitlabForm from '../../components/admin/task-forms/GitlabForm';
import SshLabForm from '../../components/admin/task-forms/SshLabForm';
// ...
case 'ctf': return <CtfForm config={cfg} update={updateConfig} />;
case 'ssh_lab': return <SshLabForm config={cfg} update={updateConfig} />;
case 'gitlab': return <GitlabForm config={cfg} update={updateConfig} />;
```

Убрать дефолтный fallback-`pre` (или оставить).

- [ ] **Step 5: Build + commit**

```bash
docker compose exec frontend npm run build
git add frontend/src/components/admin/task-forms/ frontend/src/pages/admin/TaskEditorPage.tsx
git commit -m "feat(frontend): ctf/ssh_lab/gitlab task forms"
```

---

# Phase 9 — Course editor UI

### Task 27: AdminCoursesPage — список курсов

**Files:**
- Modify: `frontend/src/pages/admin/AdminCoursesPage.tsx`

- [ ] **Step 1: Реализация**

```tsx
import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { api } from '../../api';
import Button from '../../components/Button';
import FormInput from '../../components/FormInput';
import type { AdminCourse } from '../../types';

export default function AdminCoursesPage() {
  const nav = useNavigate();
  const [courses, setCourses] = useState<AdminCourse[]>([]);
  const [creating, setCreating] = useState(false);
  const [newCourse, setNewCourse] = useState({ title: '', slug: '' });
  const [error, setError] = useState('');

  const load = () => api.adminContent.listCourses().then(setCourses)
                                     .catch(e => setError(e.message));
  useEffect(() => { load(); }, []);

  const toggleVisible = async (c: AdminCourse) => {
    try {
      await api.adminContent.patchCourse(c.id, { is_visible: !c.is_visible });
      load();
    } catch (e: any) { setError(e.message); }
  };

  const onCreate = async () => {
    try {
      const c = await api.adminContent.createCourse(newCourse);
      nav(`/admin/courses/${c.id}`);
    } catch (e: any) { setError(e.message); }
  };

  const onImport = async (file: File) => {
    try { await api.adminContent.importCourse(file, true); load(); }
    catch (e: any) { setError(e.message); }
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center gap-3">
        <h2 className="text-xl font-bold">Курсы</h2>
        <div className="flex-1" />
        <Button onClick={() => setCreating(true)}>Новый курс</Button>
        <label>
          <input type="file" accept=".zip" className="hidden"
                 onChange={e => e.target.files?.[0] && onImport(e.target.files[0])} />
          <span className="px-3 py-2 bg-surface-container-low cursor-pointer">Импорт</span>
        </label>
      </div>

      {error && <div className="text-error">{error}</div>}

      {creating && (
        <div className="border p-4 flex gap-3 items-end">
          <FormInput label="Title" value={newCourse.title}
                     onChange={v => setNewCourse({ ...newCourse, title: v })} />
          <FormInput label="Slug" value={newCourse.slug}
                     onChange={v => setNewCourse({ ...newCourse, slug: v })} />
          <Button onClick={onCreate}>Создать</Button>
          <Button onClick={() => setCreating(false)} variant="secondary">Отмена</Button>
        </div>
      )}

      <table className="w-full">
        <thead><tr>
          <th className="text-left">Title</th><th>Slug</th>
          <th>Order</th><th>Visible</th>
        </tr></thead>
        <tbody>
          {courses.map(c => (
            <tr key={c.id} className="hover:bg-surface-container-low">
              <td><Link to={`/admin/courses/${c.id}`}>{c.title}</Link></td>
              <td className="font-mono text-sm">{c.slug}</td>
              <td>{c.order}</td>
              <td>
                <label className="flex items-center gap-2">
                  <input type="checkbox" checked={c.is_visible}
                         onChange={() => toggleVisible(c)} />
                  {c.is_visible ? 'Visible' : 'Hidden'}
                </label>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 2: Build + commit**

```bash
docker compose exec frontend npm run build
git add frontend/src/pages/admin/AdminCoursesPage.tsx
git commit -m "feat(frontend): AdminCoursesPage with create/toggle/import"
```

---

### Task 28: CourseEditorPage — метаданные + список модулей + DnD + юниты + TaskPicker

Это самая крупная задача, разобьём на подзадачи внутри (каждый шаг = действие).

**Files:**
- Modify: `frontend/src/pages/admin/CourseEditorPage.tsx`
- Create: `frontend/src/components/admin/ModuleCard.tsx`
- Create: `frontend/src/components/admin/UnitRow.tsx`
- Create: `frontend/src/components/admin/TaskPicker.tsx`

- [ ] **Step 1: TaskPicker модалка**

`frontend/src/components/admin/TaskPicker.tsx`:

```tsx
import { useEffect, useState } from 'react';

import { api } from '../../api';
import Button from '../Button';
import FormInput from '../FormInput';
import FormSelect from '../FormSelect';
import type { AdminTask, TaskType } from '../../types';

export default function TaskPicker({ onPick, onClose }: {
  onPick: (task: AdminTask) => void; onClose: () => void;
}) {
  const [tasks, setTasks] = useState<AdminTask[]>([]);
  const [type, setType] = useState('');
  const [search, setSearch] = useState('');

  const load = () => api.adminContent.listTasks({
    type: type || undefined, search: search || undefined,
  }).then(setTasks);
  useEffect(() => { load(); }, [type]);

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-surface max-w-2xl w-full p-6 space-y-3">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-bold">Выбор таска</h3>
          <div className="flex-1" />
          <Button onClick={onClose} variant="secondary">Закрыть</Button>
        </div>
        <div className="flex gap-3 items-end">
          <FormSelect label="Тип" value={type} onChange={setType}
            options={['','theory','quiz','ctf','ssh_lab','gitlab']
              .map(t => ({ value: t, label: t || 'Все' }))} />
          <FormInput label="Поиск" value={search} onChange={setSearch}
                     onKeyDown={e => e.key === 'Enter' && load()} />
          <Button onClick={load}>Найти</Button>
        </div>
        <div className="max-h-96 overflow-auto">
          {tasks.map(t => (
            <div key={t.id}
                 className="p-2 hover:bg-surface-container-low cursor-pointer flex gap-3"
                 onClick={() => onPick(t)}>
              <span className="text-xs bg-surface-container-high px-2">{t.type}</span>
              <span>{t.title}</span>
              <span className="font-mono text-xs text-on-surface-variant">{t.slug}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: UnitRow**

`frontend/src/components/admin/UnitRow.tsx`:

```tsx
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

import { api } from '../../api';
import type { AdminTask, AdminUnit } from '../../types';

export default function UnitRow({ unit, task, onChange, onDelete }: {
  unit: AdminUnit; task?: AdminTask;
  onChange: (u: AdminUnit) => void; onDelete: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition } =
    useSortable({ id: unit.id });
  const style = { transform: CSS.Transform.toString(transform), transition };

  const toggleReq = async () => {
    const u = await api.adminContent.patchUnit(unit.id, { is_required: !unit.is_required });
    onChange(u);
  };

  return (
    <div ref={setNodeRef} style={style}
         className="flex items-center gap-3 p-2 bg-surface-container-low">
      <span {...attributes} {...listeners} className="cursor-grab">⋮⋮</span>
      <span className="text-xs bg-surface-container-high px-2">{task?.type}</span>
      <span className="flex-1">{task?.title || `Task ${unit.task_id}`}</span>
      <label className="flex items-center gap-1 text-sm">
        <input type="checkbox" checked={unit.is_required} onChange={toggleReq} />
        required
      </label>
      <button onClick={onDelete}>×</button>
    </div>
  );
}
```

- [ ] **Step 3: ModuleCard**

`frontend/src/components/admin/ModuleCard.tsx`:

```tsx
import { DndContext, DragEndEvent, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { SortableContext, arrayMove, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { useEffect, useState } from 'react';

import { api } from '../../api';
import Button from '../Button';
import FormInput from '../FormInput';
import type { AdminModule, AdminTask, AdminUnit } from '../../types';
import TaskPicker from './TaskPicker';
import UnitRow from './UnitRow';

export default function ModuleCard({ module, onChange, onDelete }: {
  module: AdminModule; onChange: (m: AdminModule) => void; onDelete: () => void;
}) {
  const [units, setUnits] = useState<AdminUnit[]>([]);
  const [tasks, setTasks] = useState<Record<number, AdminTask>>({});
  const [picker, setPicker] = useState(false);
  const [local, setLocal] = useState(module);
  const sensors = useSensors(useSensor(PointerSensor));

  const loadUnits = async () => {
    // Юниты сейчас отдаются через /api/modules/{id} (student endpoint),
    // но в этой задаче нам нужна структура only-admin. Используем GET /api/admin/content/courses/{id}
    // и вытаскиваем оттуда, либо новый endpoint. Для простоты — отдельный запрос:
    // TODO: сделать отдельный GET /api/admin/content/modules/{id} — добавить в Task 29.
    // Временно — пусто, заполнится из родителя через props.
  };
  useEffect(() => { setLocal(module); }, [module]);

  const saveMeta = async () => {
    const m = await api.adminContent.patchModule(module.id, {
      title: local.title, description: local.description,
      estimated_hours: local.estimated_hours, learning_outcomes: local.learning_outcomes,
    });
    onChange(m);
  };

  const addUnit = async (task: AdminTask) => {
    const u = await api.adminContent.createUnit(module.id, {
      task_id: task.id, unit_order: units.length + 1, is_required: true,
    });
    setUnits([...units, u]);
    setTasks({ ...tasks, [task.id]: task });
    setPicker(false);
  };

  const onDragEnd = async (e: DragEndEvent) => {
    if (!e.over || e.active.id === e.over.id) return;
    const oldIdx = units.findIndex(u => u.id === e.active.id);
    const newIdx = units.findIndex(u => u.id === e.over!.id);
    const next = arrayMove(units, oldIdx, newIdx);
    setUnits(next);
    await api.adminContent.reorderUnits(module.id,
      next.map((u, i) => ({ id: u.id, order: i + 1 })));
  };

  return (
    <div className="border p-4 space-y-3">
      <div className="flex gap-3 items-start">
        <div className="flex-1 space-y-2">
          <FormInput label="Title" value={local.title}
            onChange={v => setLocal({ ...local, title: v })} onBlur={saveMeta} />
          <FormInput label="Description" value={local.description}
            onChange={v => setLocal({ ...local, description: v })}
            onBlur={saveMeta} multiline />
          <FormInput label="Estimated hours" type="number"
            value={String(local.estimated_hours ?? '')}
            onChange={v => setLocal({ ...local, estimated_hours: v ? Number(v) : null })}
            onBlur={saveMeta} />
        </div>
        <Button onClick={onDelete} variant="danger">Удалить модуль</Button>
      </div>

      <div>
        <DndContext sensors={sensors} onDragEnd={onDragEnd}>
          <SortableContext items={units.map(u => u.id)} strategy={verticalListSortingStrategy}>
            {units.map(u => (
              <UnitRow key={u.id} unit={u} task={tasks[u.task_id]}
                onChange={patched => setUnits(units.map(x => x.id === u.id ? patched : x))}
                onDelete={async () => {
                  await api.adminContent.deleteUnit(u.id);
                  setUnits(units.filter(x => x.id !== u.id));
                }} />
            ))}
          </SortableContext>
        </DndContext>
        <Button onClick={() => setPicker(true)}>+ Добавить юнит</Button>
      </div>

      {picker && <TaskPicker onPick={addUnit} onClose={() => setPicker(false)} />}
    </div>
  );
}
```

- [ ] **Step 4: Добавить GET /api/admin/content/modules/{id} (ЮНИТЫ + ТАСКИ)**

В `backend/routers/admin_content.py`:

```python
class UnitWithTaskOut(BaseModel):
    id: int
    module_id: int
    task_id: int
    unit_order: int
    is_required: bool
    task_slug: str
    task_title: str
    task_type: TaskType

    model_config = ConfigDict(from_attributes=False)


@router.get("/modules/{module_id}/full")
async def get_module_full(module_id: int, db: AsyncSession = Depends(get_db)):
    m = await db.execute(
        select(Module).options(selectinload(Module.units)
                                .selectinload(ModuleUnit.task))
        .where(Module.id == module_id)
    )
    module = m.scalars().unique().one_or_none()
    if not module:
        raise HTTPException(404, "Module not found")
    return {
        "module": ModuleOutAdmin.model_validate(module).model_dump(),
        "units": [
            {
                "id": u.id, "module_id": u.module_id, "task_id": u.task_id,
                "unit_order": u.unit_order, "is_required": u.is_required,
                "task_slug": u.task.slug, "task_title": u.task.title,
                "task_type": u.task.type.value,
            } for u in sorted(module.units, key=lambda x: x.unit_order)
        ],
    }
```

И в `frontend/src/api.ts`:

```typescript
getModuleFull: (id: number) =>
  request<{ module: AdminModule; units: (AdminUnit & {
    task_slug: string; task_title: string; task_type: TaskType;
  })[] }>(`/admin/content/modules/${id}/full`),
```

В `ModuleCard.tsx` в `useEffect` после setLocal добавить:

```tsx
useEffect(() => {
  api.adminContent.getModuleFull(module.id).then(r => {
    setUnits(r.units);
    const tmap: Record<number, AdminTask> = {};
    r.units.forEach(u => {
      tmap[u.task_id] = { id: u.task_id, slug: u.task_slug, title: u.task_title,
        type: u.task_type, description: '', order: 0, config: {},
        author_id: null, updated_at: '' } as AdminTask;
    });
    setTasks(tmap);
  });
}, [module.id]);
```

- [ ] **Step 5: CourseEditorPage**

`frontend/src/pages/admin/CourseEditorPage.tsx`:

```tsx
import { DndContext, DragEndEvent, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { SortableContext, arrayMove, verticalListSortingStrategy, useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { api } from '../../api';
import ModuleCard from '../../components/admin/ModuleCard';
import Button from '../../components/Button';
import FormInput from '../../components/FormInput';
import type { AdminCourse, AdminModule } from '../../types';

function SortableModule({ m, onChange, onDelete }: {
  m: AdminModule; onChange: (x: AdminModule) => void; onDelete: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition } =
    useSortable({ id: m.id });
  const style = { transform: CSS.Transform.toString(transform), transition };
  return (
    <div ref={setNodeRef} style={style}>
      <div {...attributes} {...listeners}
           className="cursor-grab text-xs opacity-50">⋮⋮ drag module</div>
      <ModuleCard module={m} onChange={onChange} onDelete={onDelete} />
    </div>
  );
}

export default function CourseEditorPage() {
  const { id } = useParams<{ id: string }>();
  const nav = useNavigate();
  const [course, setCourse] = useState<AdminCourse | null>(null);
  const [modules, setModules] = useState<AdminModule[]>([]);
  const [error, setError] = useState('');
  const sensors = useSensors(useSensor(PointerSensor));

  const load = async () => {
    if (!id) return;
    try {
      const all = await api.adminContent.listCourses();
      const c = all.find(x => x.id === Number(id));
      setCourse(c || null);
      // Модули получаем через /api/courses/{id} (student endpoint) —
      // он отдаёт структуру с модулями. Но там фильтр по is_visible.
      // Используем отдельный admin endpoint — добавим в следующем шаге.
      const r = await fetch(`/api/admin/content/courses/${id}/modules-list`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      setModules(await r.json());
    } catch (e: any) { setError(e.message); }
  };
  useEffect(() => { load(); }, [id]);

  const patchCourse = async (patch: Partial<AdminCourse>) => {
    if (!course) return;
    try {
      const u = await api.adminContent.patchCourse(course.id, patch);
      setCourse(u);
    } catch (e: any) { setError(e.message); }
  };

  const addModule = async () => {
    if (!course) return;
    const m = await api.adminContent.createModule(course.id, {
      title: 'Новый модуль', order: modules.length + 1,
    });
    setModules([...modules, m]);
  };

  const onDelete = async () => {
    if (!course) return;
    if (course.is_visible) { alert('Сначала скройте курс.'); return; }
    if (!confirm('Удалить курс?')) return;
    await api.adminContent.deleteCourse(course.id);
    nav('/admin/courses');
  };

  const onExport = async (bundle: boolean) => {
    if (!course) return;
    const blob = await api.adminContent.exportCourse(course.id, bundle);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url;
    a.download = `course-${course.slug}.zip`; a.click();
    URL.revokeObjectURL(url);
  };

  const onDragEnd = async (e: DragEndEvent) => {
    if (!e.over || e.active.id === e.over.id || !course) return;
    const oldIdx = modules.findIndex(m => m.id === e.active.id);
    const newIdx = modules.findIndex(m => m.id === e.over!.id);
    const next = arrayMove(modules, oldIdx, newIdx);
    setModules(next);
    await api.adminContent.reorderModules(course.id,
      next.map((m, i) => ({ id: m.id, order: i + 1 })));
  };

  if (!course) return <div className="p-6">Загрузка…</div>;

  return (
    <div className="p-6 space-y-6 flex gap-6">
      <div className="w-80 space-y-3">
        <h2 className="text-xl font-bold">{course.title}</h2>
        <FormInput label="Title" value={course.title}
                   onChange={v => setCourse({ ...course, title: v })}
                   onBlur={() => patchCourse({ title: course.title })} />
        <FormInput label="Slug" value={course.slug}
                   onChange={v => setCourse({ ...course, slug: v })}
                   onBlur={() => patchCourse({ slug: course.slug })} />
        <FormInput label="Description" value={course.description}
                   onChange={v => setCourse({ ...course, description: v })}
                   onBlur={() => patchCourse({ description: course.description })} multiline />
        <FormInput label="Order" type="number" value={String(course.order)}
                   onChange={v => setCourse({ ...course, order: Number(v) })}
                   onBlur={() => patchCourse({ order: course.order })} />
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={course.is_visible}
                 onChange={e => patchCourse({ is_visible: e.target.checked })} />
          Visible to students
        </label>
        <div className="space-y-2 pt-4 border-t">
          <Button onClick={() => onExport(false)}>Экспорт (структура)</Button>
          <Button onClick={() => onExport(true)}>Экспорт (bundle)</Button>
          <Button onClick={onDelete} variant="danger">Удалить</Button>
        </div>
      </div>

      <div className="flex-1 space-y-4">
        {error && <div className="text-error">{error}</div>}
        <DndContext sensors={sensors} onDragEnd={onDragEnd}>
          <SortableContext items={modules.map(m => m.id)}
                           strategy={verticalListSortingStrategy}>
            {modules.map(m => (
              <SortableModule key={m.id} m={m}
                onChange={u => setModules(modules.map(x => x.id === u.id ? u : x))}
                onDelete={async () => {
                  await api.adminContent.deleteModule(m.id);
                  setModules(modules.filter(x => x.id !== m.id));
                }} />
            ))}
          </SortableContext>
        </DndContext>
        <Button onClick={addModule}>+ Модуль</Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Admin endpoint GET /courses/{id}/modules-list**

В `backend/routers/admin_content.py`:

```python
@router.get("/courses/{course_id}/modules-list", response_model=list[ModuleOutAdmin])
async def list_course_modules(course_id: int, db: AsyncSession = Depends(get_db)):
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    rows = await db.execute(select(Module).where(Module.course_id == course_id)
                             .order_by(Module.order))
    return rows.scalars().all()
```

- [ ] **Step 7: Build + manual smoke + commit**

```bash
docker compose restart backend && docker compose exec frontend npm run build
git add backend/routers/admin_content.py \
        frontend/src/pages/admin/CourseEditorPage.tsx \
        frontend/src/components/admin/ \
        frontend/src/api.ts
git commit -m "feat(frontend): CourseEditorPage with DnD modules/units and TaskPicker"
```

---

# Phase 10 — Cleanup

### Task 29: Снести seed.py, deploy-labs.sh, migrate-tracks-to-courses.py, папку tasks/

**Files:**
- Delete: `backend/seed.py`
- Delete: `backend/tests/test_seed_courses.py`
- Delete: `scripts/deploy-labs.sh`
- Delete: `scripts/migrate-tracks-to-courses.py`
- Delete: `tasks/` (вся папка)

- [ ] **Step 1: Проверить, что ничего не импортирует seed.py**

Run: `grep -rn 'from seed\|import seed\|seed_tasks\|seed_courses' backend/ --exclude-dir=__pycache__ --exclude=seed.py --exclude-dir=tests`
Expected: пусто (или только из удаляемого test_seed_courses.py).

- [ ] **Step 2: Удалить файлы**

```bash
rm backend/seed.py
rm backend/tests/test_seed_courses.py
rm scripts/deploy-labs.sh
rm scripts/migrate-tracks-to-courses.py
rm -rf tasks/
```

- [ ] **Step 3: Прогнать тесты бэка — убедиться, что ничего не сломалось**

Run: `docker compose exec backend pytest -v`
Expected: все PASS.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: remove YAML seed pipeline now that DB is source of truth

- delete backend/seed.py + test_seed_courses.py
- delete scripts/deploy-labs.sh and scripts/migrate-tracks-to-courses.py
- delete tasks/ folder (all content lives in DB now)
"
```

---

### Task 30: Обновить README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Удалить разделы**

В `README.md`:
- Удалить раздел «Скрипт deploy-labs.sh» (строки ~136–153).
- Удалить раздел «Добавление нового CTF-задания» (строки ~189–212).
- В разделе «Быстрый старт» удалить шаг 3 (`./scripts/deploy-labs.sh`).
- В разделе «Структура проекта» удалить упоминания `tasks/` и `seed.py`.
- В разделе «Типичные проблемы» удалить блок «CTF-задания не появляются в каталоге» (связанный с `--seed`).

- [ ] **Step 2: Добавить новый раздел**

После «Быстрый старт» вставить:

```markdown
## Управление контентом

Все курсы, модули, юниты и таски управляются через админ-панель:

```
http://lms.lab.local/admin/courses
http://lms.lab.local/admin/tasks
```

### CTF-таски

Dockerfile'ы уязвимых приложений **не хранятся в этом репозитории**. Автор задания:

1. Пишет Dockerfile и собирает образ у себя / в своём CI.
2. Пушит образ в любой доступный Docker registry (Docker Hub, GHCR, приватный).
3. В UI → Таски → Новый таск (type=ctf) заполняет поля:
   - `docker_image`: ссылка на образ (`myuser/lms-sqli-basic:v2`)
   - `flag`: plaintext-флаг (хэшируется в SHA256 на бэкенде при сохранении)
   - `port`, `ttl_minutes`, `difficulty`

При запуске студентом существующий `docker_manager` делает `docker pull` и `docker run`.

### Импорт/экспорт

На страницах курсов и тасков есть кнопки «Экспорт» (скачать zip) и «Импорт»
(загрузить zip). Формат: ZIP с YAML-манифестом внутри.

Курс можно экспортировать отдельно (только структура) или `bundle=true` —
с включением всех referenced тасков.
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs(readme): remove YAML pipeline, document admin UI"
```

---

### Task 31: smoke-course-flow.sh — расширить под новый UI-флоу

**Files:**
- Modify: `scripts/smoke-course-flow.sh`

- [ ] **Step 1: Прочитать текущий скрипт**

Run: `cat scripts/smoke-course-flow.sh`
Понять, какие эндпоинты он дёргает.

- [ ] **Step 2: Добавить E2E-секцию admin CRUD**

В конец скрипта добавить (скелет; точные URL-пути и переменные взять из существующего скрипта):

```bash
echo "=== Admin CRUD smoke ==="
TOKEN=$(curl -s -X POST "$BASE/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' | jq -r .access_token)

# Create task
curl -s -X POST "$BASE/api/admin/content/tasks" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"slug":"smoke-theory","title":"Smoke","type":"theory","config":{"content_kind":"text","content":"hi"}}'

# Create course
COURSE_ID=$(curl -s -X POST "$BASE/api/admin/content/courses" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"slug":"smoke-course","title":"Smoke Course"}' | jq -r .id)

# Publish
curl -s -X PATCH "$BASE/api/admin/content/courses/$COURSE_ID" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"is_visible":true}'

# Verify student sees it
curl -s "$BASE/api/courses" -H "Authorization: Bearer $TOKEN" \
  | jq -e '.[] | select(.slug=="smoke-course")'

# Cleanup
curl -s -X PATCH "$BASE/api/admin/content/courses/$COURSE_ID" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"is_visible":false}'
curl -s -X DELETE "$BASE/api/admin/content/courses/$COURSE_ID" \
  -H "Authorization: Bearer $TOKEN"

TASK_ID=$(curl -s "$BASE/api/admin/content/tasks?search=smoke-theory" \
  -H "Authorization: Bearer $TOKEN" | jq -r '.[0].id')
curl -s -X DELETE "$BASE/api/admin/content/tasks/$TASK_ID" \
  -H "Authorization: Bearer $TOKEN"

echo "=== Admin CRUD smoke OK ==="
```

- [ ] **Step 3: Прогнать**

Run: `bash scripts/smoke-course-flow.sh`
Expected: `Admin CRUD smoke OK` в конце.

- [ ] **Step 4: Commit**

```bash
git add scripts/smoke-course-flow.sh
git commit -m "test(smoke): extend smoke-course-flow with admin CRUD"
```

---

### Task 32: Финальная проверка и PR-описание

- [ ] **Step 1: Прогнать весь бэк-тест-сьют**

Run: `docker compose exec backend pytest -v`
Expected: 0 failures.

- [ ] **Step 2: Прогнать фронт-билд**

Run: `docker compose exec frontend npm run build`
Expected: success.

- [ ] **Step 3: Прогнать smoke**

Run: `bash scripts/smoke-course-flow.sh`
Expected: success.

- [ ] **Step 4: Проверить миграции с чистой БД**

```bash
docker compose down -v
docker compose up --build -d
sleep 10
docker compose exec backend pytest -v
```

Expected: миграции прошли, тесты зелёные, дефолтный админ создан.

- [ ] **Step 5: Создать PR**

Тело PR обязательно должно содержать:

```
## BREAKING CHANGE: Content migration required before merge

Эта ветка переводит источник правды контента из YAML-файлов (`tasks/`) в БД.
Папка `tasks/` и seed-скрипты удалены.

**Каждому оператору на каждом инстансе (prod/staging/dev) перед pull этой ветки:**

1. `./scripts/deploy-labs.sh --seed` — залить текущий YAML-контент в БД
2. Сделать backup БД: `docker compose exec postgres pg_dump -U lms lms > backup.sql`
3. Pull этой ветки + `docker compose up --build -d`
4. Миграция накатится автоматически на старте backend

После этого ВЕСЬ контент (курсы, модули, юниты, таски) редактируется через
/admin/courses и /admin/tasks.
```

---

# Self-review checklist (выполнить автору плана)

1. **Spec coverage:**
   - Скоуп C (все типы, без Dockerfile) → ✓ Tasks 22–26 (type-specific формы), Dockerfile не хранится (только docker_image в CtfForm/SshLabForm).
   - БД — источник правды + удаление YAML → ✓ Task 29.
   - ZIP-бандлы task/course + import_tasks → ✓ Tasks 17, 18.
   - `is_visible` на курсе, студент видит только visible → ✓ Tasks 1, 14, 16.
   - Flag hashing → ✓ Task 5, интегрирован в 9, 12, 17.
   - Удаление таска, используемого в курсе — 409 → ✓ Task 13.
   - Удаление видимого курса блокируется → ✓ Task 14.
   - Reorder модулей и юнитов → ✓ Task 15, интегрирован в UI в 28.
   - Slug-валидация → ✓ Task 3 schema + Task 4 utility; клиентская slugify в TaskEditor.
   - Zip-slip / размер → ✓ Tasks 6, 7.
   - Конкурентность last-write-wins, draft/версии out of scope → ✓ (никаких дополнительных полей в миграции).
   - README + smoke → ✓ Tasks 30, 31.

2. **Placeholder scan:** поиск «TBD», «TODO», «implement later» в плане — один `TODO` комментарий в черновике ModuleCard Step 2 закрыт шагом Task 28 Step 4/6 (новый endpoint `/modules/{id}/full` и `/courses/{id}/modules-list`).

3. **Type consistency:**
   - `AdminTask.type` совпадает с enum `TaskType` в backend (`'theory'|'quiz'|'ctf'|'gitlab'|'ssh_lab'`).
   - `reorderModules/reorderUnits` body — `{id, order}` и на бэке (`ReorderItem`), и на фронте.
   - Ресурсы админа возвращают `AdminCourse | AdminModule | AdminUnit` с совпадающими полями с SQLAlchemy-моделями.

План готов.
