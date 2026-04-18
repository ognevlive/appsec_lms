"""Admin CRUD for courses, modules, units, tasks + import/export.

Защищён require_admin. Все endpoints под /api/admin/content.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from auth import require_admin
from database import get_db
from models import Course, Module, ModuleUnit, Task, TaskType, User
from schemas_admin import (
    CourseCreate,
    CourseUpdate,
    ModuleCreate,
    ModuleUpdate,
    ReorderItem,
    TaskCreate,
    TaskOutAdmin,
    TaskUpdate,
    UnitCreate,
    UnitUpdate,
)
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


class CourseOutAdmin(BaseModel):
    id: int
    slug: str
    title: str
    description: str
    order: int
    config: dict
    is_visible: bool

    model_config = ConfigDict(from_attributes=True)


@router.post("/courses", status_code=201, response_model=CourseOutAdmin)
async def create_course(body: CourseCreate, db: AsyncSession = Depends(get_db)):
    course = Course(
        slug=body.slug, title=body.title, description=body.description,
        order=body.order, config=body.config, is_visible=False,
    )
    db.add(course)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Slug already exists")
    await db.refresh(course)
    return course


@router.get("/courses", response_model=list[CourseOutAdmin])
async def list_courses_admin(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(select(Course).order_by(Course.order, Course.id))
    return rows.scalars().all()


@router.patch("/courses/{course_id}", response_model=CourseOutAdmin)
async def update_course(course_id: int, body: CourseUpdate,
                         db: AsyncSession = Depends(get_db)):
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(course, k, v)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Slug already exists")
    await db.refresh(course)
    return course


@router.delete("/courses/{course_id}", status_code=204)
async def delete_course(course_id: int, db: AsyncSession = Depends(get_db)):
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    if course.is_visible:
        raise HTTPException(409, "Course must be hidden before deletion")
    await db.delete(course)
    await db.commit()


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


async def _usage_for_task(task_id: int, db: AsyncSession) -> list[dict]:
    rows = await db.execute(
        select(Course.id, Course.slug, Module.id, ModuleUnit.id)
        .join(Module, Module.course_id == Course.id)
        .join(ModuleUnit, ModuleUnit.module_id == Module.id)
        .where(ModuleUnit.task_id == task_id)
    )
    return [
        {"course_id": c_id, "course_slug": c_slug, "module_id": m_id, "unit_id": u_id}
        for c_id, c_slug, m_id, u_id in rows.all()
    ]


@router.get("/tasks/{task_id}", response_model=TaskOutAdmin)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return _task_out(task, usage=await _usage_for_task(task_id, db))


@router.patch("/tasks/{task_id}", response_model=TaskOutAdmin)
async def update_task(
    task_id: int,
    body: TaskUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    data = body.model_dump(exclude_unset=True)
    if "config" in data:
        data["config"] = apply_flag_to_config(data["config"])
    for field, value in data.items():
        setattr(task, field, value)
    task.author_id = admin.id
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Slug already exists")
    await db.refresh(task)
    return _task_out(task, usage=await _usage_for_task(task_id, db))


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    usage = await _usage_for_task(task_id, db)
    if usage:
        raise HTTPException(status_code=409, detail={"message": "Task is in use", "usage": usage})
    await db.delete(task)
    await db.commit()
