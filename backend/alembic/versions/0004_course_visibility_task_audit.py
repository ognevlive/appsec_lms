"""add course visibility and task audit fields

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-18 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "courses",
        sa.Column("is_visible", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    # Все существующие курсы делаем видимыми (уже в проде — не ломаем)
    op.execute("UPDATE courses SET is_visible = TRUE")

    op.add_column(
        "tasks",
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
    )
    op.add_column(
        "tasks",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("tasks", "updated_at")
    op.drop_column("tasks", "author_id")
    op.drop_column("courses", "is_visible")
