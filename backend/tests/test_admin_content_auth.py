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
