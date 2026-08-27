"""add sec_chunks table backed by pgvector

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-27

Replaces the standalone Qdrant service. SEC filing chunks live next to the rest of
the data, so there is one database to provision, back up and secure. The embedding
column is nullable: with no EMBEDDING_MODEL configured the app ranks by full-text
search instead, which is why the GIN index below exists alongside the HNSW one.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import UUID

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIM = 1536


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "sec_chunks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("symbol", sa.String(length=10), nullable=False),
        sa.Column("chunk_id", sa.Integer(), nullable=False),
        sa.Column("section", sa.String(length=100), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("symbol", "chunk_id", name="uq_sec_chunk"),
    )
    op.create_index("ix_sec_chunks_symbol", "sec_chunks", ["symbol"])
    op.create_index(
        "ix_sec_chunks_embedding",
        "sec_chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.execute(
        "CREATE INDEX ix_sec_chunks_content_fts ON sec_chunks "
        "USING gin (to_tsvector('english', content))"
    )


def downgrade() -> None:
    op.drop_table("sec_chunks")
