import io
import uuid
import zipfile

import pytest
import yaml
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


async def test_course_bundle_export_contains_tasks():
    token = await _admin_token()
    h = {"Authorization": f"Bearer {token}"}
    suffix = uuid.uuid4().hex[:6]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        cr = await c.post("/api/admin/content/courses",
                          json={"slug": f"cb-{suffix}", "title": "Cb"}, headers=h)
        cid = cr.json()["id"]
        tr = await c.post("/api/admin/content/tasks",
                          json={"slug": f"tb-{suffix}", "title": "T",
                                "type": "theory", "config": {}}, headers=h)
        tid = tr.json()["id"]
        mr = await c.post(f"/api/admin/content/courses/{cid}/modules",
                          json={"title": "M", "order": 1}, headers=h)
        mid = mr.json()["id"]
        await c.post(f"/api/admin/content/modules/{mid}/units",
                     json={"task_id": tid, "unit_order": 1, "is_required": True},
                     headers=h)

        er = await c.get(f"/api/admin/content/courses/{cid}/export?bundle=true",
                         headers=h)
        assert er.status_code == 200
        zf = zipfile.ZipFile(io.BytesIO(er.content))
        assert "course.yaml" in zf.namelist()
        task_files = [n for n in zf.namelist() if n.startswith("tasks/")]
        assert len(task_files) == 1


async def test_import_course_missing_task_returns_400():
    token = await _admin_token()
    h = {"Authorization": f"Bearer {token}"}
    suffix = uuid.uuid4().hex[:6]
    course_manifest = {
        "slug": f"imp-{suffix}", "title": "Imp", "description": "", "order": 0,
        "config": {},
        "modules": [{"title": "M", "order": 1, "description": "",
                      "estimated_hours": None, "learning_outcomes": [], "config": {},
                      "units": [{"task_slug": "nonexistent-task",
                                  "unit_order": 1, "is_required": True}]}],
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("course.yaml", yaml.safe_dump(course_manifest))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/admin/content/courses/import",
                         files={"file": ("b.zip", buf.getvalue(), "application/zip")},
                         headers=h)
        assert r.status_code == 400
        assert "nonexistent-task" in r.text
