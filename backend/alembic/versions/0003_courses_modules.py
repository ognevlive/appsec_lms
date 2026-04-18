"""restructure tracks into courses/modules/module_units

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create courses (clone of tracks)
    op.create_table(
        "courses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("order", sa.Integer(), server_default="0"),
        sa.Column("config", JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("slug", name="uq_courses_slug"),
    )

    # 2. Copy tracks → courses (default progression=free)
    op.execute("""
        INSERT INTO courses (id, title, slug, description, "order", config, created_at)
        SELECT
            id, title, slug, description, "order",
            CASE
                WHEN config ? 'progression' THEN config
                ELSE config || '{"progression": "free"}'::jsonb
            END,
            created_at
        FROM tracks
    """)
    # Reset sequence so new inserts don't collide
    op.execute("SELECT setval('courses_id_seq', COALESCE((SELECT MAX(id) FROM courses), 1))")

    # 3. Create modules
    op.create_table(
        "modules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("estimated_hours", sa.Integer(), nullable=True),
        sa.Column("learning_outcomes", JSONB(), server_default=sa.text("'[]'::jsonb")),
        sa.Column("config", JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("course_id", "order", name="uq_modules_course_order"),
    )
    op.create_index("ix_modules_course_id", "modules", ["course_id"])

    # 4. Create module_units
    op.create_table(
        "module_units",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("module_id", sa.Integer(), sa.ForeignKey("modules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("unit_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_required", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.UniqueConstraint("module_id", "task_id", name="uq_module_units_module_task"),
    )
    op.create_index("ix_module_units_module_id", "module_units", ["module_id"])

    # 5. Seed one "Основы" module per course and move track_steps in
    op.execute("""
        INSERT INTO modules (course_id, title, description, "order", estimated_hours, learning_outcomes, config)
        SELECT id, 'Основы', '', 1, NULL, '[]'::jsonb, '{}'::jsonb FROM courses
    """)

    op.execute("""
        INSERT INTO module_units (module_id, task_id, unit_order, is_required)
        SELECT m.id, ts.task_id, ts.step_order, TRUE
        FROM track_steps ts
        JOIN modules m ON m.course_id = ts.track_id AND m.title = 'Основы' AND m."order" = 1
    """)

    # 6. Drop old tables
    op.drop_table("track_steps")
    op.drop_table("tracks")


def downgrade() -> None:
    # Restore tracks/track_steps from courses/module_units
    op.create_table(
        "tracks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("order", sa.Integer(), server_default="0"),
        sa.Column("config", JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("slug", name="uq_tracks_slug"),
    )
    op.create_table(
        "track_steps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("track_id", sa.Integer(), sa.ForeignKey("tracks.id"), nullable=False),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("step_order", sa.Integer(), server_default="0"),
    )

    op.execute("""
        INSERT INTO tracks (id, title, slug, description, "order", config, created_at)
        SELECT id, title, slug, description, "order", config, created_at FROM courses
    """)
    op.execute("SELECT setval('tracks_id_seq', COALESCE((SELECT MAX(id) FROM tracks), 1))")

    op.execute("""
        INSERT INTO track_steps (track_id, task_id, step_order)
        SELECT m.course_id, mu.task_id, mu.unit_order
        FROM module_units mu
        JOIN modules m ON m.id = mu.module_id
    """)

    op.drop_index("ix_module_units_module_id", table_name="module_units")
    op.drop_table("module_units")
    op.drop_index("ix_modules_course_id", table_name="modules")
    op.drop_table("modules")
    op.drop_table("courses")
