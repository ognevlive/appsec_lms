import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
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

    submissions = relationship("TaskSubmission", back_populates="user")
    containers = relationship("ContainerInstance", back_populates="user")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    type = Column(Enum(TaskType), nullable=False)
    config = Column(JSONB, default=dict)
    order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    submissions = relationship("TaskSubmission", back_populates="task")


class TaskSubmission(Base):
    __tablename__ = "task_submissions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    status = Column(Enum(SubmissionStatus), default=SubmissionStatus.pending)
    details = Column(JSONB, default=dict)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="submissions")
    task = relationship("Task", back_populates="submissions")


class Track(Base):
    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    description = Column(Text, default="")
    order = Column(Integer, default=0)
    config = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    steps = relationship("TrackStep", back_populates="track", order_by="TrackStep.step_order")


class TrackStep(Base):
    __tablename__ = "track_steps"

    id = Column(Integer, primary_key=True)
    track_id = Column(Integer, ForeignKey("tracks.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    step_order = Column(Integer, default=0)

    track = relationship("Track", back_populates="steps")
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
