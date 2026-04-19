# Manual Review & File Uploads Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dodat' manual review + file uploads — студент может прикрепить файлы и/или текст к сабмишену; преподаватель проверяет через очередь и ставит вердикт с комментарием.

**Architecture:** Без новых TaskType'ов. Флаги в `task.config` (`review_mode`, `file_upload`, `answer_text`). Новая таблица `submission_files` + 3 колонки в `task_submissions`. Файлы — в локальном volume `/app/uploads`, скачивание через auth-роуты. Новый общий роутер `/api/submissions` + `/api/admin/review`.

**Tech Stack:** FastAPI 0.115, SQLAlchemy 2.0 async, Alembic 1.14, PostgreSQL 16, React 18 + Vite + Tailwind, pytest+httpx для тестов.

**Reference spec:** [docs/superpowers/specs/2026-04-19-manual-review-and-file-uploads-design.md](../specs/2026-04-19-manual-review-and-file-uploads-design.md).

## Project notes (prerequisite reading for implementer)

- Stack: FastAPI + SQLAlchemy async + Alembic, PostgreSQL, frontend React/Vite.
- Все роутеры в `backend/routers/`, бизнес-логика в `backend/services/`.
- Тесты лежат в `backend/tests/`. Паттерн: `httpx.AsyncClient(transport=ASGITransport(app))` + прямой импорт `app` из `main`. Фикстура `_fresh_engine_per_test` (dispose engine вокруг теста) используется почти везде. Маркер `pytestmark = pytest.mark.anyio`.
- Auth: JWT через `auth.create_token(user_id, role)`; в тестах хедер `Authorization: Bearer <token>`. `require_admin` для админских эндпоинтов, `get_current_user` для студенческих.
- Миграции: `backend/alembic/versions/`, последовательные `0001…0004`. Следующая будет `0005`.
- Frontend: компоненты в `frontend/src/components`, страницы в `frontend/src/pages`, админ-подпапки уже есть. HTTP-клиент — `frontend/src/api.ts`, объект `api`. Маршрутизация — `react-router-dom` v6.
- Тестов фронта нет — проверяем руками через `docker compose up` + браузер. В плане проверочные шаги стоят в конце.

## File Structure

**Backend:**
- Create `backend/alembic/versions/0005_manual_review_and_uploads.py` — миграция.
- Modify `backend/models.py` — новые колонки + `SubmissionFile` + relationship.
- Modify `backend/config.py` — uploads-настройки.
- Modify `backend/schemas.py` — Pydantic-схемы для submissions/review.
- Create `backend/services/uploads.py` — санитизация имён, сохранение, удаление, стриминг.
- Create `backend/routers/submissions.py` — студенческий роутер.
- Create `backend/routers/admin_review.py` — админский роутер очереди + вердикта.
- Modify `backend/routers/quiz.py` — учесть `review_mode=manual` (auto_score в details, статус pending).
- Modify `backend/main.py` — подключение новых роутеров.
- Modify `backend/tests/conftest.py` — добавить фикстуру чистки `/tmp/uploads`.
- Create backend tests: `test_uploads_service.py`, `test_submissions_student.py`, `test_admin_review.py`, `test_manual_quiz.py`.

**Frontend:**
- Modify `frontend/src/api.ts` — новые методы.
- Create `frontend/src/components/FileUploader.tsx`.
- Create `frontend/src/components/SubmissionHistory.tsx`.
- Modify `frontend/src/pages/ChallengeDetailsPage.tsx` — блок «Сдача работы» + плашка статуса.
- Create `frontend/src/pages/admin/AdminReviewQueuePage.tsx`.
- Create `frontend/src/pages/admin/AdminReviewDetailPage.tsx`.
- Modify `frontend/src/components/Sidebar.tsx` — пункт «Проверка работ» + счётчик.
- Modify `frontend/src/App.tsx` (или место с router-config) — регистрация маршрутов админки.

**Infra:**
- Modify `docker-compose.yml` — volume `./uploads:/app/uploads` на backend.
- Modify `.env` (опционально) — документация `UPLOADS_DIR`.

---

## Phase 1 — DB schema

### Task 1: Alembic migration 0005

**Files:**
- Create: `backend/alembic/versions/0005_manual_review_and_uploads.py`

- [ ] **Step 1: Написать миграцию**

```python
"""add manual review and file uploads

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-19 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "task_submissions",
        sa.Column("reviewer_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
    )
    op.add_column(
        "task_submissions",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "task_submissions",
        sa.Column("review_comment", sa.Text(), nullable=True),
    )

    op.create_table(
        "submission_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "submission_id",
            sa.Integer(),
            sa.ForeignKey("task_submissions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("stored_path", sa.String(length=500), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_submission_files_submission_id", "submission_files", ["submission_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_submission_files_submission_id", table_name="submission_files")
    op.drop_table("submission_files")
    op.drop_column("task_submissions", "review_comment")
    op.drop_column("task_submissions", "reviewed_at")
    op.drop_column("task_submissions", "reviewer_id")
```

- [ ] **Step 2: Применить миграцию на dev-БД**

Run: `docker compose exec backend alembic upgrade head`
Expected: `Running upgrade 0004 -> 0005, add manual review and file uploads`

- [ ] **Step 3: Проверить rollback**

Run:
```
docker compose exec backend alembic downgrade 0004
docker compose exec backend alembic upgrade head
```
Expected: оба шага без ошибок.

- [ ] **Step 4: Commit**

```bash
git add backend/alembic/versions/0005_manual_review_and_uploads.py
git commit -m "db(migration): add manual review columns and submission_files table"
```

---

### Task 2: ORM model updates

**Files:**
- Modify: `backend/models.py`

- [ ] **Step 1: Добавить `SubmissionFile` и колонки в `TaskSubmission`**

В `backend/models.py`:

```python
class TaskSubmission(Base):
    __tablename__ = "task_submissions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    status = Column(Enum(SubmissionStatus), default=SubmissionStatus.pending)
    details = Column(JSONB, default=dict)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_comment = Column(Text, nullable=True)

    user = relationship("User", back_populates="submissions", foreign_keys=[user_id])
    task = relationship("Task", back_populates="submissions")
    reviewer = relationship("User", foreign_keys=[reviewer_id])
    files = relationship(
        "SubmissionFile",
        back_populates="submission",
        cascade="all, delete-orphan",
    )


class SubmissionFile(Base):
    __tablename__ = "submission_files"

    id = Column(Integer, primary_key=True)
    submission_id = Column(
        Integer,
        ForeignKey("task_submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename = Column(String(255), nullable=False)
    stored_path = Column(String(500), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    content_type = Column(String(100), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    submission = relationship("TaskSubmission", back_populates="files")
```

Заменить существующий класс `TaskSubmission` и дописать `SubmissionFile` в конец файла.

- [ ] **Step 2: Smoke — backend стартует**

Run: `docker compose restart backend && docker compose logs --tail 50 backend`
Expected: нет трейсбеков, `Application startup complete`.

- [ ] **Step 3: Commit**

```bash
git add backend/models.py
git commit -m "models: add SubmissionFile and review columns to TaskSubmission"
```

---

## Phase 2 — Config, storage, uploads service

### Task 3: Uploads settings in config.py

**Files:**
- Modify: `backend/config.py`

- [ ] **Step 1: Добавить три настройки**

В `backend/config.py` заменить класс `Settings` на:

```python
from pydantic_settings import BaseSettings


DEFAULT_ALLOWED_EXT = [
    "pdf", "png", "jpg", "jpeg", "zip", "txt", "md", "docx", "py", "js", "ts",
]


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://lms:lms@postgres:5432/lms"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    domain: str = "lab.local"
    traefik_network: str = "lms_network"
    tasks_dir: str = "/tasks"
    container_check_timeout: int = 5
    uploads_dir: str = "/app/uploads"
    uploads_max_size_mb: int = 20
    uploads_allowed_ext_default: list[str] = DEFAULT_ALLOWED_EXT

    class Config:
        env_file = ".env"


settings = Settings()
```

- [ ] **Step 2: Smoke**

Run: `docker compose restart backend`
Expected: нет ошибок в логах.

- [ ] **Step 3: Commit**

```bash
git add backend/config.py
git commit -m "config: add uploads settings"
```

---

### Task 4: docker-compose volume

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: Добавить volume backend + named volume**

В `docker-compose.yml`, секция `backend.volumes`:

```yaml
  backend:
    build: ./backend
    env_file: .env
    volumes:
      - ./backend:/app
      - /var/run/docker.sock:/var/run/docker.sock
      - ./tasks:/tasks:ro
      - uploads_data:/app/uploads
```

В конец файла секция `volumes`:

```yaml
volumes:
  postgres_data:
  uploads_data:
```

- [ ] **Step 2: Пересоздать backend-контейнер**

Run: `docker compose up -d backend`
Expected: backend поднимается; `docker compose exec backend ls -la /app/uploads` показывает пустой каталог.

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml
git commit -m "infra: add uploads_data volume for backend"
```

---

### Task 5: Uploads service — скелет + тесты санитайза

**Files:**
- Create: `backend/services/uploads.py`
- Create: `backend/tests/test_uploads_service.py`

- [ ] **Step 1: Написать тест санитизации имени файла**

Create `backend/tests/test_uploads_service.py`:

```python
"""Unit tests for upload filename sanitization and validation helpers."""
import pytest

from services.uploads import sanitize_filename, validate_upload_config

pytestmark = pytest.mark.anyio


def test_sanitize_strips_path_separators():
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("a/b/c.txt") == "c.txt"
    assert sanitize_filename("x\\y\\z.pdf") == "z.pdf"


def test_sanitize_keeps_unicode():
    assert sanitize_filename("отчёт.pdf") == "отчёт.pdf"


def test_sanitize_truncates():
    name = "a" * 300 + ".pdf"
    result = sanitize_filename(name)
    assert len(result) <= 200
    assert result.endswith(".pdf")


def test_sanitize_rejects_empty_after_clean():
    assert sanitize_filename("") == "file"
    assert sanitize_filename("/") == "file"
    assert sanitize_filename("   ") == "file"


def test_validate_upload_config_rejects_disabled():
    cfg = {}
    with pytest.raises(ValueError, match="uploads_disabled"):
        validate_upload_config(cfg, file_count=1, total_size_bytes=0)


def test_validate_upload_config_required_empty():
    cfg = {"file_upload": {"enabled": True, "required": True, "max_files": 5, "max_size_mb": 20, "allowed_ext": ["pdf"]}}
    with pytest.raises(ValueError, match="file_required"):
        validate_upload_config(cfg, file_count=0, total_size_bytes=0)


def test_validate_upload_config_too_many_files():
    cfg = {"file_upload": {"enabled": True, "required": False, "max_files": 2, "max_size_mb": 20, "allowed_ext": ["pdf"]}}
    with pytest.raises(ValueError, match="too_many_files"):
        validate_upload_config(cfg, file_count=3, total_size_bytes=0)
```

- [ ] **Step 2: Написать минимальный `services/uploads.py`**

Create `backend/services/uploads.py`:

```python
"""Upload handling: filename sanitization, config validation, storage, streaming."""
from __future__ import annotations

import os
import secrets
import shutil
import unicodedata
from pathlib import Path
from typing import Iterable

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models import SubmissionFile, TaskSubmission

_MAX_NAME_LEN = 200
_CHUNK_SIZE = 1 << 20  # 1 MiB


def sanitize_filename(name: str) -> str:
    """Strip path separators / control chars, NFC normalize, truncate."""
    if not name:
        return "file"
    cleaned = name.replace("\\", "/").split("/")[-1]
    cleaned = unicodedata.normalize("NFC", cleaned)
    cleaned = "".join(ch for ch in cleaned if ch.isprintable()).strip()
    if not cleaned:
        return "file"
    if len(cleaned) > _MAX_NAME_LEN:
        stem = Path(cleaned).stem
        suffix = Path(cleaned).suffix
        keep = _MAX_NAME_LEN - len(suffix)
        cleaned = stem[: max(keep, 1)] + suffix
    return cleaned


def _upload_cfg(task_config: dict) -> dict | None:
    cfg = (task_config or {}).get("file_upload")
    if not cfg or not cfg.get("enabled"):
        return None
    return cfg


def validate_upload_config(
    task_config: dict, file_count: int, total_size_bytes: int
) -> None:
    """Raise ValueError on limit violation. file_count=0 is allowed unless required."""
    cfg = _upload_cfg(task_config)
    if cfg is None:
        if file_count > 0:
            raise ValueError("uploads_disabled")
        return

    if cfg.get("required") and file_count == 0:
        raise ValueError("file_required")

    max_files = int(cfg.get("max_files", 5))
    if file_count > max_files:
        raise ValueError(f"too_many_files:{max_files}")

    max_mb = int(cfg.get("max_size_mb", settings.uploads_max_size_mb))
    if any_size_over(total_size_bytes, file_count, max_mb):
        raise ValueError(f"file_too_large:{max_mb}")


def any_size_over(total_size_bytes: int, file_count: int, max_mb: int) -> bool:
    # Total bound — per-file enforced during streaming.
    return total_size_bytes > file_count * max_mb * 1024 * 1024


def validate_file(task_config: dict, filename: str, size_bytes: int) -> None:
    cfg = _upload_cfg(task_config)
    if cfg is None:
        raise ValueError("uploads_disabled")

    max_mb = int(cfg.get("max_size_mb", settings.uploads_max_size_mb))
    if size_bytes > max_mb * 1024 * 1024:
        raise ValueError(f"file_too_large:{max_mb}")

    allowed = [e.lower() for e in cfg.get("allowed_ext") or settings.uploads_allowed_ext_default]
    ext = Path(filename).suffix.lstrip(".").lower()
    if ext not in allowed:
        raise ValueError(f"ext_not_allowed:{ext}")


async def save_submission_files(
    submission: TaskSubmission,
    task_config: dict,
    files: Iterable[UploadFile],
    db: AsyncSession,
) -> list[SubmissionFile]:
    """Stream-save each UploadFile to disk, insert SubmissionFile rows, return list."""
    sub_dir = Path(settings.uploads_dir) / str(submission.id)
    sub_dir.mkdir(parents=True, exist_ok=True)

    saved: list[SubmissionFile] = []
    try:
        for upload in files:
            original = sanitize_filename(upload.filename or "file")
            stored_name = f"{secrets.token_hex(8)}_{original}"
            dst = sub_dir / stored_name
            size = 0
            with dst.open("wb") as fp:
                while True:
                    chunk = await upload.read(_CHUNK_SIZE)
                    if not chunk:
                        break
                    size += len(chunk)
                    fp.write(chunk)
            validate_file(task_config, original, size)

            rec = SubmissionFile(
                submission_id=submission.id,
                filename=original,
                stored_path=str(dst.relative_to(settings.uploads_dir)),
                size_bytes=size,
                content_type=upload.content_type,
            )
            db.add(rec)
            saved.append(rec)
        await db.flush()
        return saved
    except Exception:
        # Roll back files on disk if any step failed
        shutil.rmtree(sub_dir, ignore_errors=True)
        raise


def delete_submission_files(submission_id: int) -> None:
    sub_dir = Path(settings.uploads_dir) / str(submission_id)
    shutil.rmtree(sub_dir, ignore_errors=True)


def absolute_stored_path(stored_path: str) -> Path:
    """Resolve a file path, guarding against traversal outside UPLOADS_DIR."""
    base = Path(settings.uploads_dir).resolve()
    target = (base / stored_path).resolve()
    if not str(target).startswith(str(base) + os.sep) and target != base:
        raise ValueError("path_escape")
    return target
```

- [ ] **Step 3: Запустить тесты**

Run: `docker compose exec backend pytest tests/test_uploads_service.py -v`
Expected: все `test_sanitize_*` и `test_validate_upload_config_*` — PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/services/uploads.py backend/tests/test_uploads_service.py
git commit -m "services: add uploads service with sanitization and validation"
```

---

## Phase 3 — Student submissions router

### Task 6: Pydantic schemas

**Files:**
- Modify: `backend/schemas.py`

- [ ] **Step 1: Дописать схемы в конец `backend/schemas.py`**

```python
# --- Submissions (generic, with files) ---
class SubmissionFileOut(BaseModel):
    id: int
    filename: str
    size_bytes: int
    content_type: str | None = None

    class Config:
        from_attributes = True


class SubmissionDetail(BaseModel):
    id: int
    user_id: int
    task_id: int
    status: SubmissionStatus
    details: dict
    submitted_at: datetime
    reviewer_id: int | None = None
    reviewed_at: datetime | None = None
    review_comment: str | None = None
    files: list[SubmissionFileOut] = []

    class Config:
        from_attributes = True


# --- Admin review ---
class ReviewQueueItem(BaseModel):
    submission_id: int
    task_id: int
    task_title: str
    user_id: int
    username: str
    user_full_name: str
    submitted_at: datetime
    course_id: int | None = None
    course_title: str | None = None


class ReviewQueueResponse(BaseModel):
    items: list[ReviewQueueItem]
    total: int
    page: int
    per_page: int


class ReviewVerdict(BaseModel):
    status: SubmissionStatus  # success | fail
    comment: str = ""
```

- [ ] **Step 2: Smoke**

Run: `docker compose exec backend python -c "import schemas"`
Expected: без ошибок.

- [ ] **Step 3: Commit**

```bash
git add backend/schemas.py
git commit -m "schemas: add submission and review-queue models"
```

---

### Task 7: Student submissions router — happy path test

**Files:**
- Create: `backend/tests/test_submissions_student.py`

- [ ] **Step 1: Написать первый тест: создание manual сабмишена с файлом → pending**

Create `backend/tests/test_submissions_student.py`:

```python
"""Tests for student submissions router (file upload + manual review)."""
import io

import pytest
from httpx import ASGITransport, AsyncClient

from auth import create_token, hash_password
from database import async_session, engine
from main import app
from models import SubmissionFile, Task, TaskSubmission, TaskType, User, UserRole

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
async def _fresh_engine_per_test():
    await engine.dispose()
    yield
    await engine.dispose()


async def _seed_manual_theory() -> dict:
    async with async_session() as db:
        user = User(
            username="student_sub_1",
            password_hash=hash_password("x"),
            full_name="Stu",
            role=UserRole.student,
        )
        task = Task(
            slug="theory-manual-1",
            title="Manual theory",
            description="",
            type=TaskType.theory,
            config={
                "review_mode": "manual",
                "file_upload": {
                    "enabled": True,
                    "max_files": 3,
                    "max_size_mb": 5,
                    "allowed_ext": ["pdf", "txt"],
                    "required": True,
                },
                "answer_text": {"enabled": True, "required": False},
            },
        )
        db.add_all([user, task])
        await db.commit()
        await db.refresh(user)
        await db.refresh(task)
        token = create_token(user.id, user.role.value)
        return {"user_id": user.id, "task_id": task.id, "token": token}


async def test_manual_submission_with_file_becomes_pending():
    seed = await _seed_manual_theory()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        files = [("files", ("report.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf"))]
        data = {"answer_text": "see attached"}
        resp = await ac.post(
            f"/api/submissions/{seed['task_id']}",
            data=data,
            files=files,
            headers={"Authorization": f"Bearer {seed['token']}"},
        )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "pending"
    assert len(body["files"]) == 1
    assert body["files"][0]["filename"] == "report.pdf"

    async with async_session() as db:
        sub = await db.get(TaskSubmission, body["id"])
        assert sub.status.value == "pending"
        assert sub.details.get("answer_text") == "see attached"
```

- [ ] **Step 2: Запустить — ожидается FAIL (роутера нет)**

Run: `docker compose exec backend pytest tests/test_submissions_student.py::test_manual_submission_with_file_becomes_pending -v`
Expected: FAIL с 404 на `/api/submissions/{task_id}`.

- [ ] **Step 3: Commit (red)**

```bash
git add backend/tests/test_submissions_student.py
git commit -m "test: student submission manual file upload -> pending (red)"
```

---

### Task 8: Implement student submissions router

**Files:**
- Create: `backend/routers/submissions.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Написать роутер**

Create `backend/routers/submissions.py`:

```python
"""Student-facing submissions router: create submissions with files, fetch own, download."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from auth import get_current_user
from database import get_db
from models import SubmissionFile, SubmissionStatus, Task, TaskSubmission, TaskType, User
from schemas import SubmissionDetail, SubmissionFileOut
from services.unlock_guard import require_unit_unlocked
from services.uploads import absolute_stored_path, save_submission_files, validate_upload_config

router = APIRouter(prefix="/api/submissions", tags=["submissions"])


def _serialize(sub: TaskSubmission) -> SubmissionDetail:
    return SubmissionDetail(
        id=sub.id,
        user_id=sub.user_id,
        task_id=sub.task_id,
        status=sub.status,
        details=sub.details or {},
        submitted_at=sub.submitted_at,
        reviewer_id=sub.reviewer_id,
        reviewed_at=sub.reviewed_at,
        review_comment=sub.review_comment,
        files=[SubmissionFileOut.model_validate(f) for f in sub.files],
    )


async def _auto_grade(task: Task, submission: TaskSubmission, answer_text: str | None) -> None:
    """Compute preliminary auto grading into submission.details. Status set by caller."""
    details = dict(submission.details or {})
    if answer_text is not None:
        details["answer_text"] = answer_text

    if task.type == TaskType.quiz:
        # Quiz answers are expected as JSON inside answer_text for this generic endpoint.
        import json

        try:
            answers = json.loads(answer_text or "{}")
        except json.JSONDecodeError:
            answers = {}
        questions = (task.config or {}).get("questions", [])
        correct, wrong = [], []
        for q in questions:
            qid = str(q["id"])
            if answers.get(qid, "") == q["correct_answer"]:
                correct.append(q["id"])
            else:
                wrong.append(q["id"])
        details["auto_score"] = {
            "score": len(correct),
            "total": len(questions),
            "correct": correct,
            "wrong": wrong,
        }
    submission.details = details


@router.post(
    "/{task_id}",
    response_model=SubmissionDetail,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_unit_unlocked)],
)
async def create_submission(
    task_id: int,
    answer_text: str | None = Form(default=None),
    files: list[UploadFile] = File(default_factory=list),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task_res = await db.execute(select(Task).where(Task.id == task_id))
    task = task_res.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    cfg = task.config or {}
    review_mode = cfg.get("review_mode", "auto")
    uploads_enabled = bool((cfg.get("file_upload") or {}).get("enabled"))
    answer_cfg = cfg.get("answer_text") or {}

    if not uploads_enabled and len(files) > 0:
        raise HTTPException(status_code=400, detail="uploads_disabled")
    if answer_cfg.get("required") and not (answer_text or "").strip():
        raise HTTPException(status_code=400, detail="answer_required")

    # Validate counts/required up front (per-file size enforced during streaming).
    try:
        if uploads_enabled:
            validate_upload_config(cfg, file_count=len(files), total_size_bytes=0)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    is_manual = review_mode == "manual"
    submission = TaskSubmission(
        user_id=user.id,
        task_id=task_id,
        status=SubmissionStatus.pending,
        details={},
    )
    db.add(submission)
    await db.flush()  # need id for directory

    try:
        if files:
            await save_submission_files(submission, cfg, files, db)

        await _auto_grade(task, submission, answer_text)

        if not is_manual:
            # Auto-finalize: quiz -> success if full score; others currently not auto-passable via this endpoint
            auto = (submission.details or {}).get("auto_score")
            if task.type == TaskType.quiz and auto and auto["score"] == auto["total"]:
                submission.status = SubmissionStatus.success
            elif task.type == TaskType.quiz:
                submission.status = SubmissionStatus.fail
            else:
                # No auto grading available -> keep pending
                submission.status = SubmissionStatus.pending
        await db.commit()
    except HTTPException:
        await db.rollback()
        raise
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    # Reload with files
    res = await db.execute(
        select(TaskSubmission)
        .options(selectinload(TaskSubmission.files))
        .where(TaskSubmission.id == submission.id)
    )
    fresh = res.scalar_one()
    return _serialize(fresh)


@router.get("/{submission_id}", response_model=SubmissionDetail)
async def get_submission(
    submission_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(TaskSubmission)
        .options(selectinload(TaskSubmission.files))
        .where(TaskSubmission.id == submission_id)
    )
    sub = res.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Not found")
    if sub.user_id != user.id and user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    return _serialize(sub)


@router.get("/{submission_id}/files/{file_id}")
async def download_submission_file(
    submission_id: int,
    file_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(SubmissionFile, TaskSubmission)
        .join(TaskSubmission, SubmissionFile.submission_id == TaskSubmission.id)
        .where(SubmissionFile.id == file_id, TaskSubmission.id == submission_id)
    )
    row = res.first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    file_rec, sub = row
    if sub.user_id != user.id and user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        path = absolute_stored_path(file_rec.stored_path)
    except ValueError:
        raise HTTPException(status_code=500, detail="path_error")

    if not path.exists():
        raise HTTPException(status_code=404, detail="file_missing")

    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename=file_rec.filename,
    )
```

- [ ] **Step 2: Зарегистрировать роутер в `backend/main.py`**

Найти блок `from routers import ...` и добавить `submissions`:

```python
from routers import admin, admin_content, auth_router, courses, ctf, gitlab_tasks, progress, quiz, submissions, tasks, tracks
```

И ниже, в блоке `app.include_router(...)`:

```python
app.include_router(submissions.router)
```

- [ ] **Step 3: Запустить тест**

Run: `docker compose restart backend && sleep 3 && docker compose exec backend pytest tests/test_submissions_student.py::test_manual_submission_with_file_becomes_pending -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/routers/submissions.py backend/main.py
git commit -m "feat(submissions): student router with file upload and manual/auto routing"
```

---

### Task 9: Negative tests — disabled uploads, required file, ext guard, ownership

**Files:**
- Modify: `backend/tests/test_submissions_student.py`

- [ ] **Step 1: Дописать тесты**

Добавить в `test_submissions_student.py`:

```python
async def _seed_auto_quiz_no_uploads() -> dict:
    async with async_session() as db:
        user = User(
            username="student_sub_2",
            password_hash=hash_password("x"),
            full_name="Stu2",
            role=UserRole.student,
        )
        task = Task(
            slug="quiz-auto-1",
            title="Auto quiz",
            description="",
            type=TaskType.quiz,
            config={
                "questions": [
                    {"id": 1, "text": "1+1?", "options": ["1", "2"], "correct_answer": "2"}
                ]
            },
        )
        db.add_all([user, task])
        await db.commit()
        await db.refresh(user)
        await db.refresh(task)
        return {"user_id": user.id, "task_id": task.id, "token": create_token(user.id, user.role.value)}


async def test_rejects_files_when_upload_disabled():
    seed = await _seed_auto_quiz_no_uploads()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        files = [("files", ("x.pdf", io.BytesIO(b"data"), "application/pdf"))]
        resp = await ac.post(
            f"/api/submissions/{seed['task_id']}",
            data={"answer_text": "{}"},
            files=files,
            headers={"Authorization": f"Bearer {seed['token']}"},
        )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "uploads_disabled"


async def test_rejects_disallowed_extension():
    seed = await _seed_manual_theory()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        files = [("files", ("evil.exe", io.BytesIO(b"MZ"), "application/octet-stream"))]
        resp = await ac.post(
            f"/api/submissions/{seed['task_id']}",
            files=files,
            headers={"Authorization": f"Bearer {seed['token']}"},
        )
    assert resp.status_code == 400
    assert "ext_not_allowed" in resp.json()["detail"]


async def test_rejects_when_file_required_and_missing():
    seed = await _seed_manual_theory()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            f"/api/submissions/{seed['task_id']}",
            data={"answer_text": "no files"},
            headers={"Authorization": f"Bearer {seed['token']}"},
        )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "file_required"


async def test_other_student_cannot_fetch_submission():
    seed = await _seed_manual_theory()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        files = [("files", ("report.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf"))]
        resp = await ac.post(
            f"/api/submissions/{seed['task_id']}",
            files=files,
            headers={"Authorization": f"Bearer {seed['token']}"},
        )
    sub_id = resp.json()["id"]

    async with async_session() as db:
        other = User(
            username="student_other",
            password_hash=hash_password("x"),
            full_name="Other",
            role=UserRole.student,
        )
        db.add(other)
        await db.commit()
        await db.refresh(other)
        other_token = create_token(other.id, other.role.value)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get(
            f"/api/submissions/{sub_id}",
            headers={"Authorization": f"Bearer {other_token}"},
        )
    assert resp.status_code == 403
```

- [ ] **Step 2: Запустить все тесты этого файла**

Run: `docker compose exec backend pytest tests/test_submissions_student.py -v`
Expected: все 4 теста PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_submissions_student.py
git commit -m "test(submissions): cover disabled uploads, ext guard, required file, ownership"
```

---

## Phase 4 — Admin review router

### Task 10: Admin review queue — first test

**Files:**
- Create: `backend/tests/test_admin_review.py`

- [ ] **Step 1: Написать тест очереди**

Create `backend/tests/test_admin_review.py`:

```python
"""Admin review queue and verdict endpoints."""
import io

import pytest
from httpx import ASGITransport, AsyncClient

from auth import create_token, hash_password
from database import async_session, engine
from main import app
from models import Task, TaskType, User, UserRole

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
async def _fresh_engine_per_test():
    await engine.dispose()
    yield
    await engine.dispose()


async def _seed() -> dict:
    async with async_session() as db:
        admin = User(
            username="admin_rev",
            password_hash=hash_password("x"),
            full_name="Admin",
            role=UserRole.admin,
        )
        student = User(
            username="stud_rev",
            password_hash=hash_password("x"),
            full_name="Stud",
            role=UserRole.student,
        )
        task = Task(
            slug="theory-review-1",
            title="Review me",
            description="",
            type=TaskType.theory,
            config={
                "review_mode": "manual",
                "file_upload": {
                    "enabled": True,
                    "max_files": 3,
                    "max_size_mb": 5,
                    "allowed_ext": ["pdf"],
                    "required": True,
                },
            },
        )
        db.add_all([admin, student, task])
        await db.commit()
        await db.refresh(admin)
        await db.refresh(student)
        await db.refresh(task)
        return {
            "admin_token": create_token(admin.id, admin.role.value),
            "student_token": create_token(student.id, student.role.value),
            "task_id": task.id,
            "admin_id": admin.id,
            "student_id": student.id,
        }


async def _create_pending(client: AsyncClient, seed: dict) -> int:
    files = [("files", ("r.pdf", io.BytesIO(b"%PDF"), "application/pdf"))]
    r = await client.post(
        f"/api/submissions/{seed['task_id']}",
        files=files,
        headers={"Authorization": f"Bearer {seed['student_token']}"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def test_queue_lists_pending_manual_submission():
    seed = await _seed()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await _create_pending(ac, seed)
        r = await ac.get(
            "/api/admin/review/queue",
            headers={"Authorization": f"Bearer {seed['admin_token']}"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    assert any(item["task_id"] == seed["task_id"] for item in body["items"])


async def test_queue_count():
    seed = await _seed()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await _create_pending(ac, seed)
        r = await ac.get(
            "/api/admin/review/queue/count",
            headers={"Authorization": f"Bearer {seed['admin_token']}"},
        )
    assert r.status_code == 200
    assert r.json()["count"] >= 1


async def test_admin_posts_verdict_success():
    seed = await _seed()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        sub_id = await _create_pending(ac, seed)
        r = await ac.post(
            f"/api/admin/submissions/{sub_id}/review",
            json={"status": "success", "comment": "nicely done"},
            headers={"Authorization": f"Bearer {seed['admin_token']}"},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "success"
    assert body["review_comment"] == "nicely done"
    assert body["reviewer_id"] == seed["admin_id"]


async def test_double_review_rejected():
    seed = await _seed()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        sub_id = await _create_pending(ac, seed)
        await ac.post(
            f"/api/admin/submissions/{sub_id}/review",
            json={"status": "fail", "comment": "x"},
            headers={"Authorization": f"Bearer {seed['admin_token']}"},
        )
        r = await ac.post(
            f"/api/admin/submissions/{sub_id}/review",
            json={"status": "success", "comment": "y"},
            headers={"Authorization": f"Bearer {seed['admin_token']}"},
        )
    assert r.status_code == 400
    assert r.json()["detail"] == "already_reviewed"


async def test_non_admin_forbidden():
    seed = await _seed()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get(
            "/api/admin/review/queue",
            headers={"Authorization": f"Bearer {seed['student_token']}"},
        )
    assert r.status_code == 403
```

- [ ] **Step 2: Запустить — ожидается FAIL**

Run: `docker compose exec backend pytest tests/test_admin_review.py -v`
Expected: FAIL — все пять тестов, роутера нет (404 на `/api/admin/review/queue` и т.п.).

- [ ] **Step 3: Commit (red)**

```bash
git add backend/tests/test_admin_review.py
git commit -m "test(admin-review): queue, verdict, double-review, auth (red)"
```

---

### Task 11: Implement admin review router

**Files:**
- Create: `backend/routers/admin_review.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Написать роутер**

Create `backend/routers/admin_review.py`:

```python
"""Admin review router: pending queue, submission detail, file download, verdict."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from auth import require_admin
from database import get_db
from models import (
    Course,
    Module,
    ModuleUnit,
    SubmissionFile,
    SubmissionStatus,
    Task,
    TaskSubmission,
    User,
)
from schemas import (
    ReviewQueueItem,
    ReviewQueueResponse,
    ReviewVerdict,
    SubmissionDetail,
    SubmissionFileOut,
)
from services.uploads import absolute_stored_path

router = APIRouter(
    prefix="/api/admin",
    tags=["admin-review"],
    dependencies=[Depends(require_admin)],
)


def _is_manual(task: Task) -> bool:
    return (task.config or {}).get("review_mode") == "manual"


async def _pending_manual_base_query(db: AsyncSession):
    """Base SELECT for pending submissions whose task has review_mode=manual."""
    q = (
        select(TaskSubmission, Task, User)
        .join(Task, TaskSubmission.task_id == Task.id)
        .join(User, TaskSubmission.user_id == User.id)
        .where(
            TaskSubmission.status == SubmissionStatus.pending,
            Task.config["review_mode"].astext == "manual",
        )
        .order_by(TaskSubmission.submitted_at.asc())
    )
    return q


@router.get("/review/queue", response_model=ReviewQueueResponse)
async def review_queue(
    course_id: int | None = Query(default=None),
    user_id: int | None = Query(default=None),
    task_id: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    q = await _pending_manual_base_query(db)

    if user_id is not None:
        q = q.where(TaskSubmission.user_id == user_id)
    if task_id is not None:
        q = q.where(TaskSubmission.task_id == task_id)
    if course_id is not None:
        q = q.where(
            TaskSubmission.task_id.in_(
                select(ModuleUnit.task_id)
                .join(Module, ModuleUnit.module_id == Module.id)
                .where(Module.course_id == course_id)
            )
        )

    # Count
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    rows = (
        await db.execute(q.offset((page - 1) * per_page).limit(per_page))
    ).all()

    # Course lookup per task (first course via any module)
    task_ids = [t.id for (_s, t, _u) in rows]
    course_map: dict[int, tuple[int, str]] = {}
    if task_ids:
        course_rows = await db.execute(
            select(ModuleUnit.task_id, Course.id, Course.title)
            .join(Module, ModuleUnit.module_id == Module.id)
            .join(Course, Module.course_id == Course.id)
            .where(ModuleUnit.task_id.in_(task_ids))
        )
        for tid, cid, ctitle in course_rows.all():
            course_map.setdefault(tid, (cid, ctitle))

    items = [
        ReviewQueueItem(
            submission_id=s.id,
            task_id=t.id,
            task_title=t.title,
            user_id=u.id,
            username=u.username,
            user_full_name=u.full_name or "",
            submitted_at=s.submitted_at,
            course_id=course_map.get(t.id, (None, None))[0],
            course_title=course_map.get(t.id, (None, None))[1],
        )
        for (s, t, u) in rows
    ]
    return ReviewQueueResponse(items=items, total=total, page=page, per_page=per_page)


@router.get("/review/queue/count")
async def review_queue_count(db: AsyncSession = Depends(get_db)):
    q = await _pending_manual_base_query(db)
    count = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
    return {"count": count}


@router.get("/submissions/{submission_id}", response_model=SubmissionDetail)
async def admin_get_submission(
    submission_id: int, db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(TaskSubmission)
        .options(selectinload(TaskSubmission.files))
        .where(TaskSubmission.id == submission_id)
    )
    sub = res.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Not found")
    return SubmissionDetail(
        id=sub.id,
        user_id=sub.user_id,
        task_id=sub.task_id,
        status=sub.status,
        details=sub.details or {},
        submitted_at=sub.submitted_at,
        reviewer_id=sub.reviewer_id,
        reviewed_at=sub.reviewed_at,
        review_comment=sub.review_comment,
        files=[SubmissionFileOut.model_validate(f) for f in sub.files],
    )


@router.get("/submissions/{submission_id}/files/{file_id}")
async def admin_download_file(
    submission_id: int, file_id: int, db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(SubmissionFile).where(
            SubmissionFile.id == file_id,
            SubmissionFile.submission_id == submission_id,
        )
    )
    f = res.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="Not found")
    try:
        path = absolute_stored_path(f.stored_path)
    except ValueError:
        raise HTTPException(status_code=500, detail="path_error")
    if not path.exists():
        raise HTTPException(status_code=404, detail="file_missing")
    return FileResponse(path, media_type="application/octet-stream", filename=f.filename)


@router.post("/submissions/{submission_id}/review", response_model=SubmissionDetail)
async def submit_review(
    submission_id: int,
    body: ReviewVerdict,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if body.status not in (SubmissionStatus.success, SubmissionStatus.fail):
        raise HTTPException(status_code=400, detail="bad_status")

    res = await db.execute(
        select(TaskSubmission)
        .options(selectinload(TaskSubmission.files))
        .where(TaskSubmission.id == submission_id)
    )
    sub = res.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Not found")
    if sub.reviewer_id is not None or sub.status != SubmissionStatus.pending:
        raise HTTPException(status_code=400, detail="already_reviewed")

    sub.status = body.status
    sub.reviewer_id = admin.id
    sub.reviewed_at = datetime.now(timezone.utc)
    sub.review_comment = body.comment
    await db.commit()
    await db.refresh(sub)

    return SubmissionDetail(
        id=sub.id,
        user_id=sub.user_id,
        task_id=sub.task_id,
        status=sub.status,
        details=sub.details or {},
        submitted_at=sub.submitted_at,
        reviewer_id=sub.reviewer_id,
        reviewed_at=sub.reviewed_at,
        review_comment=sub.review_comment,
        files=[SubmissionFileOut.model_validate(f) for f in sub.files],
    )
```

- [ ] **Step 2: Подключить роутер в `main.py`**

В `backend/main.py`:

```python
from routers import admin, admin_content, admin_review, auth_router, courses, ctf, gitlab_tasks, progress, quiz, submissions, tasks, tracks
...
app.include_router(admin_review.router)
```

- [ ] **Step 3: Запустить тесты**

Run: `docker compose restart backend && sleep 3 && docker compose exec backend pytest tests/test_admin_review.py -v`
Expected: все 5 тестов PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/routers/admin_review.py backend/main.py
git commit -m "feat(admin-review): queue, submission detail, verdict endpoint"
```

---

## Phase 5 — Manual quiz behavior

### Task 12: Quiz with review_mode=manual stays pending

**Files:**
- Modify: `backend/routers/quiz.py`
- Create: `backend/tests/test_manual_quiz.py`

- [ ] **Step 1: Написать тест для манулл quiz через `/api/quiz/submit`**

Create `backend/tests/test_manual_quiz.py`:

```python
"""Quiz with review_mode=manual: stays pending, auto_score recorded."""
import pytest
from httpx import ASGITransport, AsyncClient

from auth import create_token, hash_password
from database import async_session, engine
from main import app
from models import SubmissionStatus, Task, TaskSubmission, TaskType, User, UserRole

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
async def _fresh_engine_per_test():
    await engine.dispose()
    yield
    await engine.dispose()


async def test_manual_quiz_submit_stays_pending_and_records_auto_score():
    async with async_session() as db:
        user = User(
            username="stu_manq",
            password_hash=hash_password("x"),
            full_name="S",
            role=UserRole.student,
        )
        task = Task(
            slug="quiz-manual-1",
            title="Manual quiz",
            description="",
            type=TaskType.quiz,
            config={
                "review_mode": "manual",
                "questions": [
                    {"id": 1, "text": "1+1?", "options": ["1", "2"], "correct_answer": "2"},
                    {"id": 2, "text": "2+2?", "options": ["3", "4"], "correct_answer": "4"},
                ],
            },
        )
        db.add_all([user, task])
        await db.commit()
        await db.refresh(user)
        await db.refresh(task)
        token = create_token(user.id, user.role.value)
        tid = task.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(
            f"/api/quiz/{tid}/submit",
            json={"answers": {"1": "2", "2": "3"}},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 200, r.text

    async with async_session() as db:
        res = await db.execute(
            TaskSubmission.__table__.select().where(TaskSubmission.task_id == tid)
        )
        rows = res.fetchall()
        assert len(rows) == 1
        sub = rows[0]
        assert sub.status == SubmissionStatus.pending
        auto = sub.details.get("auto_score")
        assert auto == {"score": 1, "total": 2, "correct": [1], "wrong": [2]}
```

- [ ] **Step 2: Запустить — ожидается FAIL**

Run: `docker compose exec backend pytest tests/test_manual_quiz.py -v`
Expected: FAIL — статус будет `fail`, `auto_score` отсутствует.

- [ ] **Step 3: Обновить `quiz.py`**

В `backend/routers/quiz.py`, заменить тело функции `submit_quiz` на:

```python
@router.post("/{task_id}/submit", response_model=QuizResult, dependencies=[Depends(require_unit_unlocked)])
async def submit_quiz(
    task_id: int,
    body: QuizSubmit,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task or task.type != TaskType.quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    questions = task.config.get("questions", [])
    correct, wrong = [], []
    for q in questions:
        qid = str(q["id"])
        user_answer = body.answers.get(qid, "")
        if user_answer == q["correct_answer"]:
            correct.append(q["id"])
        else:
            wrong.append(q["id"])

    score = len(correct)
    total = len(questions)
    passed = total > 0 and score == total

    is_manual = (task.config or {}).get("review_mode") == "manual"
    auto_score = {"score": score, "total": total, "correct": correct, "wrong": wrong}
    details = {"auto_score": auto_score} if is_manual else {
        "score": score, "total": total, "correct": correct, "wrong": wrong,
    }

    if is_manual:
        sub_status = SubmissionStatus.pending
    else:
        sub_status = SubmissionStatus.success if passed else SubmissionStatus.fail

    submission = TaskSubmission(
        user_id=user.id,
        task_id=task_id,
        status=sub_status,
        details=details,
    )
    db.add(submission)
    await db.commit()

    return QuizResult(score=score, total=total, correct=correct, wrong=wrong)
```

- [ ] **Step 4: Запустить ВСЕ quiz-тесты**

Run: `docker compose exec backend pytest tests/test_manual_quiz.py tests/test_courses_api.py tests/test_progression.py -v`
Expected: все зелёные.

- [ ] **Step 5: Commit**

```bash
git add backend/routers/quiz.py backend/tests/test_manual_quiz.py
git commit -m "feat(quiz): support review_mode=manual (pending + auto_score in details)"
```

---

### Task 13: Resubmission after fail — backend test

**Files:**
- Create: `backend/tests/test_resubmission.py`

- [ ] **Step 1: Тест на повторную отправку после fail**

Create `backend/tests/test_resubmission.py`:

```python
"""After a fail verdict the student can create a new submission."""
import io

import pytest
from httpx import ASGITransport, AsyncClient

from auth import create_token, hash_password
from database import async_session, engine
from main import app
from models import Task, TaskType, User, UserRole

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
async def _fresh_engine_per_test():
    await engine.dispose()
    yield
    await engine.dispose()


async def test_resubmit_allowed_after_fail():
    async with async_session() as db:
        admin = User(username="adm_res", password_hash=hash_password("x"), full_name="A", role=UserRole.admin)
        stud = User(username="stu_res", password_hash=hash_password("x"), full_name="S", role=UserRole.student)
        task = Task(
            slug="theory-resub",
            title="Resub",
            type=TaskType.theory,
            config={
                "review_mode": "manual",
                "file_upload": {"enabled": True, "max_files": 1, "max_size_mb": 1, "allowed_ext": ["txt"], "required": True},
            },
        )
        db.add_all([admin, stud, task])
        await db.commit()
        await db.refresh(admin)
        await db.refresh(stud)
        await db.refresh(task)
        admin_token = create_token(admin.id, admin.role.value)
        stud_token = create_token(stud.id, stud.role.value)
        tid = task.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r1 = await ac.post(
            f"/api/submissions/{tid}",
            files=[("files", ("a.txt", io.BytesIO(b"hi"), "text/plain"))],
            headers={"Authorization": f"Bearer {stud_token}"},
        )
        assert r1.status_code == 201
        sub1 = r1.json()["id"]

        r2 = await ac.post(
            f"/api/admin/submissions/{sub1}/review",
            json={"status": "fail", "comment": "redo"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r2.status_code == 200

        r3 = await ac.post(
            f"/api/submissions/{tid}",
            files=[("files", ("b.txt", io.BytesIO(b"hi2"), "text/plain"))],
            headers={"Authorization": f"Bearer {stud_token}"},
        )
        assert r3.status_code == 201
        assert r3.json()["id"] != sub1
        assert r3.json()["status"] == "pending"
```

- [ ] **Step 2: Запустить**

Run: `docker compose exec backend pytest tests/test_resubmission.py -v`
Expected: PASS (логика уже рабочая, тест страхует).

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_resubmission.py
git commit -m "test: resubmission after fail creates a new pending submission"
```

---

## Phase 6 — Frontend student UI

### Task 14a: Upgrade /tasks/{id}/submissions to return full detail

**Files:**
- Modify: `backend/routers/tasks.py`

- [ ] **Step 1: Заменить эндпоинт, отдающий список сабмишенов студента**

В `backend/routers/tasks.py` заменить существующий `@router.get("/{task_id}/submissions", ...)` на:

```python
from sqlalchemy.orm import selectinload
from schemas import SubmissionDetail, SubmissionFileOut


@router.get("/{task_id}/submissions", response_model=list[SubmissionDetail])
async def my_submissions(
    task_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TaskSubmission)
        .options(selectinload(TaskSubmission.files))
        .where(TaskSubmission.task_id == task_id, TaskSubmission.user_id == user.id)
        .order_by(TaskSubmission.submitted_at.desc())
    )
    subs = result.scalars().all()
    return [
        SubmissionDetail(
            id=s.id,
            user_id=s.user_id,
            task_id=s.task_id,
            status=s.status,
            details=s.details or {},
            submitted_at=s.submitted_at,
            reviewer_id=s.reviewer_id,
            reviewed_at=s.reviewed_at,
            review_comment=s.review_comment,
            files=[SubmissionFileOut.model_validate(f) for f in s.files],
        )
        for s in subs
    ]
```

(Существующий импорт `SubmissionOut` можно оставить — он используется `/admin` в другом роутере.)

- [ ] **Step 2: Smoke — backend стартует**

Run: `docker compose restart backend && sleep 3 && docker compose exec backend pytest tests/ -x -q`
Expected: зелёно (существующие тесты не завязаны на структуру SubmissionOut без file/review полей; новые уже ожидают SubmissionDetail).

- [ ] **Step 3: Commit**

```bash
git add backend/routers/tasks.py
git commit -m "feat(tasks): return full SubmissionDetail with files and review fields"
```

---

### Task 14: API client additions

**Files:**
- Modify: `frontend/src/api.ts`

- [ ] **Step 1: Добавить методы в объект `api`**

В конец объекта `api` (перед закрывающей `}`) в `frontend/src/api.ts`:

```typescript
  submitTask: async (taskId: number, form: FormData) => {
    const token = getToken();
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch(`${API_BASE}/submissions/${taskId}`, {
      method: 'POST',
      body: form,
      headers,
    });
    if (resp.status === 401) {
      clearToken();
      window.location.href = '/login';
      throw new Error('Unauthorized');
    }
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      throw new Error(body.detail || `HTTP ${resp.status}`);
    }
    return resp.json();
  },

  getSubmission: (id: number) => request<any>(`/submissions/${id}`),

  // NOTE: reuses existing api.mySubmissions(taskId) — the backend endpoint
  // now returns SubmissionDetail with files and review fields.

  fileDownloadUrl: (submissionId: number, fileId: number, isAdmin = false) =>
    isAdmin
      ? `${API_BASE}/admin/submissions/${submissionId}/files/${fileId}`
      : `${API_BASE}/submissions/${submissionId}/files/${fileId}`,

  // Admin review
  getReviewQueue: (params: { course_id?: number; user_id?: number; task_id?: number; page?: number; per_page?: number } = {}) => {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null) q.set(k, String(v));
    });
    return request<any>(`/admin/review/queue${q.toString() ? `?${q}` : ''}`);
  },

  getReviewQueueCount: () => request<{ count: number }>('/admin/review/queue/count'),

  getAdminSubmission: (id: number) => request<any>(`/admin/submissions/${id}`),

  reviewSubmission: (id: number, status: 'success' | 'fail', comment: string) =>
    request<any>(`/admin/submissions/${id}/review`, {
      method: 'POST',
      body: JSON.stringify({ status, comment }),
    }),
```

- [ ] **Step 2: Проверить сборку фронта**

Run: `docker compose exec frontend npm run build` (если контейнер имеет node) или локально `cd frontend && npm run build`.
Expected: успешная сборка.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api.ts
git commit -m "frontend(api): add submission and admin-review endpoints"
```

---

### Task 15: FileUploader component

**Files:**
- Create: `frontend/src/components/FileUploader.tsx`

- [ ] **Step 1: Написать компонент**

Create `frontend/src/components/FileUploader.tsx`:

```tsx
import { useRef, useState } from 'react';

interface Props {
  maxFiles: number;
  maxSizeMb: number;
  allowedExt: string[];
  required: boolean;
  files: File[];
  onChange: (files: File[]) => void;
  disabled?: boolean;
}

export default function FileUploader({
  maxFiles, maxSizeMb, allowedExt, required, files, onChange, disabled,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);

  const accept = allowedExt.map((e) => `.${e}`).join(',');

  function validate(list: File[]): string | null {
    if (list.length > maxFiles) return `Максимум файлов: ${maxFiles}`;
    for (const f of list) {
      const ext = f.name.split('.').pop()?.toLowerCase() || '';
      if (!allowedExt.includes(ext)) return `Расширение .${ext} не разрешено`;
      if (f.size > maxSizeMb * 1024 * 1024) return `Файл ${f.name} больше ${maxSizeMb} МБ`;
    }
    return null;
  }

  function addFiles(incoming: FileList | File[]) {
    const merged = [...files, ...Array.from(incoming)];
    const err = validate(merged);
    if (err) {
      setError(err);
      return;
    }
    setError(null);
    onChange(merged);
  }

  function removeAt(i: number) {
    const next = files.slice();
    next.splice(i, 1);
    onChange(next);
  }

  return (
    <div className="space-y-2">
      <div
        className="border-2 border-dashed border-outline-variant/30 rounded p-4 text-center cursor-pointer hover:bg-surface-container-low"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          if (!disabled) addFiles(e.dataTransfer.files);
        }}
        onClick={() => !disabled && inputRef.current?.click()}
      >
        <p className="text-sm text-on-surface-variant">
          Перетащите файлы или нажмите, чтобы выбрать
        </p>
        <p className="text-xs text-on-surface-variant/60 mt-1">
          До {maxFiles} шт., макс {maxSizeMb} МБ; {allowedExt.join(', ')}
          {required ? ' (обязательно)' : ''}
        </p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={accept}
          className="hidden"
          onChange={(e) => e.target.files && addFiles(e.target.files)}
        />
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      {files.length > 0 && (
        <ul className="text-sm space-y-1">
          {files.map((f, i) => (
            <li key={i} className="flex justify-between items-center bg-surface-container-low rounded px-3 py-1.5">
              <span className="truncate">{f.name} <span className="text-on-surface-variant/60 text-xs">({Math.round(f.size / 1024)} KB)</span></span>
              <button
                type="button"
                onClick={() => removeAt(i)}
                className="text-xs text-red-400 hover:underline"
                disabled={disabled}
              >
                удалить
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Сборка фронта**

Run: `cd frontend && npm run build`
Expected: без TS-ошибок.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/FileUploader.tsx
git commit -m "frontend(components): add FileUploader with drag-n-drop and client validation"
```

---

### Task 16: SubmissionHistory component

**Files:**
- Create: `frontend/src/components/SubmissionHistory.tsx`

- [ ] **Step 1: Компонент истории**

Create `frontend/src/components/SubmissionHistory.tsx`:

```tsx
import { useState } from 'react';

interface Submission {
  id: number;
  status: 'pending' | 'success' | 'fail';
  submitted_at: string;
  review_comment?: string | null;
  files?: { id: number; filename: string }[];
}

interface Props {
  items: Submission[];
  downloadUrl: (submissionId: number, fileId: number) => string;
}

const statusLabel: Record<string, string> = {
  pending: 'На проверке',
  success: 'Зачтено',
  fail: 'Не зачтено',
};

const statusColor: Record<string, string> = {
  pending: 'text-yellow-300',
  success: 'text-primary',
  fail: 'text-red-400',
};

export default function SubmissionHistory({ items, downloadUrl }: Props) {
  const [open, setOpen] = useState(false);
  if (!items.length) return null;

  return (
    <details
      open={open}
      onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)}
      className="border border-outline-variant/20 rounded"
    >
      <summary className="px-3 py-2 cursor-pointer text-sm">
        История попыток ({items.length})
      </summary>
      <ul className="divide-y divide-outline-variant/20">
        {items.map((s) => (
          <li key={s.id} className="px-3 py-2 text-sm space-y-1">
            <div className="flex justify-between">
              <span className={statusColor[s.status]}>{statusLabel[s.status]}</span>
              <span className="text-on-surface-variant/60 text-xs">
                {new Date(s.submitted_at).toLocaleString()}
              </span>
            </div>
            {s.review_comment && (
              <p className="text-on-surface-variant text-xs whitespace-pre-wrap">
                {s.review_comment}
              </p>
            )}
            {s.files && s.files.length > 0 && (
              <ul className="text-xs space-x-2">
                {s.files.map((f) => (
                  <a
                    key={f.id}
                    href={downloadUrl(s.id, f.id)}
                    className="text-primary hover:underline"
                    target="_blank"
                    rel="noreferrer"
                  >
                    {f.filename}
                  </a>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ul>
    </details>
  );
}
```

- [ ] **Step 2: Сборка**

Run: `cd frontend && npm run build`
Expected: без ошибок.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/SubmissionHistory.tsx
git commit -m "frontend(components): add SubmissionHistory list"
```

---

### Task 17: Integrate submission block into ChallengeDetailsPage

**Files:**
- Modify: `frontend/src/pages/ChallengeDetailsPage.tsx`

- [ ] **Step 1: Определить, где сейчас рендерится контент задачи, и добавить блок**

Открой `frontend/src/pages/ChallengeDetailsPage.tsx`. Найди место, где по `task.type` отрисовывается тело задачи. Добавь общий блок «Сдача работы», который рендерится когда `task.config.file_upload?.enabled || task.config.review_mode === 'manual'`.

Вставь импорты вверху:

```tsx
import { useMemo, useState } from 'react';
import FileUploader from '../components/FileUploader';
import SubmissionHistory from '../components/SubmissionHistory';
import { api } from '../api';
```

Внутри компонента, после получения `task` и `submissions`, добавь:

```tsx
const uploadCfg = (task?.config?.file_upload ?? null) as
  | { enabled: boolean; max_files: number; max_size_mb: number; allowed_ext: string[]; required: boolean }
  | null;
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
```

И в JSX добавь (там, где уместно — ниже `description`, перед историей прогресса, если есть):

```tsx
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
```

Если локальной переменной `submissions` на странице ещё нет, загрузи её: добавь `useEffect` с `api.mySubmissions(taskId).then(setSubmissions)`.

- [ ] **Step 2: Сборка и smoke в браузере**

Run: `cd frontend && npm run build`
Expected: без ошибок.

Затем `docker compose up -d frontend backend` и в браузере создать через админку theory-таск с `review_mode=manual` и `file_upload.enabled=true`, залогиниться студентом, проверить, что блок отображается, загрузка проходит, плашка статуса `pending` видна.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/ChallengeDetailsPage.tsx
git commit -m "frontend(challenge): submission block with file upload and verdict display"
```

---

## Phase 7 — Frontend admin UI

### Task 18: Admin review queue page

**Files:**
- Create: `frontend/src/pages/admin/AdminReviewQueuePage.tsx`

- [ ] **Step 1: Написать страницу**

Create `frontend/src/pages/admin/AdminReviewQueuePage.tsx`:

```tsx
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../../api';

interface QueueItem {
  submission_id: number;
  task_id: number;
  task_title: string;
  user_id: number;
  username: string;
  user_full_name: string;
  submitted_at: string;
  course_id: number | null;
  course_title: string | null;
}

export default function AdminReviewQueuePage() {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [perPage] = useState(20);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const data = await api.getReviewQueue({ page, per_page: perPage });
      setItems(data.items);
      setTotal(data.total);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [page]);

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-semibold">Проверка работ</h1>
      {loading ? (
        <p className="text-sm text-on-surface-variant">Загрузка…</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-on-surface-variant">Очередь пуста.</p>
      ) : (
        <table className="w-full text-sm">
          <thead className="text-left text-on-surface-variant">
            <tr>
              <th className="py-2">Студент</th>
              <th>Задача</th>
              <th>Курс</th>
              <th>Отправлено</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((it) => (
              <tr key={it.submission_id} className="border-t border-outline-variant/20">
                <td className="py-2">{it.user_full_name || it.username}</td>
                <td>{it.task_title}</td>
                <td>{it.course_title || '—'}</td>
                <td>{new Date(it.submitted_at).toLocaleString()}</td>
                <td>
                  <Link
                    to={`/admin/review/${it.submission_id}`}
                    className="text-primary hover:underline"
                  >
                    Проверить
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <div className="flex gap-2 items-center text-sm">
        <button
          disabled={page <= 1}
          onClick={() => setPage((p) => p - 1)}
          className="px-2 py-1 rounded bg-surface-container-low disabled:opacity-50"
        >
          ← Назад
        </button>
        <span>
          {page} / {Math.max(1, Math.ceil(total / perPage))}
        </span>
        <button
          disabled={page * perPage >= total}
          onClick={() => setPage((p) => p + 1)}
          className="px-2 py-1 rounded bg-surface-container-low disabled:opacity-50"
        >
          Вперёд →
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Зарегистрировать маршрут**

Открой файл с роутингом (обычно `frontend/src/App.tsx` или `main.tsx` с `createBrowserRouter`). Найди блок admin-маршрутов (где `/admin/users`, `/admin/tasks`), добавь:

```tsx
<Route path="/admin/review" element={<AdminReviewQueuePage />} />
<Route path="/admin/review/:submissionId" element={<AdminReviewDetailPage />} />
```

И импорты (детальная страница создаётся следующей задачей — пока может быть заглушка):

```tsx
import AdminReviewQueuePage from './pages/admin/AdminReviewQueuePage';
// import AdminReviewDetailPage — появится в следующей задаче
```

Если detail-страница ещё не создана, добавь временно `element={<div>TODO</div>}` в Route и удали после Task 19.

- [ ] **Step 3: Сборка**

Run: `cd frontend && npm run build`
Expected: без ошибок.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/admin/AdminReviewQueuePage.tsx frontend/src/App.tsx
git commit -m "frontend(admin): review queue page and route"
```

---

### Task 19: Admin review detail page

**Files:**
- Create: `frontend/src/pages/admin/AdminReviewDetailPage.tsx`

- [ ] **Step 1: Написать страницу**

Create `frontend/src/pages/admin/AdminReviewDetailPage.tsx`:

```tsx
import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../../api';

interface SubmissionFile {
  id: number;
  filename: string;
  size_bytes: number;
}

interface Submission {
  id: number;
  user_id: number;
  task_id: number;
  status: 'pending' | 'success' | 'fail';
  details: Record<string, any>;
  submitted_at: string;
  reviewer_id: number | null;
  reviewed_at: string | null;
  review_comment: string | null;
  files: SubmissionFile[];
}

export default function AdminReviewDetailPage() {
  const { submissionId } = useParams();
  const navigate = useNavigate();
  const [sub, setSub] = useState<Submission | null>(null);
  const [task, setTask] = useState<any>(null);
  const [verdict, setVerdict] = useState<'success' | 'fail'>('success');
  const [comment, setComment] = useState('');
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      const id = Number(submissionId);
      const s = await api.getAdminSubmission(id);
      setSub(s);
      const t = await api.getTask(s.task_id);
      setTask(t);
    })();
  }, [submissionId]);

  async function submit() {
    if (!sub) return;
    setSaving(true);
    setErr(null);
    try {
      await api.reviewSubmission(sub.id, verdict, comment);
      navigate('/admin/review');
    } catch (e: any) {
      setErr(e.message || 'Ошибка');
    } finally {
      setSaving(false);
    }
  }

  if (!sub) return <div className="p-6 text-sm">Загрузка…</div>;

  const locked = sub.status !== 'pending' || sub.reviewer_id !== null;
  const auto = sub.details?.auto_score;

  return (
    <div className="p-6 space-y-4 max-w-3xl">
      <h1 className="text-2xl font-semibold">Проверка: {task?.title}</h1>
      <p className="text-sm text-on-surface-variant">
        Отправлено: {new Date(sub.submitted_at).toLocaleString()}
      </p>

      {sub.details?.answer_text && (
        <section>
          <h2 className="text-sm font-medium mb-1">Ответ студента</h2>
          <pre className="whitespace-pre-wrap bg-surface-container-low rounded p-3 text-sm">
            {sub.details.answer_text}
          </pre>
        </section>
      )}

      {auto && (
        <section className="text-sm">
          <h2 className="font-medium mb-1">Автопроверка (quiz)</h2>
          <p>Счёт: {auto.score} / {auto.total}. Правильно: {auto.correct.join(', ') || '—'}. Неверно: {auto.wrong.join(', ') || '—'}.</p>
        </section>
      )}

      {sub.files.length > 0 && (
        <section>
          <h2 className="text-sm font-medium mb-1">Файлы</h2>
          <ul className="space-y-1 text-sm">
            {sub.files.map((f) => (
              <li key={f.id}>
                <a
                  className="text-primary hover:underline"
                  href={api.fileDownloadUrl(sub.id, f.id, true)}
                  target="_blank"
                  rel="noreferrer"
                >
                  {f.filename}
                </a>
                <span className="text-on-surface-variant/60 text-xs ml-2">
                  {Math.round(f.size_bytes / 1024)} KB
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="space-y-2">
        <h2 className="text-sm font-medium">Вердикт</h2>
        {locked ? (
          <p className="text-sm text-on-surface-variant">
            Уже проверено: статус <b>{sub.status}</b>. Комментарий: {sub.review_comment || '—'}.
          </p>
        ) : (
          <>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="radio"
                checked={verdict === 'success'}
                onChange={() => setVerdict('success')}
              />
              Зачесть
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="radio"
                checked={verdict === 'fail'}
                onChange={() => setVerdict('fail')}
              />
              Не зачесть
            </label>
            <textarea
              rows={4}
              className="w-full bg-surface-container-low rounded p-3 text-sm"
              placeholder="Комментарий"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
            />
            {err && <p className="text-red-400 text-sm">{err}</p>}
            <button
              onClick={submit}
              disabled={saving}
              className="px-4 py-2 rounded bg-primary text-on-primary text-sm disabled:opacity-50"
            >
              {saving ? 'Сохраняем…' : 'Сохранить вердикт'}
            </button>
          </>
        )}
      </section>
    </div>
  );
}
```

- [ ] **Step 2: Обновить импорт в роутере**

В том же файле, где добавил Route на предыдущем шаге:

```tsx
import AdminReviewDetailPage from './pages/admin/AdminReviewDetailPage';
```

Замени placeholder на реальный компонент.

- [ ] **Step 3: Сборка**

Run: `cd frontend && npm run build`
Expected: без ошибок.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/admin/AdminReviewDetailPage.tsx frontend/src/App.tsx
git commit -m "frontend(admin): review detail page with verdict form"
```

---

### Task 20: Sidebar badge

**Files:**
- Modify: `frontend/src/components/Sidebar.tsx`

- [ ] **Step 1: Добавить пункт и счётчик**

В `frontend/src/components/Sidebar.tsx` заменить массив `adminItems` и импорты:

```tsx
import { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../contexts/AuthContext';

const adminItems: SidebarItem[] = [
  { to: '/admin/users', icon: 'group', label: 'Пользователи' },
  { to: '/admin/courses', icon: 'school', label: 'Курсы' },
  { to: '/admin/tasks', icon: 'task_alt', label: 'Таски' },
  { to: '/admin/review', icon: 'rate_review', label: 'Проверка работ' },
  { to: '/admin/results', icon: 'bug_report', label: 'Результаты' },
  { to: '/admin/containers', icon: 'dns', label: 'Контейнеры' },
];
```

Внутри компонента `Sidebar`:

```tsx
const [reviewCount, setReviewCount] = useState<number>(0);

useEffect(() => {
  if (variant !== 'admin') return;
  let stopped = false;
  const load = () =>
    api
      .getReviewQueueCount()
      .then((r) => !stopped && setReviewCount(r.count))
      .catch(() => {});
  load();
  const id = setInterval(load, 30000);
  return () => {
    stopped = true;
    clearInterval(id);
  };
}, [variant]);
```

И в рендере `items.map`, рядом с `label`, добавь бейдж — если `item.to === '/admin/review'` и `reviewCount > 0`:

```tsx
{item.to === '/admin/review' && reviewCount > 0 && (
  <span className="ml-auto bg-primary text-on-primary text-[10px] rounded-full px-2 py-0.5">
    {reviewCount}
  </span>
)}
```

(Если существующий JSX `items.map` не позволяет это вставить без правки — оберни label в `<span className="flex-1">{item.label}</span>` и добавь бейдж после.)

- [ ] **Step 2: Сборка**

Run: `cd frontend && npm run build`
Expected: без ошибок.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Sidebar.tsx
git commit -m "frontend(sidebar): pending-review counter and link for admin"
```

---

## Phase 8 — Smoke & docs

### Task 21: Manual smoke in browser

**Files:** —

- [ ] **Step 1: Запуск стека**

Run: `docker compose up -d --build`
Expected: все контейнеры healthy.

- [ ] **Step 2: Создать theory-таск с ручной проверкой через админку**

1. Открыть `http://lms.lab.local`, логин `admin/admin`.
2. В `/admin/tasks` → новый таск, тип `theory`. В config добавить:
   ```json
   {
     "review_mode": "manual",
     "file_upload": { "enabled": true, "max_files": 2, "max_size_mb": 5, "allowed_ext": ["pdf","txt"], "required": true },
     "answer_text": { "enabled": true, "required": false }
   }
   ```
3. Прицепить к модулю видимого курса.

- [ ] **Step 3: Проверить как студент**

1. Создать/использовать студента. Войти.
2. Открыть задачу → увидеть блок «Сдача работы».
3. Загрузить два `.pdf`, вписать текст, «Отправить на проверку».
4. Плашка `На проверке`.
5. Проверить, что `.exe` отклоняется на клиенте и на сервере.

- [ ] **Step 4: Проверить как преподаватель**

1. Админом открыть `/admin/review` — запись есть.
2. В сайдбаре — бейдж со счётчиком.
3. Открыть карточку, скачать файл, поставить «Не зачесть» с комментарием.
4. Студентом перезайти — видна плашка `Не зачтено` + комментарий. Форма повторной отправки доступна.
5. Студент отправляет снова → админ зачитывает → студент видит зелёную плашку.

- [ ] **Step 5: Прогон backend-тестов**

Run: `docker compose exec backend pytest -x`
Expected: все тесты PASS.

- [ ] **Step 6: Commit (если были правки)**

```bash
# только если что-то пришлось донастроить
git add .
git commit -m "smoke: final fixes after browser verification"
```

---

### Task 22: Update README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Добавить раздел «Ручная проверка и загрузка файлов»**

В `README.md` после секции «Управление контентом → CTF-таски» добавить:

```markdown
### Ручная проверка и файлы

Любую задачу (theory / quiz / gitlab / …) можно пометить как проверяемую преподавателем и/или разрешить прикрепление файлов. В `task.config`:

- `review_mode: "manual"` — сабмишен создаётся со статусом `pending`, пока преподаватель не поставит вердикт.
- `file_upload: { enabled, max_files, max_size_mb, allowed_ext, required }` — блок загрузки файлов (макс 20 МБ / 5 файлов по умолчанию).
- `answer_text: { enabled, required }` — поле свободного ответа.

Преподаватель работает со всеми непроверенными сабмишенами из `/admin/review`. После вердикта — `success` или `fail`; при `fail` студент может отправить работу заново.

Файлы хранятся в volume `uploads_data` (контейнер: `/app/uploads`). Скачивание — только через auth-роуты, прямых URL нет.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs(readme): document manual review and file uploads"
```

---

## Self-review notes

- Спецификация покрыта: миграция (Task 1–2), uploads-сервис (Task 5), student API (Task 7–9), admin API (Task 10–11), manual quiz (Task 12), пересдача (Task 13), frontend студент (Task 14–17), frontend админ (Task 18–20), smoke (Task 21), docs (Task 22). Docker volume — Task 4.
- Имена совпадают между задачами: `SubmissionFile`, `SubmissionDetail`, `ReviewVerdict`, `FileUploader`, `SubmissionHistory`, `AdminReviewQueuePage`, `AdminReviewDetailPage`, `api.submitTask`, `api.getReviewQueue`, `api.reviewSubmission`, `api.fileDownloadUrl`, `api.getAdminSubmission`, `api.getMySubmissionsForTask`, `api.getReviewQueueCount`.
- Флаги конфига в тестах и в UI одинаковые: `review_mode`, `file_upload.enabled/max_files/max_size_mb/allowed_ext/required`, `answer_text.enabled/required`.
- Эндпоинты: `POST /api/submissions/{task_id}`, `GET /api/submissions/{id}`, `GET /api/submissions/{id}/files/{file_id}`, `GET /api/admin/review/queue`, `GET /api/admin/review/queue/count`, `GET /api/admin/submissions/{id}`, `GET /api/admin/submissions/{id}/files/{file_id}`, `POST /api/admin/submissions/{id}/review`.
