"""Tests for student submissions router (file upload + manual review)."""
import io

import pytest
from httpx import ASGITransport, AsyncClient

from auth import create_token, hash_password
from database import async_session, engine
from main import app
from models import SubmissionFile, Task, TaskSubmission, TaskType, User, UserRole

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
async def _fresh_engine_per_test():
    await engine.dispose()
    yield
    await engine.dispose()


async def _seed_manual_theory() -> dict:
    async with async_session() as db:
        user = User(
            username="student_sub_1",
            password_hash=hash_password("x"),
            full_name="Stu",
            role=UserRole.student,
        )
        task = Task(
            slug="theory-manual-1",
            title="Manual theory",
            description="",
            type=TaskType.theory,
            config={
                "review_mode": "manual",
                "file_upload": {
                    "enabled": True,
                    "max_files": 3,
                    "max_size_mb": 5,
                    "allowed_ext": ["pdf", "txt"],
                    "required": True,
                },
                "answer_text": {"enabled": True, "required": False},
            },
        )
        db.add_all([user, task])
        await db.commit()
        await db.refresh(user)
        await db.refresh(task)
        token = create_token(user.id, user.role.value)
        return {"user_id": user.id, "task_id": task.id, "token": token}


async def test_manual_submission_with_file_becomes_pending():
    seed = await _seed_manual_theory()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        files = [("files", ("report.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf"))]
        data = {"answer_text": "see attached"}
        resp = await ac.post(
            f"/api/submissions/{seed['task_id']}",
            data=data,
            files=files,
            headers={"Authorization": f"Bearer {seed['token']}"},
        )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "pending"
    assert len(body["files"]) == 1
    assert body["files"][0]["filename"] == "report.pdf"

    async with async_session() as db:
        sub = await db.get(TaskSubmission, body["id"])
        assert sub.status.value == "pending"
        assert sub.details.get("answer_text") == "see attached"
