import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from auth import create_token, hash_password
from database import async_session, engine
from main import app
from models import Course, Module, ModuleUnit, User, UserRole

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


async def test_get_task_detail_with_usage():
    token = await _admin_token()
    suffix = uuid.uuid4().hex[:6]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        cr = await c.post("/api/admin/content/tasks",
                          json={"slug": f"used-{suffix}", "title": "U", "type": "theory", "config": {}},
                          headers={"Authorization": f"Bearer {token}"})
        task_id = cr.json()["id"]

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
