import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class UserRole(str, enum.Enum):
    student = "student"
    admin = "admin"


class TaskType(str, enum.Enum):
    quiz = "quiz"
    ctf = "ctf"
    gitlab = "gitlab"
    theory = "theory"
    ssh_lab = "ssh_lab"


class SubmissionStatus(str, enum.Enum):
    pending = "pending"
    success = "success"
    fail = "fail"


class ContainerStatus(str, enum.Enum):
    running = "running"
    stopped = "stopped"
    expired = "expired"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), default="")
    role = Column(Enum(UserRole), default=UserRole.student, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    submissions = relationship(
        "TaskSubmission",
        back_populates="user",
        foreign_keys="TaskSubmission.user_id",
    )
    containers = relationship("ContainerInstance", back_populates="user")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    slug = Column(String(150), unique=True, nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    type = Column(Enum(TaskType), nullable=False)
    config = Column(JSONB, default=dict)
    order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    author_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    submissions = relationship("TaskSubmission", back_populates="task")


class TaskSubmission(Base):
    __tablename__ = "task_submissions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    status = Column(Enum(SubmissionStatus), default=SubmissionStatus.pending)
    details = Column(JSONB, default=dict)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_comment = Column(Text, nullable=True)

    user = relationship("User", back_populates="submissions", foreign_keys=[user_id])
    task = relationship("Task", back_populates="submissions")
    reviewer = relationship("User", foreign_keys=[reviewer_id])
    files = relationship(
        "SubmissionFile",
        back_populates="submission",
        cascade="all, delete-orphan",
    )


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    description = Column(Text, default="")
    order = Column(Integer, default=0)
    config = Column(JSONB, default=dict)
    is_visible = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    modules = relationship(
        "Module",
        back_populates="course",
        order_by="Module.order",
        cascade="all, delete-orphan",
    )


class Module(Base):
    __tablename__ = "modules"

    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    order = Column(Integer, default=0, nullable=False)
    estimated_hours = Column(Integer, nullable=True)
    learning_outcomes = Column(JSONB, default=list)
    config = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("course_id", "order", name="uq_modules_course_order"),)

    course = relationship("Course", back_populates="modules")
    units = relationship(
        "ModuleUnit",
        back_populates="module",
        order_by="ModuleUnit.unit_order",
        cascade="all, delete-orphan",
    )


class ModuleUnit(Base):
    __tablename__ = "module_units"

    id = Column(Integer, primary_key=True)
    module_id = Column(Integer, ForeignKey("modules.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    unit_order = Column(Integer, default=0, nullable=False)
    is_required = Column(Boolean, default=True, nullable=False)

    __table_args__ = (UniqueConstraint("module_id", "task_id", name="uq_module_units_module_task"),)

    module = relationship("Module", back_populates="units")
    task = relationship("Task")


class ContainerInstance(Base):
    __tablename__ = "container_instances"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    container_id = Column(String(100), nullable=False)
    domain = Column(String(255), nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(Enum(ContainerStatus), default=ContainerStatus.running)

    user = relationship("User", back_populates="containers")
    task = relationship("Task")


class SubmissionFile(Base):
    __tablename__ = "submission_files"

    id = Column(Integer, primary_key=True)
    submission_id = Column(
        Integer,
        ForeignKey("task_submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename = Column(String(255), nullable=False)
    stored_path = Column(String(500), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    content_type = Column(String(100), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    submission = relationship("TaskSubmission", back_populates="files")
