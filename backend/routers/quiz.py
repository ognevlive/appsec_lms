from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models import SubmissionStatus, Task, TaskSubmission, TaskType, User
from schemas import QuizQuestion, QuizResult, QuizSubmit
from services.unlock_guard import require_unit_unlocked

router = APIRouter(prefix="/api/quiz", tags=["quiz"])


@router.get("/{task_id}/questions", response_model=list[QuizQuestion])
async def get_questions(
    task_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task or task.type != TaskType.quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    questions = task.config.get("questions", [])
    return [
        QuizQuestion(id=q["id"], text=q["text"], options=q["options"]) for q in questions
    ]


@router.post("/{task_id}/submit", response_model=QuizResult, dependencies=[Depends(require_unit_unlocked)])
async def submit_quiz(
    task_id: int,
    body: QuizSubmit,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task or task.type != TaskType.quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    questions = task.config.get("questions", [])
    correct, wrong = [], []
    for q in questions:
        qid = str(q["id"])
        user_answer = body.answers.get(qid, "")
        if user_answer == q["correct_answer"]:
            correct.append(q["id"])
        else:
            wrong.append(q["id"])

    score = len(correct)
    total = len(questions)
    passed = total > 0 and score == total

    is_manual = (task.config or {}).get("review_mode") == "manual"
    auto_score = {"score": score, "total": total, "correct": correct, "wrong": wrong}
    details = {"auto_score": auto_score} if is_manual else {
        "score": score, "total": total, "correct": correct, "wrong": wrong,
    }

    if is_manual:
        sub_status = SubmissionStatus.pending
    else:
        sub_status = SubmissionStatus.success if passed else SubmissionStatus.fail

    submission = TaskSubmission(
        user_id=user.id,
        task_id=task_id,
        status=sub_status,
        details=details,
    )
    db.add(submission)
    await db.commit()

    return QuizResult(score=score, total=total, correct=correct, wrong=wrong)
