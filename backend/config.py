from pydantic_settings import BaseSettings


DEFAULT_ALLOWED_EXT = [
    "pdf", "png", "jpg", "jpeg", "zip", "txt", "md", "docx", "py", "js", "ts",
]


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://lms:lms@postgres:5432/lms"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    domain: str = "lab.local"
    traefik_network: str = "lms_network"
    tasks_dir: str = "/tasks"
    container_check_timeout: int = 5
    uploads_dir: str = "/app/uploads"
    uploads_max_size_mb: int = 20
    uploads_allowed_ext_default: list[str] = DEFAULT_ALLOWED_EXT

    class Config:
        env_file = ".env"


settings = Settings()
