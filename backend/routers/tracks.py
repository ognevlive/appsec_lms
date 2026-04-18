"""Legacy /api/tracks/* endpoints — temporary 308 redirects to /api/courses/*.

Delete this file + its import after one release cycle.
"""
from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models import Course

router = APIRouter(prefix="/api/tracks", tags=["tracks-legacy"])


@router.get("", include_in_schema=False)
async def list_tracks_redirect():
    return RedirectResponse(url="/api/courses", status_code=308)


@router.get("/{track_id}", include_in_schema=False)
async def get_track_redirect(
    track_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    # Resolve the same id in courses (since ids were preserved in migration 0003)
    result = await db.execute(select(Course.slug).where(Course.id == track_id))
    slug = result.scalar_one_or_none()
    if not slug:
        return RedirectResponse(url="/api/courses", status_code=308)
    return RedirectResponse(url=f"/api/courses/{slug}", status_code=308)
