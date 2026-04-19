"""add manual review and file uploads

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-19 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "task_submissions",
        sa.Column("reviewer_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
    )
    op.add_column(
        "task_submissions",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "task_submissions",
        sa.Column("review_comment", sa.Text(), nullable=True),
    )

    op.create_table(
        "submission_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "submission_id",
            sa.Integer(),
            sa.ForeignKey("task_submissions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("stored_path", sa.String(length=500), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_submission_files_submission_id", "submission_files", ["submission_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_submission_files_submission_id", table_name="submission_files")
    op.drop_table("submission_files")
    op.drop_column("task_submissions", "review_comment")
    op.drop_column("task_submissions", "reviewed_at")
    op.drop_column("task_submissions", "reviewer_id")
