import io
import uuid
import zipfile

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


async def _admin_token():
    async with async_session() as db:
        u = User(username=f"a-{uuid.uuid4().hex[:6]}",
                 password_hash=hash_password("x"), role=UserRole.admin)
        db.add(u); await db.commit(); await db.refresh(u)
        return create_token(u.id, "admin")


async def test_export_import_task_roundtrip():
    token = await _admin_token()
    h = {"Authorization": f"Bearer {token}"}
    suffix = uuid.uuid4().hex[:6]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        cr = await c.post("/api/admin/content/tasks",
                          json={"slug": f"io-{suffix}", "title": "IO",
                                "type": "theory", "config": {"content_kind": "text",
                                                              "content": "hi"}},
                          headers=h)
        tid = cr.json()["id"]

        er = await c.get(f"/api/admin/content/tasks/{tid}/export", headers=h)
        assert er.status_code == 200
        assert er.headers["content-type"] == "application/zip"
        zf = zipfile.ZipFile(io.BytesIO(er.content))
        assert "manifest.yaml" in zf.namelist()

        # delete original
        await c.delete(f"/api/admin/content/tasks/{tid}", headers=h)

        # import
        files = {"file": ("bundle.zip", er.content, "application/zip")}
        ir = await c.post("/api/admin/content/tasks/import", files=files, headers=h)
        assert ir.status_code == 201
        assert ir.json()["slug"] == f"io-{suffix}"
