"""Quiz with review_mode=manual: stays pending, auto_score recorded."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from auth import create_token, hash_password
from database import async_session, engine
from main import app
from models import SubmissionStatus, Task, TaskSubmission, TaskType, User, UserRole

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
async def _fresh_engine_per_test():
    await engine.dispose()
    yield
    await engine.dispose()


async def test_manual_quiz_submit_stays_pending_and_records_auto_score():
    suffix = uuid.uuid4().hex[:8]
    async with async_session() as db:
        user = User(
            username=f"stu_manq_{suffix}",
            password_hash=hash_password("x"),
            full_name="S",
            role=UserRole.student,
        )
        task = Task(
            slug=f"quiz-manual-1-{suffix}",
            title="Manual quiz",
            description="",
            type=TaskType.quiz,
            config={
                "review_mode": "manual",
                "questions": [
                    {"id": 1, "text": "1+1?", "options": ["1", "2"], "correct_answer": "2"},
                    {"id": 2, "text": "2+2?", "options": ["3", "4"], "correct_answer": "4"},
                ],
            },
        )
        db.add_all([user, task])
        await db.commit()
        await db.refresh(user)
        await db.refresh(task)
        token = create_token(user.id, user.role.value)
        tid = task.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(
            f"/api/quiz/{tid}/submit",
            json={"answers": {"1": "2", "2": "3"}},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 200, r.text

    async with async_session() as db:
        res = await db.execute(
            TaskSubmission.__table__.select().where(TaskSubmission.task_id == tid)
        )
        rows = res.fetchall()
        assert len(rows) == 1
        sub = rows[0]
        assert sub.status == SubmissionStatus.pending
        auto = sub.details.get("auto_score")
        assert auto == {"score": 1, "total": 2, "correct": [1], "wrong": [2]}
