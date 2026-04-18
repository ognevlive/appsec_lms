"""Tests for POST /api/me/progress/viewed — idempotent theory auto-submission."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from auth import create_token, hash_password
from database import async_session, engine
from main import app
from models import SubmissionStatus, Task, TaskSubmission, TaskType, User, UserRole

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
async def _fresh_engine_per_test():
    """Module-level asyncpg engine may have connections bound to another loop.

    Dispose before and after each test so the pool uses the current loop only.
    """
    await engine.dispose()
    yield
    await engine.dispose()


async def _make_user_and_theory_task():
    suffix = uuid.uuid4().hex[:8]
    async with async_session() as db:
        user = User(
            username=f"viewed_test_{suffix}",
            password_hash=hash_password("x"),
            full_name="Viewed Test",
            role=UserRole.student,
        )
        task = Task(
            slug=f"theory-viewed-{suffix}",
            title="Theory Viewed Test",
            description="",
            type=TaskType.theory,
            config={"content": "hello"},
        )
        db.add(user)
        db.add(task)
        await db.commit()
        await db.refresh(user)
        await db.refresh(task)
        user_id, task_id, role_value = user.id, task.id, user.role.value
    token = create_token(user_id, role_value)
    return user_id, task_id, token


async def _get_submissions(user_id: int, task_id: int):
    async with async_session() as db:
        result = await db.execute(
            select(TaskSubmission).where(
                TaskSubmission.user_id == user_id,
                TaskSubmission.task_id == task_id,
            )
        )
        return [(s.id, s.status) for s in result.scalars().all()]


async def _cleanup(user_id: int, task_id: int):
    async with async_session() as db:
        await db.execute(
            TaskSubmission.__table__.delete().where(
                TaskSubmission.user_id == user_id,
                TaskSubmission.task_id == task_id,
            )
        )
        await db.execute(User.__table__.delete().where(User.id == user_id))
        await db.execute(Task.__table__.delete().where(Task.id == task_id))
        await db.commit()


async def test_progress_viewed_creates_success_submission():
    user_id, task_id, token = await _make_user_and_theory_task()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                "/api/me/progress/viewed",
                headers={"Authorization": f"Bearer {token}"},
                json={"task_id": task_id},
            )
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"ok": True}

        subs = await _get_submissions(user_id, task_id)
        assert len(subs) == 1
        assert subs[0][1] == SubmissionStatus.success
    finally:
        await _cleanup(user_id, task_id)


async def test_progress_viewed_is_idempotent():
    user_id, task_id, token = await _make_user_and_theory_task()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            for _ in range(3):
                resp = await ac.post(
                    "/api/me/progress/viewed",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"task_id": task_id},
                )
                assert resp.status_code == 200, resp.text
                assert resp.json() == {"ok": True}

        subs = await _get_submissions(user_id, task_id)
        assert len(subs) == 1
        assert subs[0][1] == SubmissionStatus.success
    finally:
        await _cleanup(user_id, task_id)
