"""initial poetry schema

Revision ID: 20260912_0001
Revises:
Create Date: 2026-09-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260912_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


poem_genre = postgresql.ENUM(
    "古体诗", "绝句", "律诗", "词", "曲", "乐府", "其他",
    name="poem_genre", create_type=False
)
verification_status = postgresql.ENUM(
    "pending", "verified", "rejected", name="verification_status", create_type=False
)
tag_dimension = postgresql.ENUM(
    "subject", "season", "time", "weather", "mood", "theme", "atmosphere",
    name="tag_dimension", create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    poem_genre.create(bind, checkfirst=True)
    verification_status.create(bind, checkfirst=True)
    tag_dimension.create(bind, checkfirst=True)

    op.create_table(
        "authors",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("normalized_name", sa.String(50), nullable=False),
        sa.Column("dynasty", sa.String(20), nullable=False),
        sa.Column("aliases", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
        sa.UniqueConstraint("dynasty", "normalized_name", name="uq_authors_dynasty_name"),
    )
    op.create_table(
        "tags",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("dimension", tag_dimension, nullable=False),
        sa.Column("name", sa.String(40), nullable=False),
        sa.Column("normalized_name", sa.String(40), nullable=False),
        sa.Column("description", sa.String(200)),
        sa.Column("enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dimension", "normalized_name", name="uq_tags_dimension_name"),
    )
    op.create_table(
        "poems",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(160), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("normalized_title", sa.String(120), nullable=False),
        sa.Column("author_id", sa.BigInteger(), nullable=False),
        sa.Column("dynasty", sa.String(20), nullable=False),
        sa.Column("genre", poem_genre, nullable=False),
        sa.Column("tune", sa.String(120)),
        sa.Column("canonical_text", sa.Text(), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("aliases", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("popularity", sa.Numeric(4, 3), server_default="0.500", nullable=False),
        sa.Column("verification_status", verification_status, server_default="pending", nullable=False),
        sa.Column("source_name", sa.String(200)),
        sa.Column("source_url", sa.Text()),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("schema_version", sa.SmallInteger(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("popularity >= 0 AND popularity <= 1", name="ck_poems_popularity_range"),
        sa.ForeignKeyConstraint(["author_id"], ["authors.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("idx_poems_verified", "poems", ["verification_status", "dynasty", "genre"])
    op.create_index("idx_poems_author", "poems", ["author_id"])

    op.create_table(
        "poem_lines",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("poem_id", sa.BigInteger(), nullable=False),
        sa.Column("line_no", sa.SmallInteger(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("is_featured", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.ForeignKeyConstraint(["poem_id"], ["poems.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("poem_id", "line_no", name="uq_poem_lines_poem_line"),
    )
    op.create_index("idx_poem_lines_poem", "poem_lines", ["poem_id", "line_no"])

    op.create_table(
        "tag_aliases",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tag_id", sa.BigInteger(), nullable=False),
        sa.Column("alias", sa.String(40), nullable=False),
        sa.Column("normalized_alias", sa.String(40), nullable=False),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("normalized_alias"),
    )
    op.create_table(
        "poem_tags",
        sa.Column("poem_id", sa.BigInteger(), nullable=False),
        sa.Column("tag_id", sa.BigInteger(), nullable=False),
        sa.Column("weight", sa.Numeric(4, 3), nullable=False),
        sa.Column("evidence_lines", postgresql.ARRAY(sa.SmallInteger()), server_default="{}", nullable=False),
        sa.Column("source", sa.String(20), server_default="manual", nullable=False),
        sa.Column("reviewed", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.CheckConstraint("weight > 0 AND weight <= 1", name="ck_poem_tags_weight_range"),
        sa.CheckConstraint("source IN ('manual', 'rule', 'model')", name="ck_poem_tags_source_value"),
        sa.ForeignKeyConstraint(["poem_id"], ["poems.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("poem_id", "tag_id"),
    )
    op.create_index("idx_poem_tags_lookup", "poem_tags", ["tag_id", "weight", "poem_id"])


def downgrade() -> None:
    op.drop_index("idx_poem_tags_lookup", table_name="poem_tags")
    op.drop_table("poem_tags")
    op.drop_table("tag_aliases")
    op.drop_index("idx_poem_lines_poem", table_name="poem_lines")
    op.drop_table("poem_lines")
    op.drop_index("idx_poems_author", table_name="poems")
    op.drop_index("idx_poems_verified", table_name="poems")
    op.drop_table("poems")
    op.drop_table("tags")
    op.drop_table("authors")

    bind = op.get_bind()
    tag_dimension.drop(bind, checkfirst=True)
    verification_status.drop(bind, checkfirst=True)
    poem_genre.drop(bind, checkfirst=True)
