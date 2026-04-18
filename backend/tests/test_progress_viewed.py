"""Tests for POST /api/me/progress/viewed — idempotent theory auto-submission."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from auth import create_token, hash_password
from database import async_session, engine
from main import app
from models import (
    Course, Module, ModuleUnit, SubmissionStatus, Task, TaskSubmission,
    TaskType, User, UserRole,
)

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


async def test_progress_viewed_blocked_for_locked_module():
    """Student cannot mark a theory task in a locked module as viewed."""
    suffix = uuid.uuid4().hex[:8]
    async with async_session() as db:
        user = User(
            username=f"locked_theory_{suffix}",
            password_hash=hash_password("x"),
            full_name="Locked",
            role=UserRole.student,
        )
        t1 = Task(
            slug=f"lt-quiz-{suffix}", title=f"LT Quiz {suffix}",
            type=TaskType.quiz, config={"questions": []},
        )
        t2 = Task(
            slug=f"lt-theory-{suffix}", title=f"LT Theory {suffix}",
            type=TaskType.theory, config={"content_kind": "text"},
        )
        db.add_all([user, t1, t2])
        await db.commit()

        course = Course(
            title=f"LT Course {suffix}", slug=f"lt-course-{suffix}",
            config={"progression": "linear"},
        )
        db.add(course)
        await db.flush()
        m1 = Module(course_id=course.id, title="M1", order=1)
        m2 = Module(course_id=course.id, title="M2", order=2)
        db.add_all([m1, m2])
        await db.flush()
        db.add_all([
            ModuleUnit(module_id=m1.id, task_id=t1.id, unit_order=1, is_required=True),
            ModuleUnit(module_id=m2.id, task_id=t2.id, unit_order=1, is_required=True),
        ])
        await db.commit()
        user_id, t1_id, t2_id, course_id, m1_id, m2_id = (
            user.id, t1.id, t2.id, course.id, m1.id, m2.id
        )
        role_value = user.role.value

    token = create_token(user_id, role_value)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                "/api/me/progress/viewed",
                headers={"Authorization": f"Bearer {token}"},
                json={"task_id": t2_id},
            )
        assert resp.status_code == 403, resp.text
        subs = await _get_submissions(user_id, t2_id)
        assert len(subs) == 0, "locked theory must NOT create a submission"
    finally:
        async with async_session() as db:
            await db.execute(
                TaskSubmission.__table__.delete().where(TaskSubmission.user_id == user_id)
            )
            await db.execute(ModuleUnit.__table__.delete().where(ModuleUnit.module_id.in_([m1_id, m2_id])))
            await db.execute(Module.__table__.delete().where(Module.id.in_([m1_id, m2_id])))
            await db.execute(Course.__table__.delete().where(Course.id == course_id))
            await db.execute(Task.__table__.delete().where(Task.id.in_([t1_id, t2_id])))
            await db.execute(User.__table__.delete().where(User.id == user_id))
            await db.commit()
