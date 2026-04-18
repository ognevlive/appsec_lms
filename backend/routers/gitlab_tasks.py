from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from config import settings
from database import get_db
from models import SubmissionStatus, Task, TaskSubmission, TaskType, User
from schemas import GitLabTaskInfo
from services.gitlab_client import GitLabClient
from services.unlock_guard import require_unit_unlocked

router = APIRouter(prefix="/api/gitlab", tags=["gitlab"])

# Will be initialized on startup with actual GitLab URL and token
_gitlab_client: GitLabClient | None = None


def get_gitlab_client() -> GitLabClient:
    if not _gitlab_client:
        raise HTTPException(status_code=503, detail="GitLab integration not configured")
    return _gitlab_client


def init_gitlab_client(base_url: str, admin_token: str):
    global _gitlab_client
    _gitlab_client = GitLabClient(base_url, admin_token)


@router.post("/{task_id}/start", response_model=GitLabTaskInfo, dependencies=[Depends(require_unit_unlocked)])
async def start_gitlab_task(
    task_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_gitlab_task(task_id, db)
    gitlab = get_gitlab_client()

    template_project_id = task.config.get("template_project_id")
    if not template_project_id:
        raise HTTPException(status_code=500, detail="Task has no template_project_id")

    # Create/get GitLab user
    gl_username = f"student-{user.username}"
    gl_user = await gitlab.ensure_user(gl_username)

    # Fork template repo
    fork_info = await gitlab.fork_project(template_project_id, gl_user)

    # Save submission as pending (until student pushes and pipeline passes)
    existing = await db.execute(
        select(TaskSubmission).where(
            TaskSubmission.user_id == user.id,
            TaskSubmission.task_id == task_id,
            TaskSubmission.status == SubmissionStatus.pending,
        )
    )
    if not existing.scalar_one_or_none():
        submission = TaskSubmission(
            user_id=user.id,
            task_id=task_id,
            status=SubmissionStatus.pending,
            details={"repo_url": fork_info.repo_url, "gitlab_username": gl_username},
        )
        db.add(submission)
        await db.commit()

    return GitLabTaskInfo(
        repo_url=fork_info.repo_url,
        username=fork_info.username,
        password=fork_info.password,
    )


async def _get_gitlab_task(task_id: int, db: AsyncSession) -> Task:
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task or task.type != TaskType.gitlab:
        raise HTTPException(status_code=404, detail="GitLab task not found")
    return task
