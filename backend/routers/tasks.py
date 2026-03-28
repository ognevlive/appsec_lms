from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models import Task, TaskSubmission, User
from schemas import SubmissionOut, TaskCatalogOut, TaskDetail, TheoryRef

router = APIRouter(prefix="/api/tasks", tags=["tasks"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[TaskCatalogOut])
async def list_tasks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).order_by(Task.order, Task.id))
    tasks = result.scalars().all()
    return [
        TaskCatalogOut(
            id=t.id,
            title=t.title,
            description=t.description,
            type=t.type,
            order=t.order,
            difficulty=t.config.get("difficulty") if t.config else None,
            tags=t.config.get("tags", []) if t.config else [],
            max_points=t.config.get("max_points") if t.config else None,
        )
        for t in tasks
    ]


@router.get("/my-statuses")
async def my_task_statuses(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TaskSubmission.task_id, TaskSubmission.status)
        .where(TaskSubmission.user_id == user.id)
        .order_by(TaskSubmission.submitted_at.desc())
    )
    rows = result.all()
    statuses: dict[int, str] = {}
    for task_id, status in rows:
        if task_id not in statuses:
            # First occurrence is the latest (ordered by desc)
            # But "success" takes priority
            statuses[task_id] = status.value
        if status.value == "success":
            statuses[task_id] = "success"
    return statuses


@router.get("/{task_id}", response_model=TaskDetail)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    theory_refs: list[TheoryRef] = []
    ref_ids = (task.config or {}).get("theory_refs", [])
    if ref_ids:
        refs_result = await db.execute(
            select(Task.id, Task.title).where(Task.id.in_(ref_ids))
        )
        ref_map = {row.id: row.title for row in refs_result.all()}
        theory_refs = [
            TheoryRef(id=rid, title=ref_map[rid])
            for rid in ref_ids if rid in ref_map
        ]

    return TaskDetail(
        id=task.id,
        title=task.title,
        description=task.description,
        type=task.type,
        order=task.order,
        config=task.config or {},
        theory_refs=theory_refs,
    )


@router.get("/{task_id}/submissions", response_model=list[SubmissionOut])
async def my_submissions(
    task_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TaskSubmission)
        .where(TaskSubmission.task_id == task_id, TaskSubmission.user_id == user.id)
        .order_by(TaskSubmission.submitted_at.desc())
    )
    return result.scalars().all()
