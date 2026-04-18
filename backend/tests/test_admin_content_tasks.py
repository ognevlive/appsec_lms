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
