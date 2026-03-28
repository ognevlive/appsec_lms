import logging
import os
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text

from auth import hash_password
from config import settings
from database import engine, async_session
from models import Base, User, UserRole
from routers import admin, auth_router, ctf, gitlab_tasks, progress, quiz, tasks, tracks
from routers.gitlab_tasks import init_gitlab_client
from services.scheduler import cleanup_expired_containers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def create_default_admin():
    """Create default admin user if none exists."""
    async with async_session() as db:
        result = await db.execute(select(User).where(User.role == UserRole.admin))
        if not result.scalar_one_or_none():
            admin_user = User(
                username="admin",
                password_hash=hash_password("admin"),
                full_name="Administrator",
                role=UserRole.admin,
            )
            db.add(admin_user)
            await db.commit()
            logger.info("Default admin user created (admin/admin)")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables first, then apply migrations
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with engine.begin() as conn:
        await conn.execute(text("ALTER TYPE tasktype ADD VALUE IF NOT EXISTS 'theory'"))
    async with engine.begin() as conn:
        await conn.execute(text("ALTER TYPE tasktype ADD VALUE IF NOT EXISTS 'ssh_lab'"))
    await create_default_admin()

    # Init GitLab client if configured
    gitlab_url = os.getenv("GITLAB_URL")
    gitlab_token = os.getenv("GITLAB_ADMIN_TOKEN")
    if gitlab_url and gitlab_token:
        init_gitlab_client(gitlab_url, gitlab_token)
        logger.info(f"GitLab client initialized: {gitlab_url}")

    # Start scheduler for container cleanup
    scheduler.add_job(cleanup_expired_containers, "interval", minutes=1)
    scheduler.start()
    logger.info("Scheduler started")

    yield

    # Shutdown
    scheduler.shutdown()


app = FastAPI(title="LMS AppSec", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(tasks.router)
app.include_router(quiz.router)
app.include_router(ctf.router)
app.include_router(gitlab_tasks.router)
app.include_router(progress.router)
app.include_router(admin.router)
app.include_router(tracks.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
