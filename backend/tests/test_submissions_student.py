"""Tests for student submissions router (file upload + manual review)."""
import io
import uuid

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
    suffix = uuid.uuid4().hex[:8]
    async with async_session() as db:
        user = User(
            username=f"student_sub_1_{suffix}",
            password_hash=hash_password("x"),
            full_name="Stu",
            role=UserRole.student,
        )
        task = Task(
            slug=f"theory-manual-{suffix}",
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


async def _seed_auto_quiz_no_uploads() -> dict:
    suffix = uuid.uuid4().hex[:8]
    async with async_session() as db:
        user = User(
            username=f"student_sub_2_{suffix}",
            password_hash=hash_password("x"),
            full_name="Stu2",
            role=UserRole.student,
        )
        task = Task(
            slug=f"quiz-auto-{suffix}",
            title="Auto quiz",
            description="",
            type=TaskType.quiz,
            config={
                "questions": [
                    {"id": 1, "text": "1+1?", "options": ["1", "2"], "correct_answer": "2"}
                ]
            },
        )
        db.add_all([user, task])
        await db.commit()
        await db.refresh(user)
        await db.refresh(task)
        return {"user_id": user.id, "task_id": task.id, "token": create_token(user.id, user.role.value)}


async def test_rejects_files_when_upload_disabled():
    seed = await _seed_auto_quiz_no_uploads()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        files = [("files", ("x.pdf", io.BytesIO(b"data"), "application/pdf"))]
        resp = await ac.post(
            f"/api/submissions/{seed['task_id']}",
            data={"answer_text": "{}"},
            files=files,
            headers={"Authorization": f"Bearer {seed['token']}"},
        )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "uploads_disabled"


async def test_rejects_disallowed_extension():
    seed = await _seed_manual_theory()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        files = [("files", ("evil.exe", io.BytesIO(b"MZ"), "application/octet-stream"))]
        resp = await ac.post(
            f"/api/submissions/{seed['task_id']}",
            files=files,
            headers={"Authorization": f"Bearer {seed['token']}"},
        )
    assert resp.status_code == 400
    assert "ext_not_allowed" in resp.json()["detail"]


async def test_rejects_when_file_required_and_missing():
    seed = await _seed_manual_theory()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            f"/api/submissions/{seed['task_id']}",
            data={"answer_text": "no files"},
            headers={"Authorization": f"Bearer {seed['token']}"},
        )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "file_required"


async def test_other_student_cannot_fetch_submission():
    seed = await _seed_manual_theory()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        files = [("files", ("report.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf"))]
        resp = await ac.post(
            f"/api/submissions/{seed['task_id']}",
            files=files,
            headers={"Authorization": f"Bearer {seed['token']}"},
        )
    sub_id = resp.json()["id"]

    async with async_session() as db:
        other = User(
            username=f"student_other_{uuid.uuid4().hex[:8]}",
            password_hash=hash_password("x"),
            full_name="Other",
            role=UserRole.student,
        )
        db.add(other)
        await db.commit()
        await db.refresh(other)
        other_token = create_token(other.id, other.role.value)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get(
            f"/api/submissions/{sub_id}",
            headers={"Authorization": f"Bearer {other_token}"},
        )
    assert resp.status_code == 403
