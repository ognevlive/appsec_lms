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

        pm = await c.patch(f"/api/admin/content/modules/{mid}",
                           json={"title": "M1-new", "estimated_hours": 2}, headers=h)
        assert pm.status_code == 200
        assert pm.json()["title"] == "M1-new"

        pu = await c.patch(f"/api/admin/content/units/{uid}",
                           json={"is_required": False}, headers=h)
        assert pu.json()["is_required"] is False

        du = await c.delete(f"/api/admin/content/units/{uid}", headers=h)
        assert du.status_code == 204

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

        lst = await c.get("/api/admin/content/courses", headers=h)
        from sqlalchemy import select
        from models import Module
        async with async_session() as db:
            rows = await db.execute(
                select(Module.id, Module.order).where(Module.course_id == cid).order_by(Module.order)
            )
            pairs = list(rows.all())
        assert pairs[0][0] == m2["id"]
        assert pairs[1][0] == m1["id"]
