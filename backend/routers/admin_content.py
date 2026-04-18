"""Admin CRUD for courses, modules, units, tasks + import/export.

Защищён require_admin. Все endpoints под /api/admin/content.
"""
from fastapi import APIRouter, Depends

from auth import require_admin

router = APIRouter(
    prefix="/api/admin/content",
    tags=["admin-content"],
    dependencies=[Depends(require_admin)],
)


@router.get("/courses")
async def list_courses_admin():
    return []
