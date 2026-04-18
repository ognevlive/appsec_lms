"""add task.slug column with backfill

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-18 00:00:00.000000

"""
import re
import unicodedata
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels = None
depends_on = None


def _slugify(text: str) -> str:
    """Minimal slugify: lowercase, strip accents, replace non-alnum with hyphens."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text[:150] or "task"


def upgrade() -> None:
    op.add_column("tasks", sa.Column("slug", sa.String(length=150), nullable=True))
    op.create_index("ix_tasks_slug", "tasks", ["slug"], unique=True)

    # Backfill: generate slug from title, ensure uniqueness by appending numeric suffix
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, title FROM tasks ORDER BY id")).fetchall()
    used: set[str] = set()
    for row in rows:
        base = _slugify(row.title)
        slug = base
        i = 2
        while slug in used:
            slug = f"{base}-{i}"
            i += 1
        used.add(slug)
        conn.execute(
            sa.text("UPDATE tasks SET slug = :slug WHERE id = :id"),
            {"slug": slug, "id": row.id},
        )


def downgrade() -> None:
    op.drop_index("ix_tasks_slug", table_name="tasks")
    op.drop_column("tasks", "slug")
