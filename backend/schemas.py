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


class TheoryRef(BaseModel):
    id: int
    title: str


class TaskDetail(TaskOut):
    config: dict
    theory_refs: list[TheoryRef] = []


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


# --- Course / Module / Unit ---
class UnitOut(BaseModel):
    id: int
    task_id: int
    task_slug: str
    task_title: str
    task_type: TaskType
    task_difficulty: str | None = None
    content_kind: str | None = None
    unit_order: int
    is_required: bool
    user_status: str | None = None

    class Config:
        from_attributes = True


class ModuleOut(BaseModel):
    id: int
    title: str
    description: str
    order: int
    estimated_hours: int | None
    learning_outcomes: list[str]
    config: dict
    is_locked: bool
    unit_count: int
    completed_unit_count: int
    pending_unit_count: int = 0
    units: list[UnitOut]

    class Config:
        from_attributes = True


class CourseOut(BaseModel):
    id: int
    slug: str
    title: str
    description: str
    order: int
    config: dict
    module_count: int
    unit_count: int
    completed_unit_count: int
    pending_unit_count: int = 0
    progress_pct: int


class CourseDetail(CourseOut):
    modules: list[ModuleOut]


# --- GitLab ---
class GitLabTaskInfo(BaseModel):
    repo_url: str
    username: str
    password: str


# --- Submissions (generic, with files) ---
class SubmissionFileOut(BaseModel):
    id: int
    filename: str
    size_bytes: int
    content_type: str | None = None

    class Config:
        from_attributes = True


class SubmissionDetail(BaseModel):
    id: int
    user_id: int
    task_id: int
    status: SubmissionStatus
    details: dict
    submitted_at: datetime
    reviewer_id: int | None = None
    reviewed_at: datetime | None = None
    review_comment: str | None = None
    files: list[SubmissionFileOut] = []

    class Config:
        from_attributes = True


# --- Admin review ---
class ReviewQueueItem(BaseModel):
    submission_id: int
    task_id: int
    task_title: str
    user_id: int
    username: str
    user_full_name: str
    submitted_at: datetime
    course_id: int | None = None
    course_title: str | None = None


class ReviewQueueResponse(BaseModel):
    items: list[ReviewQueueItem]
    total: int
    page: int
    per_page: int


class ReviewVerdict(BaseModel):
    status: SubmissionStatus  # success | fail
    comment: str = ""
