"""Tests for /api/courses endpoints — list, detail, and linear progression locking."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from auth import create_token, hash_password
from database import async_session, engine
from main import app
from models import (
    Course,
    Module,
    ModuleUnit,
    SubmissionStatus,
    Task,
    TaskSubmission,
    TaskType,
    User,
    UserRole,
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


async def _seed_linear_course(suffix: str) -> dict:
    """Seed a linear Course with 2 Modules, each holding 1 required Unit.

    Module 1 (order=1) -> theory task (order=1 unit)
    Module 2 (order=2) -> quiz task   (order=1 unit)

    Returns a dict with ids for the caller: user_id, user_role, course_id, course_slug,
    module1_id, module2_id, task1_id (theory), task2_id (quiz), unit1_id, unit2_id.
    """
    async with async_session() as db:
        user = User(
            username=f"courses_test_{suffix}",
            password_hash=hash_password("x"),
            full_name="Courses Test",
            role=UserRole.student,
        )
        task1 = Task(
            slug=f"theory-courses-{suffix}",
            title="Theory Courses Test",
            description="",
            type=TaskType.theory,
            config={"content_kind": "text"},
        )
        task2 = Task(
            slug=f"quiz-courses-{suffix}",
            title="Quiz Courses Test",
            description="",
            type=TaskType.quiz,
            config={"questions": []},
        )
        course = Course(
            slug=f"course-linear-{suffix}",
            title="Linear Course Test",
            description="",
            order=999,
            config={"progression": "linear", "icon": "x"},
        )
        db.add_all([user, task1, task2, course])
        await db.commit()
        await db.refresh(user)
        await db.refresh(task1)
        await db.refresh(task2)
        await db.refresh(course)

        module1 = Module(
            course_id=course.id,
            title="Module 1",
            description="",
            order=1,
            estimated_hours=1,
            learning_outcomes=[],
            config={},
        )
        module2 = Module(
            course_id=course.id,
            title="Module 2",
            description="",
            order=2,
            estimated_hours=1,
            learning_outcomes=[],
            config={},
        )
        db.add_all([module1, module2])
        await db.commit()
        await db.refresh(module1)
        await db.refresh(module2)

        unit1 = ModuleUnit(
            module_id=module1.id,
            task_id=task1.id,
            unit_order=1,
            is_required=True,
        )
        unit2 = ModuleUnit(
            module_id=module2.id,
            task_id=task2.id,
            unit_order=1,
            is_required=True,
        )
        db.add_all([unit1, unit2])
        await db.commit()
        await db.refresh(unit1)
        await db.refresh(unit2)

        return {
            "user_id": user.id,
            "user_role": user.role.value,
            "course_id": course.id,
            "course_slug": course.slug,
            "module1_id": module1.id,
            "module2_id": module2.id,
            "task1_id": task1.id,
            "task2_id": task2.id,
            "unit1_id": unit1.id,
            "unit2_id": unit2.id,
        }


async def _add_success_submission(user_id: int, task_id: int) -> int:
    async with async_session() as db:
        sub = TaskSubmission(
            user_id=user_id,
            task_id=task_id,
            status=SubmissionStatus.success,
            details={},
        )
        db.add(sub)
        await db.commit()
        await db.refresh(sub)
        return sub.id


async def _cleanup(seed: dict):
    async with async_session() as db:
        # Delete submissions for this user first to honor FK from task_submissions.
        await db.execute(
            TaskSubmission.__table__.delete().where(
                TaskSubmission.user_id == seed["user_id"]
            )
        )
        # Units -> Modules -> Course (cascade would handle it, but be explicit).
        await db.execute(
            ModuleUnit.__table__.delete().where(
                ModuleUnit.id.in_([seed["unit1_id"], seed["unit2_id"]])
            )
        )
        await db.execute(
            Module.__table__.delete().where(
                Module.id.in_([seed["module1_id"], seed["module2_id"]])
            )
        )
        await db.execute(Course.__table__.delete().where(Course.id == seed["course_id"]))
        await db.execute(
            Task.__table__.delete().where(
                Task.id.in_([seed["task1_id"], seed["task2_id"]])
            )
        )
        await db.execute(User.__table__.delete().where(User.id == seed["user_id"]))
        await db.commit()


async def test_linear_course_module_is_locked_for_fresh_user():
    suffix = uuid.uuid4().hex[:8]
    seed = await _seed_linear_course(suffix)
    try:
        token = create_token(seed["user_id"], seed["user_role"])
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get(
                f"/api/courses/{seed['course_slug']}",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["slug"] == seed["course_slug"]
        assert data["unit_count"] == 2
        assert data["completed_unit_count"] == 0
        assert data["progress_pct"] == 0

        modules_by_order = {m["order"]: m for m in data["modules"]}
        assert modules_by_order[1]["is_locked"] is False
        assert modules_by_order[2]["is_locked"] is True
    finally:
        await _cleanup(seed)


async def test_linear_course_unlocks_after_success_submission():
    suffix = uuid.uuid4().hex[:8]
    seed = await _seed_linear_course(suffix)
    try:
        await _add_success_submission(seed["user_id"], seed["task1_id"])
        token = create_token(seed["user_id"], seed["user_role"])
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get(
                f"/api/courses/{seed['course_slug']}",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["unit_count"] == 2
        assert data["completed_unit_count"] == 1
        assert data["progress_pct"] == 50

        modules_by_order = {m["order"]: m for m in data["modules"]}
        assert modules_by_order[1]["is_locked"] is False
        assert modules_by_order[2]["is_locked"] is False
    finally:
        await _cleanup(seed)
