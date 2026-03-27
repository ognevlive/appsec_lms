from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models import Task, TaskSubmission, SubmissionStatus, User, UserRole

router = APIRouter(prefix="/api/me", tags=["progress"], dependencies=[Depends(get_current_user)])


@router.get("/progress")
async def get_progress(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Total tasks
    total_result = await db.execute(select(func.count(Task.id)))
    total_tasks = total_result.scalar() or 0

    # Completed tasks (distinct tasks with at least one success)
    completed_result = await db.execute(
        select(func.count(func.distinct(TaskSubmission.task_id)))
        .where(
            TaskSubmission.user_id == user.id,
            TaskSubmission.status == SubmissionStatus.success,
        )
    )
    completed_tasks = completed_result.scalar() or 0

    # Progress percentage
    progress_pct = round(completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

    # Total XP - sum of max_points from completed tasks' configs
    completed_task_ids_query = (
        select(func.distinct(TaskSubmission.task_id))
        .where(
            TaskSubmission.user_id == user.id,
            TaskSubmission.status == SubmissionStatus.success,
        )
    )
    completed_tasks_result = await db.execute(
        select(Task).where(Task.id.in_(completed_task_ids_query))
    )
    completed_task_objects = completed_tasks_result.scalars().all()
    total_xp = sum(
        (t.config or {}).get("max_points", 100) for t in completed_task_objects
    )

    # Ranking - count users with more XP
    # Get all students
    students_result = await db.execute(
        select(User.id).where(User.role == UserRole.student)
    )
    student_ids = [row[0] for row in students_result.all()]
    total_users = len(student_ids)

    # Calculate XP for each student to determine rank
    rank = 1
    for sid in student_ids:
        if sid == user.id:
            continue
        sid_completed = await db.execute(
            select(func.distinct(TaskSubmission.task_id))
            .where(
                TaskSubmission.user_id == sid,
                TaskSubmission.status == SubmissionStatus.success,
            )
        )
        sid_task_ids = [row[0] for row in sid_completed.all()]
        if sid_task_ids:
            sid_tasks = await db.execute(
                select(Task).where(Task.id.in_(sid_task_ids))
            )
            sid_xp = sum(
                (t.config or {}).get("max_points", 100) for t in sid_tasks.scalars().all()
            )
            if sid_xp > total_xp:
                rank += 1

    # Specializations - group completed tasks by tags
    specializations: dict[str, dict] = {}
    all_tasks_result = await db.execute(select(Task))
    all_tasks = all_tasks_result.scalars().all()
    completed_ids_set = {t.id for t in completed_task_objects}

    for t in all_tasks:
        tags = (t.config or {}).get("tags", [])
        for tag in tags:
            if tag not in specializations:
                specializations[tag] = {"total": 0, "completed": 0}
            specializations[tag]["total"] += 1
            if t.id in completed_ids_set:
                specializations[tag]["completed"] += 1

    spec_list = [
        {
            "name": name,
            "pct": round(data["completed"] / data["total"] * 100) if data["total"] > 0 else 0,
        }
        for name, data in specializations.items()
    ]
    spec_list.sort(key=lambda x: x["pct"], reverse=True)

    # Activity log - recent submissions
    activity_result = await db.execute(
        select(TaskSubmission, Task.title)
        .join(Task, TaskSubmission.task_id == Task.id)
        .where(TaskSubmission.user_id == user.id)
        .order_by(TaskSubmission.submitted_at.desc())
        .limit(20)
    )
    activity_log = []
    for sub, task_title in activity_result.all():
        points = 0
        if sub.status == SubmissionStatus.success:
            task_obj = next((t for t in all_tasks if t.id == sub.task_id), None)
            if task_obj:
                points = (task_obj.config or {}).get("max_points", 100)
        activity_log.append({
            "date": sub.submitted_at.isoformat() if sub.submitted_at else "",
            "task_title": task_title,
            "points": points,
            "status": sub.status.value,
        })

    return {
        "completed_tasks": completed_tasks,
        "total_tasks": total_tasks,
        "progress_pct": progress_pct,
        "total_xp": total_xp,
        "rank": rank,
        "total_users": total_users,
        "specializations": spec_list,
        "activity_log": activity_log,
    }
