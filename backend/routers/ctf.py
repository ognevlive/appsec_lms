import hashlib

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models import (
    ContainerInstance,
    ContainerStatus,
    SubmissionStatus,
    Task,
    TaskSubmission,
    TaskType,
    User,
)
from schemas import CheckResponse, CheckResultItem, ContainerInfo, FlagSubmit
from services.container_checker import run_checks
from services.docker_manager import start_container, stop_container

router = APIRouter(prefix="/api/ctf", tags=["ctf"])


@router.post("/{task_id}/start", response_model=ContainerInfo)
async def start_ctf(
    task_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_ctf_task(task_id, db)

    # Check if already running
    existing = await db.execute(
        select(ContainerInstance).where(
            ContainerInstance.user_id == user.id,
            ContainerInstance.task_id == task_id,
            ContainerInstance.status == ContainerStatus.running,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Container already running for this task")

    config = task.config
    docker_image = config.get("docker_image")
    ttl = config.get("ttl_minutes", 120)
    port = config.get("container_port", 80)

    if not docker_image:
        raise HTTPException(status_code=500, detail="Task has no docker_image configured")

    try:
        result = start_container(
            user_id=user.id,
            task_id=task_id,
            docker_image=docker_image,
            ttl_minutes=ttl,
            container_port=port,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start container: {e}")

    instance = ContainerInstance(
        user_id=user.id,
        task_id=task_id,
        container_id=result.container_id,
        domain=result.domain,
        expires_at=result.expires_at,
        status=ContainerStatus.running,
    )
    db.add(instance)
    await db.commit()
    await db.refresh(instance)

    return ContainerInfo(
        container_id=instance.container_id,
        domain=instance.domain,
        expires_at=instance.expires_at,
        status=instance.status,
    )


@router.post("/{task_id}/stop")
async def stop_ctf(
    task_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    instance = await _get_running_instance(user.id, task_id, db)
    stop_container(instance.container_id)
    instance.status = ContainerStatus.stopped
    await db.commit()
    return {"status": "stopped"}


@router.get("/{task_id}/status", response_model=ContainerInfo | None)
async def ctf_status(
    task_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ContainerInstance).where(
            ContainerInstance.user_id == user.id,
            ContainerInstance.task_id == task_id,
            ContainerInstance.status == ContainerStatus.running,
        )
    )
    instance = result.scalar_one_or_none()
    if not instance:
        return None
    return ContainerInfo(
        container_id=instance.container_id,
        domain=instance.domain,
        expires_at=instance.expires_at,
        status=instance.status,
    )


@router.post("/{task_id}/flag")
async def submit_flag(
    task_id: int,
    body: FlagSubmit,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_ctf_task(task_id, db)
    flag_hash = task.config.get("flag_hash")
    if not flag_hash:
        raise HTTPException(status_code=400, detail="This task does not use flag submission")

    submitted_hash = hashlib.sha256(body.flag.strip().encode()).hexdigest()
    passed = submitted_hash == flag_hash

    submission = TaskSubmission(
        user_id=user.id,
        task_id=task_id,
        status=SubmissionStatus.success if passed else SubmissionStatus.fail,
        details={"method": "flag"},
    )
    db.add(submission)
    await db.commit()

    if not passed:
        raise HTTPException(status_code=400, detail="Incorrect flag")
    return {"status": "correct"}


@router.post("/{task_id}/check", response_model=CheckResponse)
async def check_container(
    task_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_ctf_task(task_id, db)
    checks = task.config.get("checks", [])
    if not checks:
        raise HTTPException(status_code=400, detail="This task has no automated checks")

    instance = await _get_running_instance(user.id, task_id, db)

    results = run_checks(instance.container_id, checks)
    all_passed = all(r.passed for r in results)

    submission = TaskSubmission(
        user_id=user.id,
        task_id=task_id,
        status=SubmissionStatus.success if all_passed else SubmissionStatus.fail,
        details={
            "method": "check",
            "results": [{"name": r.name, "passed": r.passed, "message": r.message} for r in results],
        },
    )
    db.add(submission)
    await db.commit()

    return CheckResponse(
        all_passed=all_passed,
        results=[CheckResultItem(name=r.name, passed=r.passed, message=r.message) for r in results],
    )


async def _get_ctf_task(task_id: int, db: AsyncSession) -> Task:
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task or task.type != TaskType.ctf:
        raise HTTPException(status_code=404, detail="CTF task not found")
    return task


async def _get_running_instance(user_id: int, task_id: int, db: AsyncSession) -> ContainerInstance:
    result = await db.execute(
        select(ContainerInstance).where(
            ContainerInstance.user_id == user_id,
            ContainerInstance.task_id == task_id,
            ContainerInstance.status == ContainerStatus.running,
        )
    )
    instance = result.scalar_one_or_none()
    if not instance:
        raise HTTPException(status_code=404, detail="No running container for this task")
    return instance
