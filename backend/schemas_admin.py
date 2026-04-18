"""Pydantic-схемы для /api/admin/content.

Type-specific конфиги (theory/quiz/ctf/ssh_lab/gitlab) валидируются дискриминированным
союзом через поле `type` на уровне TaskCreate/TaskUpdate.
"""
from datetime import datetime
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from models import TaskType

SLUG_RE = r"^[a-z0-9-]{2,100}$"


# --- Task configs per type ---

class TheoryVideo(BaseModel):
    provider: Literal["youtube", "url"]
    src: str


class TheoryConfig(BaseModel):
    content_kind: Literal["text", "video", "mixed"] = "text"
    tags: list[str] = Field(default_factory=list)
    content: str = ""
    video: TheoryVideo | None = None


class QuizChoice(BaseModel):
    text: str
    correct: bool = False


class QuizQuestion(BaseModel):
    id: int | None = None
    text: str
    options: list[QuizChoice]


class QuizConfig(BaseModel):
    questions: list[QuizQuestion] = Field(default_factory=list)
    pass_threshold: int = 70
    shuffle: bool = False


# SECURITY CONTRACT for CtfConfig / SshLabConfig:
#   `flag` is plaintext and WRITE-ONLY. The admin router MUST:
#     1. Read `flag` from the incoming payload.
#     2. Compute SHA-256, store the digest in `flag_hash` on Task.config.
#     3. STRIP `flag` from Task.config BEFORE persisting (otherwise it leaks
#        via TaskOutAdmin.config, which is `dict` — no schema-level guard).
#   Any code path that persists Task.config must use services/flag_hash.py.


class CtfConfig(BaseModel):
    docker_image: str
    port: int = 5000
    ttl_minutes: int = 120
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    flag_hash: str = ""
    flag: str | None = None  # write-only, stripped before persistence — see SECURITY CONTRACT above


class SshLabConfig(BaseModel):
    docker_image: str
    terminal_port: int = 80
    ttl_minutes: int = 120
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    instructions: str = ""
    flag_hash: str = ""
    flag: str | None = None  # write-only, stripped before persistence — see SECURITY CONTRACT above


class GitlabConfig(BaseModel):
    # Пропускаем все поля существующей gitlab-конфигурации как есть
    model_config = ConfigDict(extra="allow")


# --- Task create/update ---

class TaskBase(BaseModel):
    slug: str = Field(pattern=SLUG_RE)
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    order: int = 0


class TaskCreate(TaskBase):
    type: TaskType
    config: dict = Field(default_factory=dict)


class TaskUpdate(BaseModel):
    slug: str | None = Field(default=None, pattern=SLUG_RE)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    order: int | None = None
    config: dict | None = None


class TaskUsage(BaseModel):
    course_id: int
    course_slug: str
    module_id: int
    unit_id: int


class TaskOutAdmin(TaskBase):
    id: int
    type: TaskType
    config: dict
    author_id: int | None
    updated_at: datetime
    usage: list[TaskUsage] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# --- Course/Module/Unit ---

class CourseCreate(BaseModel):
    slug: str = Field(pattern=SLUG_RE)
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    order: int = 0
    config: dict = Field(default_factory=dict)


class CourseUpdate(BaseModel):
    slug: str | None = Field(default=None, pattern=SLUG_RE)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    order: int | None = None
    config: dict | None = None
    is_visible: bool | None = None


class ModuleCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    order: int = 0
    estimated_hours: int | None = None
    learning_outcomes: list[str] = Field(default_factory=list)
    config: dict = Field(default_factory=dict)


class ModuleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    order: int | None = None
    estimated_hours: int | None = None
    learning_outcomes: list[str] | None = None
    config: dict | None = None


class UnitCreate(BaseModel):
    task_id: int
    unit_order: int = 0
    is_required: bool = True


class UnitUpdate(BaseModel):
    unit_order: int | None = None
    is_required: bool | None = None


class ReorderItem(BaseModel):
    id: int
    order: int
