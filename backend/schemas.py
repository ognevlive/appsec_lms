from datetime import datetime

from pydantic import BaseModel

from models import ContainerStatus, SubmissionStatus, TaskType, UserRole


# --- Auth ---
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- User ---
class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str = ""
    role: UserRole = UserRole.student


class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    role: UserRole
    created_at: datetime

    class Config:
        from_attributes = True


# --- Task ---
class TaskOut(BaseModel):
    id: int
    title: str
    description: str
    type: TaskType
    order: int

    class Config:
        from_attributes = True


class TaskDetail(TaskOut):
    config: dict


class TaskCatalogOut(TaskOut):
    difficulty: str | None = None
    tags: list[str] = []
    max_points: int | None = None


# --- Paginated ---
class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    per_page: int


# --- Quiz ---
class QuizQuestion(BaseModel):
    id: int
    text: str
    options: list[str]


class QuizSubmit(BaseModel):
    answers: dict[str, str]  # question_id -> answer


class QuizResult(BaseModel):
    score: int
    total: int
    correct: list[int]
    wrong: list[int]


# --- CTF ---
class ContainerInfo(BaseModel):
    container_id: str
    domain: str
    expires_at: datetime
    status: ContainerStatus


class FlagSubmit(BaseModel):
    flag: str


# --- Container Check ---
class CheckResultItem(BaseModel):
    name: str
    passed: bool
    message: str = ""


class CheckResponse(BaseModel):
    all_passed: bool
    results: list[CheckResultItem]


# --- Submission ---
class SubmissionOut(BaseModel):
    id: int
    user_id: int
    task_id: int
    status: SubmissionStatus
    details: dict
    submitted_at: datetime

    class Config:
        from_attributes = True


# --- Track ---
class TrackStepOut(BaseModel):
    id: int
    task_id: int
    step_order: int
    task_title: str
    task_type: TaskType
    task_difficulty: str | None
    user_status: str | None

    class Config:
        from_attributes = True


class TrackOut(BaseModel):
    id: int
    title: str
    slug: str
    description: str
    order: int
    config: dict
    step_count: int
    completed_count: int


class TrackDetail(TrackOut):
    steps: list[TrackStepOut]


# --- GitLab ---
class GitLabTaskInfo(BaseModel):
    repo_url: str
    username: str
    password: str
