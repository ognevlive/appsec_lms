import logging
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass

import docker
from docker.errors import NotFound as DockerNotFound

from config import settings

logger = logging.getLogger(__name__)

client = docker.from_env()


@dataclass
class ContainerResult:
    container_id: str
    domain: str
    expires_at: datetime


def start_container(
    user_id: int,
    task_id: int,
    docker_image: str,
    ttl_minutes: int = 120,
    container_port: int = 80,
) -> ContainerResult:
    name = f"lms-task{task_id}-user{user_id}"
    domain = f"{name}.{settings.domain}"

    # Remove existing container if any
    try:
        old = client.containers.get(name)
        old.remove(force=True)
    except DockerNotFound:
        pass

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)

    labels = {
        "traefik.enable": "true",
        f"traefik.http.routers.{name}.rule": f"Host(`{domain}`)",
        f"traefik.http.routers.{name}.entrypoints": "web",
        f"traefik.http.services.{name}.loadbalancer.server.port": str(container_port),
        "lms.managed": "true",
        "lms.user_id": str(user_id),
        "lms.task_id": str(task_id),
        "lms.expires_at": expires_at.isoformat(),
    }

    container = client.containers.run(
        docker_image,
        name=name,
        detach=True,
        labels=labels,
        network=settings.traefik_network,
        mem_limit="512m",
        cpu_period=100000,
        cpu_quota=50000,  # 0.5 CPU
    )

    return ContainerResult(
        container_id=container.id,
        domain=domain,
        expires_at=expires_at,
    )


def stop_container(container_id: str) -> None:
    try:
        container = client.containers.get(container_id)
        container.remove(force=True)
    except DockerNotFound:
        logger.warning(f"Container {container_id} not found for removal")


def exec_in_container(container_id: str, cmd: str, timeout: int = 5) -> tuple[int, str]:
    """Execute a command inside a container. Returns (exit_code, output)."""
    try:
        container = client.containers.get(container_id)
        result = container.exec_run(
            ["sh", "-c", cmd],
            demux=True,
        )
        stdout = result.output[0].decode() if result.output[0] else ""
        stderr = result.output[1].decode() if result.output[1] else ""
        output = stdout + stderr
        return result.exit_code, output.strip()
    except DockerNotFound:
        return -1, "Container not found"
    except Exception as e:
        return -1, str(e)


def get_managed_containers() -> list[dict]:
    """List all LMS-managed containers."""
    containers = client.containers.list(filters={"label": "lms.managed=true"})
    result = []
    for c in containers:
        result.append({
            "container_id": c.id,
            "name": c.name,
            "user_id": c.labels.get("lms.user_id"),
            "task_id": c.labels.get("lms.task_id"),
            "expires_at": c.labels.get("lms.expires_at"),
            "status": c.status,
        })
    return result
