import hashlib
import io
import uuid
import zipfile

import pytest
from httpx import ASGITransport, AsyncClient

from auth import create_token, hash_password
from database import async_session, engine
from main import app
from models import User, UserRole
from services.bundle import pack_task

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


async def test_import_rejects_non_zip():
    token = await _admin_token()
    h = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        files = {"file": ("bundle.zip", b"not a zip", "application/zip")}
        r = await c.post("/api/admin/content/tasks/import", files=files, headers=h)
        assert r.status_code == 400
        assert "not a valid zip" in r.text


async def test_import_rejects_bundle_without_manifest():
    token = await _admin_token()
    h = {"Authorization": f"Bearer {token}"}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("random.txt", "hello")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        files = {"file": ("bundle.zip", buf.getvalue(), "application/zip")}
        r = await c.post("/api/admin/content/tasks/import", files=files, headers=h)
        assert r.status_code == 400
        assert "missing file in bundle" in r.text


async def test_import_rejects_invalid_manifest():
    token = await _admin_token()
    h = {"Authorization": f"Bearer {token}"}
    blob = pack_task({
        "slug": "INVALID SLUG!",
        "title": "Bad",
        "type": "theory",
        "config": {"content_kind": "text", "content": "x"},
    })
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        files = {"file": ("bundle.zip", blob, "application/zip")}
        r = await c.post("/api/admin/content/tasks/import", files=files, headers=h)
        assert r.status_code == 422


async def test_import_strips_plaintext_flag():
    token = await _admin_token()
    h = {"Authorization": f"Bearer {token}"}
    suffix = uuid.uuid4().hex[:6]
    plaintext = "FLAG{secret}"
    expected_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    blob = pack_task({
        "slug": f"ctf-{suffix}",
        "title": "CTF",
        "type": "ctf",
        "config": {"docker_image": "x", "flag": plaintext},
    })
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        files = {"file": ("bundle.zip", blob, "application/zip")}
        r = await c.post("/api/admin/content/tasks/import", files=files, headers=h)
        assert r.status_code == 201
        cfg = r.json()["config"]
        assert "flag" not in cfg
        assert cfg["flag_hash"] == expected_hash
