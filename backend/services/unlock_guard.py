"""FastAPI dependency that blocks access to locked units."""
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from auth import get_current_user
from database import get_db
from models import Course, Module, ModuleUnit, TaskSubmission, User
from services.progression import is_module_locked


async def _user_statuses(user_id: int, db: AsyncSession) -> dict[int, str]:
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


async def require_unit_unlocked(
    task_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Verify that a unit referencing this task is unlocked for the user.

    If the task is not linked to any module (standalone catalog task) — allow.
    If linked and the module is locked by progression rules — raise 403.
    Admins bypass the check.
    """
    if user.role.value == "admin":
        return

    result = await db.execute(
        select(ModuleUnit)
        .options(
            selectinload(ModuleUnit.module)
            .selectinload(Module.course)
            .selectinload(Course.modules)
            .selectinload(Module.units)
        )
        .where(ModuleUnit.task_id == task_id)
    )
    mus = result.scalars().unique().all()
    if not mus:
        return  # standalone task, no gating

    statuses = await _user_statuses(user.id, db)
    # If ANY of the linking modules is unlocked, allow (unit is reachable via another path)
    for mu in mus:
        module = mu.module
        course = module.course
        if not is_module_locked(course, module, statuses):
            return

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="module_locked")
