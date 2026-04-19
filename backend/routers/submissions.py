"""Student-facing submissions router: create submissions with files, fetch own, download."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from auth import get_current_user
from database import get_db
from models import SubmissionFile, SubmissionStatus, Task, TaskSubmission, TaskType, User
from schemas import SubmissionDetail, SubmissionFileOut
from services.unlock_guard import require_unit_unlocked
from services.uploads import (
    absolute_stored_path,
    delete_submission_files,
    save_submission_files,
    validate_upload_config,
)

router = APIRouter(prefix="/api/submissions", tags=["submissions"])


def _serialize(sub: TaskSubmission) -> SubmissionDetail:
    return SubmissionDetail(
        id=sub.id,
        user_id=sub.user_id,
        task_id=sub.task_id,
        status=sub.status,
        details=sub.details or {},
        submitted_at=sub.submitted_at,
        reviewer_id=sub.reviewer_id,
        reviewed_at=sub.reviewed_at,
        review_comment=sub.review_comment,
        files=[SubmissionFileOut.model_validate(f) for f in sub.files],
    )


async def _auto_grade(
    task: Task,
    submission: TaskSubmission,
    answer_text: str | None,
    review_mode: str,
) -> None:
    """Compute preliminary auto grading into submission.details. Status set by caller."""
    details = dict(submission.details or {})
    if answer_text is not None:
        details["answer_text"] = answer_text

    if task.type == TaskType.quiz and review_mode == "auto":
        # Quiz answers are expected as JSON inside answer_text for this generic endpoint.
        import json

        try:
            answers = json.loads(answer_text or "{}")
        except json.JSONDecodeError:
            answers = {}
        questions = (task.config or {}).get("questions", [])
        correct, wrong = [], []
        for q in questions:
            qid = str(q["id"])
            if answers.get(qid, "") == q["correct_answer"]:
                correct.append(q["id"])
            else:
                wrong.append(q["id"])
        details["auto_score"] = {
            "score": len(correct),
            "total": len(questions),
            "correct": correct,
            "wrong": wrong,
        }
    submission.details = details


@router.post(
    "/{task_id}",
    response_model=SubmissionDetail,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_unit_unlocked)],
)
async def create_submission(
    task_id: int,
    answer_text: str | None = Form(default=None),
    files: list[UploadFile] = File(default_factory=list),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task_res = await db.execute(select(Task).where(Task.id == task_id))
    task = task_res.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    cfg = task.config or {}
    review_mode = cfg.get("review_mode", "auto")
    uploads_enabled = bool((cfg.get("file_upload") or {}).get("enabled"))
    answer_cfg = cfg.get("answer_text") or {}

    if not uploads_enabled and len(files) > 0:
        raise HTTPException(status_code=400, detail="uploads_disabled")
    if answer_cfg.get("required") and not (answer_text or "").strip():
        raise HTTPException(status_code=400, detail="answer_required")

    # Validate counts/required up front (per-file size enforced during streaming).
    try:
        if uploads_enabled:
            validate_upload_config(cfg, file_count=len(files))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    is_manual = review_mode == "manual"
    # Guard: auto mode only supports quiz tasks via this endpoint.
    if not is_manual and task.type != TaskType.quiz:
        raise HTTPException(status_code=400, detail="auto_unsupported_task_type")

    submission = TaskSubmission(
        user_id=user.id,
        task_id=task_id,
        status=SubmissionStatus.pending,
        details={},
    )
    db.add(submission)
    await db.flush()  # need id for directory

    try:
        if files:
            await save_submission_files(submission, cfg, files, db)

        await _auto_grade(task, submission, answer_text, review_mode)

        if not is_manual:
            # Auto-finalize: quiz -> success if full score; others currently not auto-passable via this endpoint
            auto = (submission.details or {}).get("auto_score")
            if task.type == TaskType.quiz and auto and auto["score"] == auto["total"]:
                submission.status = SubmissionStatus.success
            elif task.type == TaskType.quiz:
                submission.status = SubmissionStatus.fail
            else:
                # No auto grading available -> keep pending
                submission.status = SubmissionStatus.pending
        await db.commit()
    except HTTPException:
        await db.rollback()
        delete_submission_files(submission.id)
        raise
    except ValueError as e:
        await db.rollback()
        delete_submission_files(submission.id)
        raise HTTPException(status_code=400, detail=str(e))

    # Reload with files
    res = await db.execute(
        select(TaskSubmission)
        .options(selectinload(TaskSubmission.files))
        .where(TaskSubmission.id == submission.id)
    )
    fresh = res.scalar_one()
    return _serialize(fresh)


@router.get("/{submission_id}", response_model=SubmissionDetail)
async def get_submission(
    submission_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(TaskSubmission)
        .options(selectinload(TaskSubmission.files))
        .where(TaskSubmission.id == submission_id)
    )
    sub = res.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Not found")
    if sub.user_id != user.id and user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    return _serialize(sub)


@router.get("/{submission_id}/files/{file_id}")
async def download_submission_file(
    submission_id: int,
    file_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(SubmissionFile, TaskSubmission)
        .join(TaskSubmission, SubmissionFile.submission_id == TaskSubmission.id)
        .where(SubmissionFile.id == file_id, TaskSubmission.id == submission_id)
    )
    row = res.first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    file_rec, sub = row
    if sub.user_id != user.id and user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        path = absolute_stored_path(file_rec.stored_path)
    except ValueError:
        raise HTTPException(status_code=500, detail="path_error")

    if not path.exists():
        raise HTTPException(status_code=404, detail="file_missing")

    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename=file_rec.filename,
    )
