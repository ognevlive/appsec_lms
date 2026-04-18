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


_CYRILLIC_MAP = str.maketrans({
    'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'e','ж':'zh','з':'z',
    'и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r',
    'с':'s','т':'t','у':'u','ф':'f','х':'h','ц':'c','ч':'ch','ш':'sh','щ':'sch',
    'ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya',
    'А':'A','Б':'B','В':'V','Г':'G','Д':'D','Е':'E','Ё':'E','Ж':'Zh','З':'Z',
    'И':'I','Й':'Y','К':'K','Л':'L','М':'M','Н':'N','О':'O','П':'P','Р':'R',
    'С':'S','Т':'T','У':'U','Ф':'F','Х':'H','Ц':'C','Ч':'Ch','Ш':'Sh','Щ':'Sch',
    'Ъ':'','Ы':'Y','Ь':'','Э':'E','Ю':'Yu','Я':'Ya',
})


def _slugify(text: str) -> str:
    """Minimal slugify: transliterate Cyrillic, lowercase, strip accents, replace non-alnum with hyphens."""
    text = text.translate(_CYRILLIC_MAP)
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
