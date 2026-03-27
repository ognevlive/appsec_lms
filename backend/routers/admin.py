from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from auth import hash_password, require_admin
from database import get_db
from models import ContainerInstance, ContainerStatus, Task, TaskSubmission, User
from schemas import SubmissionOut, UserCreate, UserOut

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(body: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.username == body.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")

    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/users")
async def list_users(
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession = Depends(get_db),
):
    count_query = select(func.count(User.id))
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = (
        select(User)
        .order_by(User.id)
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(query)
    items = result.scalars().all()

    return {
        "items": [UserOut.model_validate(u) for u in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.delete(user)
    await db.commit()


@router.get("/submissions")
async def list_submissions(
    task_id: int | None = None,
    user_id: int | None = None,
    status: str | None = None,
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession = Depends(get_db),
):
    query = select(TaskSubmission).order_by(TaskSubmission.submitted_at.desc())
    count_query = select(func.count(TaskSubmission.id))

    if task_id:
        query = query.where(TaskSubmission.task_id == task_id)
        count_query = count_query.where(TaskSubmission.task_id == task_id)
    if user_id:
        query = query.where(TaskSubmission.user_id == user_id)
        count_query = count_query.where(TaskSubmission.user_id == user_id)
    if status:
        query = query.where(TaskSubmission.status == status)
        count_query = count_query.where(TaskSubmission.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    items = result.scalars().all()

    return {
        "items": [SubmissionOut.model_validate(s) for s in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/containers")
async def list_active_containers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ContainerInstance)
        .where(ContainerInstance.status == ContainerStatus.running)
        .order_by(ContainerInstance.started_at.desc())
    )
    containers = result.scalars().all()
    return [
        {
            "id": c.id,
            "user_id": c.user_id,
            "task_id": c.task_id,
            "domain": c.domain,
            "started_at": c.started_at,
            "expires_at": c.expires_at,
        }
        for c in containers
    ]
