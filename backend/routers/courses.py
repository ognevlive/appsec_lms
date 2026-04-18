from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from auth import get_current_user
from database import get_db
from models import Course, Module, ModuleUnit, TaskSubmission, TaskType, User
from schemas import CourseDetail, CourseOut, ModuleOut, UnitOut
from services.progression import is_module_locked

router = APIRouter(prefix="/api/courses", tags=["courses"], dependencies=[Depends(get_current_user)])

modules_router = APIRouter(prefix="/api/modules", tags=["modules"], dependencies=[Depends(get_current_user)])


async def _user_statuses(user_id: int, db: AsyncSession) -> dict[int, str]:
    """Return best submission status per task_id for a user ('success' wins)."""
    result = await db.execute(
        select(TaskSubmission.task_id, TaskSubmission.status)
        .where(TaskSubmission.user_id == user_id)
        .order_by(TaskSubmission.submitted_at.desc())
    )
    statuses: dict[int, str] = {}
    for task_id, status in result.all():
        val = status.value if hasattr(status, "value") else status
        if task_id not in statuses or val == "success":
            statuses[task_id] = val
    return statuses


def _course_agg(course: Course, statuses: dict[int, str]) -> tuple[int, int, int]:
    """Return (module_count, unit_count_required, completed_unit_count_required)."""
    module_count = len(course.modules)
    unit_count = 0
    completed = 0
    for m in course.modules:
        for u in m.units:
            if u.is_required:
                unit_count += 1
                if statuses.get(u.task_id) == "success":
                    completed += 1
    return module_count, unit_count, completed


def _build_unit_out(mu: ModuleUnit, statuses: dict[int, str]) -> UnitOut:
    cfg = mu.task.config or {}
    content_kind = None
    if mu.task.type == TaskType.theory:
        content_kind = cfg.get("content_kind", "text")
    return UnitOut(
        id=mu.id,
        task_id=mu.task_id,
        task_slug=mu.task.slug or "",
        task_title=mu.task.title,
        task_type=mu.task.type,
        task_difficulty=cfg.get("difficulty"),
        content_kind=content_kind,
        unit_order=mu.unit_order,
        is_required=mu.is_required,
        user_status=statuses.get(mu.task_id),
    )


def _build_module_out(course: Course, module: Module, statuses: dict[int, str]) -> ModuleOut:
    units = [_build_unit_out(mu, statuses) for mu in module.units]
    required = [u for u in units if u.is_required]
    completed = sum(1 for u in required if u.user_status == "success")
    return ModuleOut(
        id=module.id,
        title=module.title,
        description=module.description or "",
        order=module.order,
        estimated_hours=module.estimated_hours,
        learning_outcomes=module.learning_outcomes or [],
        config=module.config or {},
        is_locked=is_module_locked(course, module, statuses),
        unit_count=len(required),
        completed_unit_count=completed,
        units=units,
    )


def _load_course_query():
    return (
        select(Course)
        .options(
            selectinload(Course.modules)
            .selectinload(Module.units)
            .selectinload(ModuleUnit.task)
        )
        .order_by(Course.order, Course.id)
    )


@router.get("", response_model=list[CourseOut])
async def list_courses(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(_load_course_query())
    courses = result.scalars().unique().all()
    statuses = await _user_statuses(user.id, db)
    out: list[CourseOut] = []
    for c in courses:
        module_count, unit_count, completed = _course_agg(c, statuses)
        pct = round(completed / unit_count * 100) if unit_count else 0
        out.append(CourseOut(
            id=c.id,
            slug=c.slug,
            title=c.title,
            description=c.description or "",
            order=c.order,
            config=c.config or {},
            module_count=module_count,
            unit_count=unit_count,
            completed_unit_count=completed,
            progress_pct=pct,
        ))
    return out


@router.get("/{slug_or_id}", response_model=CourseDetail)
async def get_course(
    slug_or_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = _load_course_query()
    if slug_or_id.isdigit():
        q = q.where(Course.id == int(slug_or_id))
    else:
        q = q.where(Course.slug == slug_or_id)
    result = await db.execute(q)
    course = result.scalars().unique().one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    statuses = await _user_statuses(user.id, db)
    module_count, unit_count, completed = _course_agg(course, statuses)
    pct = round(completed / unit_count * 100) if unit_count else 0

    return CourseDetail(
        id=course.id,
        slug=course.slug,
        title=course.title,
        description=course.description or "",
        order=course.order,
        config=course.config or {},
        module_count=module_count,
        unit_count=unit_count,
        completed_unit_count=completed,
        progress_pct=pct,
        modules=[_build_module_out(course, m, statuses) for m in course.modules],
    )


@modules_router.get("/{module_id}", response_model=ModuleOut)
async def get_module(
    module_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Module)
        .options(selectinload(Module.units).selectinload(ModuleUnit.task))
        .where(Module.id == module_id)
    )
    module = result.scalar_one_or_none()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    # load parent course for progression check
    course_result = await db.execute(
        _load_course_query().where(Course.id == module.course_id)
    )
    course = course_result.scalars().unique().one()

    statuses = await _user_statuses(user.id, db)
    return _build_module_out(course, module, statuses)
