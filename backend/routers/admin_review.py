"""Admin review router: pending queue, submission detail, file download, verdict."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from auth import require_admin
from database import get_db
from models import (
    Course,
    Module,
    ModuleUnit,
    SubmissionFile,
    SubmissionStatus,
    Task,
    TaskSubmission,
    User,
)
from schemas import (
    ReviewQueueItem,
    ReviewQueueResponse,
    ReviewVerdict,
    SubmissionDetail,
    SubmissionFileOut,
)
from services.uploads import absolute_stored_path

router = APIRouter(
    prefix="/api/admin",
    tags=["admin-review"],
    dependencies=[Depends(require_admin)],
)


def _is_manual(task: Task) -> bool:
    return (task.config or {}).get("review_mode") == "manual"


async def _pending_manual_base_query(db: AsyncSession):
    """Base SELECT for pending submissions whose task has review_mode=manual."""
    q = (
        select(TaskSubmission, Task, User)
        .join(Task, TaskSubmission.task_id == Task.id)
        .join(User, TaskSubmission.user_id == User.id)
        .where(
            TaskSubmission.status == SubmissionStatus.pending,
            Task.config["review_mode"].astext == "manual",
        )
        .order_by(TaskSubmission.submitted_at.asc())
    )
    return q


@router.get("/review/queue", response_model=ReviewQueueResponse)
async def review_queue(
    course_id: int | None = Query(default=None),
    user_id: int | None = Query(default=None),
    task_id: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    q = await _pending_manual_base_query(db)

    if user_id is not None:
        q = q.where(TaskSubmission.user_id == user_id)
    if task_id is not None:
        q = q.where(TaskSubmission.task_id == task_id)
    if course_id is not None:
        q = q.where(
            TaskSubmission.task_id.in_(
                select(ModuleUnit.task_id)
                .join(Module, ModuleUnit.module_id == Module.id)
                .where(Module.course_id == course_id)
            )
        )

    # Count
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    rows = (
        await db.execute(q.offset((page - 1) * per_page).limit(per_page))
    ).all()

    # Course lookup per task (first course via any module)
    task_ids = [t.id for (_s, t, _u) in rows]
    course_map: dict[int, tuple[int, str]] = {}
    if task_ids:
        course_rows = await db.execute(
            select(ModuleUnit.task_id, Course.id, Course.title)
            .join(Module, ModuleUnit.module_id == Module.id)
            .join(Course, Module.course_id == Course.id)
            .where(ModuleUnit.task_id.in_(task_ids))
        )
        for tid, cid, ctitle in course_rows.all():
            course_map.setdefault(tid, (cid, ctitle))

    items = [
        ReviewQueueItem(
            submission_id=s.id,
            task_id=t.id,
            task_title=t.title,
            user_id=u.id,
            username=u.username,
            user_full_name=u.full_name or "",
            submitted_at=s.submitted_at,
            course_id=course_map.get(t.id, (None, None))[0],
            course_title=course_map.get(t.id, (None, None))[1],
        )
        for (s, t, u) in rows
    ]
    return ReviewQueueResponse(items=items, total=total, page=page, per_page=per_page)


@router.get("/review/queue/count")
async def review_queue_count(db: AsyncSession = Depends(get_db)):
    q = await _pending_manual_base_query(db)
    count = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
    return {"count": count}


@router.get("/submissions/{submission_id}", response_model=SubmissionDetail)
async def admin_get_submission(
    submission_id: int, db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(TaskSubmission)
        .options(selectinload(TaskSubmission.files))
        .where(TaskSubmission.id == submission_id)
    )
    sub = res.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Not found")
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


@router.get("/submissions/{submission_id}/files/{file_id}")
async def admin_download_file(
    submission_id: int, file_id: int, db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(SubmissionFile).where(
            SubmissionFile.id == file_id,
            SubmissionFile.submission_id == submission_id,
        )
    )
    f = res.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="Not found")
    try:
        path = absolute_stored_path(f.stored_path)
    except ValueError:
        raise HTTPException(status_code=500, detail="path_error")
    if not path.exists():
        raise HTTPException(status_code=404, detail="file_missing")
    return FileResponse(path, media_type="application/octet-stream", filename=f.filename)


@router.post("/submissions/{submission_id}/review", response_model=SubmissionDetail)
async def submit_review(
    submission_id: int,
    body: ReviewVerdict,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if body.status not in (SubmissionStatus.success, SubmissionStatus.fail):
        raise HTTPException(status_code=400, detail="bad_status")

    res = await db.execute(
        select(TaskSubmission)
        .options(selectinload(TaskSubmission.files))
        .where(TaskSubmission.id == submission_id)
    )
    sub = res.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Not found")
    if sub.reviewer_id is not None or sub.status != SubmissionStatus.pending:
        raise HTTPException(status_code=400, detail="already_reviewed")

    sub.status = body.status
    sub.reviewer_id = admin.id
    sub.reviewed_at = datetime.now(timezone.utc)
    sub.review_comment = body.comment
    await db.commit()
    await db.refresh(sub)

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
