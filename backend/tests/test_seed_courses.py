"""Smoke test: seed runs without error on the actual repo YAML and creates courses."""
import os
import pytest
from sqlalchemy import select

from database import async_session, engine
from models import Course, Module, ModuleUnit
from seed import seed_tasks

pytestmark = pytest.mark.anyio

REPO_TASKS = os.path.join(os.path.dirname(__file__), "..", "..", "tasks")


@pytest.fixture(autouse=True)
async def _dispose_engine():
    await engine.dispose()
    yield
    await engine.dispose()


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
        assert len(modules) >= 1


async def test_seed_is_idempotent():
    if not os.path.isdir(os.path.join(REPO_TASKS, "courses")):
        pytest.skip("tasks/courses not generated yet in this environment")
    await seed_tasks(REPO_TASKS)
    async with async_session() as db:
        mus_a = (await db.execute(select(ModuleUnit))).scalars().all()
    await seed_tasks(REPO_TASKS)
    async with async_session() as db:
        mus_b = (await db.execute(select(ModuleUnit))).scalars().all()
    assert len(mus_a) == len(mus_b)
