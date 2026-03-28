from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models import Track, TrackStep, TaskSubmission, TaskType, User
from schemas import TrackOut, TrackDetail, TrackStepOut

router = APIRouter(prefix="/api/tracks", tags=["tracks"], dependencies=[Depends(get_current_user)])


async def _get_user_statuses(user_id: int, db: AsyncSession) -> dict[int, str]:
    """Return best submission status per task_id for the given user."""
    result = await db.execute(
        select(TaskSubmission.task_id, TaskSubmission.status)
        .where(TaskSubmission.user_id == user_id)
        .order_by(TaskSubmission.submitted_at.desc())
    )
    statuses: dict[int, str] = {}
    for task_id, status in result.all():
        if task_id not in statuses:
            statuses[task_id] = status.value
        if status.value == "success":
            statuses[task_id] = "success"
    return statuses


@router.get("", response_model=list[TrackOut])
async def list_tracks(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Track)
        .options(selectinload(Track.steps).selectinload(TrackStep.task))
        .order_by(Track.order, Track.id)
    )
    tracks = result.scalars().all()

    statuses = await _get_user_statuses(user.id, db)

    out = []
    for track in tracks:
        step_count = sum(1 for step in track.steps if step.task.type != TaskType.theory)
        completed_count = sum(
            1 for step in track.steps
            if step.task.type != TaskType.theory and statuses.get(step.task_id) == "success"
        )
        out.append(
            TrackOut(
                id=track.id,
                title=track.title,
                slug=track.slug,
                description=track.description,
                order=track.order,
                config=track.config or {},
                step_count=step_count,
                completed_count=completed_count,
            )
        )
    return out


@router.get("/{track_id}", response_model=TrackDetail)
async def get_track(
    track_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Track)
        .options(selectinload(Track.steps).selectinload(TrackStep.task))
        .where(Track.id == track_id)
    )
    track = result.scalar_one_or_none()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    statuses = await _get_user_statuses(user.id, db)

    steps = [
        TrackStepOut(
            id=step.id,
            task_id=step.task_id,
            step_order=step.step_order,
            task_title=step.task.title,
            task_type=step.task.type,
            task_difficulty=step.task.config.get("difficulty") if step.task.config else None,
            user_status=statuses.get(step.task_id),
        )
        for step in track.steps
    ]

    step_count = sum(1 for s in steps if s.task_type != TaskType.theory)
    completed_count = sum(1 for s in steps if s.task_type != TaskType.theory and s.user_status == "success")

    return TrackDetail(
        id=track.id,
        title=track.title,
        slug=track.slug,
        description=track.description,
        order=track.order,
        config=track.config or {},
        step_count=step_count,
        completed_count=completed_count,
        steps=steps,
    )
