import logging
import secrets
import string
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass
class GitLabUserInfo:
    user_id: int
    username: str
    password: str


@dataclass
class GitLabForkInfo:
    repo_url: str
    username: str
    password: str


class GitLabClient:
    def __init__(self, base_url: str, admin_token: str):
        self.base_url = base_url.rstrip("/")
        self.headers = {"PRIVATE-TOKEN": admin_token}

    async def ensure_user(self, username: str, email: str | None = None) -> GitLabUserInfo:
        """Create a GitLab user or return existing one. Returns credentials."""
        email = email or f"{username}@lms.local"
        password = _generate_password()

        async with httpx.AsyncClient() as client:
            # Check if user exists
            resp = await client.get(
                f"{self.base_url}/api/v4/users",
                headers=self.headers,
                params={"username": username},
            )
            resp.raise_for_status()
            users = resp.json()

            if users:
                user_id = users[0]["id"]
                # Reset password
                await client.put(
                    f"{self.base_url}/api/v4/users/{user_id}",
                    headers=self.headers,
                    json={"password": password},
                )
                return GitLabUserInfo(user_id=user_id, username=username, password=password)

            # Create new user
            resp = await client.post(
                f"{self.base_url}/api/v4/users",
                headers=self.headers,
                json={
                    "username": username,
                    "name": username,
                    "email": email,
                    "password": password,
                    "skip_confirmation": True,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return GitLabUserInfo(user_id=data["id"], username=username, password=password)

    async def fork_project(
        self, template_project_id: int, gitlab_user: GitLabUserInfo
    ) -> GitLabForkInfo:
        """Fork a template project for a student."""
        async with httpx.AsyncClient() as client:
            # Fork as admin, then transfer to user
            resp = await client.post(
                f"{self.base_url}/api/v4/projects/{template_project_id}/fork",
                headers=self.headers,
                json={"namespace_id": gitlab_user.user_id},
            )

            if resp.status_code == 409:
                # Fork already exists, find it
                resp2 = await client.get(
                    f"{self.base_url}/api/v4/users/{gitlab_user.user_id}/projects",
                    headers=self.headers,
                )
                resp2.raise_for_status()
                projects = resp2.json()
                if projects:
                    repo_url = projects[0].get("http_url_to_repo", "")
                    return GitLabForkInfo(
                        repo_url=repo_url,
                        username=gitlab_user.username,
                        password=gitlab_user.password,
                    )

            resp.raise_for_status()
            data = resp.json()
            return GitLabForkInfo(
                repo_url=data.get("http_url_to_repo", ""),
                username=gitlab_user.username,
                password=gitlab_user.password,
            )

    async def get_pipeline_status(self, project_id: int) -> str | None:
        """Get latest pipeline status for a project."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/api/v4/projects/{project_id}/pipelines",
                headers=self.headers,
                params={"per_page": 1},
            )
            resp.raise_for_status()
            pipelines = resp.json()
            if pipelines:
                return pipelines[0].get("status")
            return None


def _generate_password(length: int = 16) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))
