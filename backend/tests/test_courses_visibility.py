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
