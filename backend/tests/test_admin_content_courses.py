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
