"""Admin review queue and verdict endpoints."""
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


async def _seed() -> dict:
    suffix = uuid.uuid4().hex[:8]
    async with async_session() as db:
        admin = User(
            username=f"admin_rev_{suffix}",
            password_hash=hash_password("x"),
            full_name="Admin",
            role=UserRole.admin,
        )
        student = User(
            username=f"stud_rev_{suffix}",
            password_hash=hash_password("x"),
            full_name="Stud",
            role=UserRole.student,
        )
        task = Task(
            slug=f"theory-review-1-{suffix}",
            title="Review me",
            description="",
            type=TaskType.theory,
            config={
                "review_mode": "manual",
                "file_upload": {
                    "enabled": True,
                    "max_files": 3,
                    "max_size_mb": 5,
                    "allowed_ext": ["pdf"],
                    "required": True,
                },
            },
        )
        db.add_all([admin, student, task])
        await db.commit()
        await db.refresh(admin)
        await db.refresh(student)
        await db.refresh(task)
        return {
            "admin_token": create_token(admin.id, admin.role.value),
            "student_token": create_token(student.id, student.role.value),
            "task_id": task.id,
            "admin_id": admin.id,
            "student_id": student.id,
        }


async def _create_pending(client: AsyncClient, seed: dict) -> int:
    files = [("files", ("r.pdf", io.BytesIO(b"%PDF"), "application/pdf"))]
    r = await client.post(
        f"/api/submissions/{seed['task_id']}",
        files=files,
        headers={"Authorization": f"Bearer {seed['student_token']}"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def test_queue_lists_pending_manual_submission():
    seed = await _seed()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await _create_pending(ac, seed)
        r = await ac.get(
            "/api/admin/review/queue",
            headers={"Authorization": f"Bearer {seed['admin_token']}"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    assert any(item["task_id"] == seed["task_id"] for item in body["items"])


async def test_queue_count():
    seed = await _seed()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await _create_pending(ac, seed)
        r = await ac.get(
            "/api/admin/review/queue/count",
            headers={"Authorization": f"Bearer {seed['admin_token']}"},
        )
    assert r.status_code == 200
    assert r.json()["count"] >= 1


async def test_admin_posts_verdict_success():
    seed = await _seed()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        sub_id = await _create_pending(ac, seed)
        r = await ac.post(
            f"/api/admin/submissions/{sub_id}/review",
            json={"status": "success", "comment": "nicely done"},
            headers={"Authorization": f"Bearer {seed['admin_token']}"},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "success"
    assert body["review_comment"] == "nicely done"
    assert body["reviewer_id"] == seed["admin_id"]


async def test_double_review_rejected():
    seed = await _seed()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        sub_id = await _create_pending(ac, seed)
        await ac.post(
            f"/api/admin/submissions/{sub_id}/review",
            json={"status": "fail", "comment": "x"},
            headers={"Authorization": f"Bearer {seed['admin_token']}"},
        )
        r = await ac.post(
            f"/api/admin/submissions/{sub_id}/review",
            json={"status": "success", "comment": "y"},
            headers={"Authorization": f"Bearer {seed['admin_token']}"},
        )
    assert r.status_code == 400
    assert r.json()["detail"] == "already_reviewed"


async def test_non_admin_forbidden():
    seed = await _seed()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get(
            "/api/admin/review/queue",
            headers={"Authorization": f"Bearer {seed['student_token']}"},
        )
    assert r.status_code == 403
