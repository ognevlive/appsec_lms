"""After a fail verdict the student can create a new submission."""
import io
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from auth import create_token, hash_password
from database import async_session, engine
from main import app
from models import Task, TaskType, User, UserRole

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
async def _fresh_engine_per_test():
    await engine.dispose()
    yield
    await engine.dispose()


async def test_resubmit_allowed_after_fail():
    suffix = uuid.uuid4().hex[:8]
    async with async_session() as db:
        admin = User(
            username=f"adm_res_{suffix}",
            password_hash=hash_password("x"),
            full_name="A",
            role=UserRole.admin,
        )
        stud = User(
            username=f"stu_res_{suffix}",
            password_hash=hash_password("x"),
            full_name="S",
            role=UserRole.student,
        )
        task = Task(
            slug=f"theory-resub-{suffix}",
            title="Resub",
            type=TaskType.theory,
            config={
                "review_mode": "manual",
                "file_upload": {
                    "enabled": True,
                    "max_files": 1,
                    "max_size_mb": 1,
                    "allowed_ext": ["txt"],
                    "required": True,
                },
            },
        )
        db.add_all([admin, stud, task])
        await db.commit()
        await db.refresh(admin)
        await db.refresh(stud)
        await db.refresh(task)
        admin_token = create_token(admin.id, admin.role.value)
        stud_token = create_token(stud.id, stud.role.value)
        tid = task.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r1 = await ac.post(
            f"/api/submissions/{tid}",
            files=[("files", ("a.txt", io.BytesIO(b"hi"), "text/plain"))],
            headers={"Authorization": f"Bearer {stud_token}"},
        )
        assert r1.status_code == 201
        sub1 = r1.json()["id"]

        r2 = await ac.post(
            f"/api/admin/submissions/{sub1}/review",
            json={"status": "fail", "comment": "redo"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r2.status_code == 200

        r3 = await ac.post(
            f"/api/submissions/{tid}",
            files=[("files", ("b.txt", io.BytesIO(b"hi2"), "text/plain"))],
            headers={"Authorization": f"Bearer {stud_token}"},
        )
        assert r3.status_code == 201
        assert r3.json()["id"] != sub1
        assert r3.json()["status"] == "pending"
