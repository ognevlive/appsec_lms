import logging
from datetime import datetime, timezone

from sqlalchemy import select, update

from database import async_session
from models import ContainerInstance, ContainerStatus
from services.docker_manager import stop_container

logger = logging.getLogger(__name__)


async def cleanup_expired_containers():
    """Remove containers that have exceeded their TTL."""
    now = datetime.now(timezone.utc)

    async with async_session() as db:
        result = await db.execute(
            select(ContainerInstance).where(
                ContainerInstance.status == ContainerStatus.running,
                ContainerInstance.expires_at <= now,
            )
        )
        expired = result.scalars().all()

        for container in expired:
            logger.info(
                f"Removing expired container {container.container_id} "
                f"(user={container.user_id}, task={container.task_id})"
            )
            try:
                stop_container(container.container_id)
            except Exception:
                logger.exception(f"Failed to remove container {container.container_id}")

            container.status = ContainerStatus.expired

        await db.commit()

        if expired:
            logger.info(f"Cleaned up {len(expired)} expired containers")
