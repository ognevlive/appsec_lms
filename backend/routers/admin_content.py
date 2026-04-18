"""Admin CRUD for courses, modules, units, tasks + import/export.

Защищён require_admin. Все endpoints под /api/admin/content.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from auth import require_admin
from database import get_db
from models import ModuleUnit, Task, TaskType, User
from schemas_admin import TaskCreate, TaskOutAdmin
from services.flag_hash import apply_flag_to_config

router = APIRouter(
    prefix="/api/admin/content",
    tags=["admin-content"],
    dependencies=[Depends(require_admin)],
)


def _task_out(task: Task, usage: list[dict] | None = None) -> dict:
    return {
        "id": task.id,
        "slug": task.slug,
        "title": task.title,
        "description": task.description or "",
        "order": task.order,
        "type": task.type,
        "config": task.config or {},
        "author_id": task.author_id,
        "updated_at": task.updated_at,
        "usage": usage or [],
    }


@router.get("/courses")
async def list_courses_admin():
    return []


@router.get("/tasks", response_model=list[TaskOutAdmin])
async def list_tasks(
    type: TaskType | None = None,
    search: str | None = None,
    unused: bool = False,
    db: AsyncSession = Depends(get_db),
):
    q = select(Task)
    if type is not None:
        q = q.where(Task.type == type)
    if search:
        like = f"%{search}%"
        q = q.where(or_(Task.title.ilike(like), Task.slug.ilike(like)))
    if unused:
        used_ids = select(ModuleUnit.task_id).distinct()
        q = q.where(Task.id.notin_(used_ids))
    q = q.order_by(Task.updated_at.desc())
    result = await db.execute(q)
    return [_task_out(t) for t in result.scalars().all()]


@router.post("/tasks", status_code=status.HTTP_201_CREATED, response_model=TaskOutAdmin)
async def create_task(
    body: TaskCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    config = apply_flag_to_config(body.config or {})
    task = Task(
        slug=body.slug,
        title=body.title,
        description=body.description,
        order=body.order,
        type=body.type,
        config=config,
        author_id=admin.id,
    )
    db.add(task)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Slug already exists")
    await db.refresh(task)
    return _task_out(task)
