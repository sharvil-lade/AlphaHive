"""add users table and agent_trace verdict columns

Revision ID: a1b2c3d4e5f6
Revises: ffa8b06e2a31
Create Date: 2026-08-25

Adds the accounts table (see app/core/deps.py for how `users.session_id` relates to
the session-partitioned data model) and the verdict columns that let the per-agent
"Analyst views" panel survive a page reload.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "ffa8b06e2a31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=True),
        sa.Column("session_id", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_session_id", "users", ["session_id"], unique=True)

    op.add_column("agent_traces", sa.Column("label", sa.String(length=80), nullable=True))
    op.add_column("agent_traces", sa.Column("rating", sa.String(length=40), nullable=True))
    op.add_column("agent_traces", sa.Column("confidence", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("agent_traces", "confidence")
    op.drop_column("agent_traces", "rating")
    op.drop_column("agent_traces", "label")
    op.drop_index("ix_users_session_id", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
