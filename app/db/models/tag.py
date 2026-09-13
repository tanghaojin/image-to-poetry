from decimal import Decimal

from sqlalchemy import ARRAY, BigInteger, Boolean, CheckConstraint, Enum, ForeignKey, Index, Numeric, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import TagDimension
from app.db.models.poem import enum_values


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (
        UniqueConstraint("dimension", "normalized_name", name="uq_tags_dimension_name"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    dimension: Mapped[TagDimension] = mapped_column(
        Enum(TagDimension, name="tag_dimension", values_callable=enum_values), nullable=False
    )
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str | None] = mapped_column(String(200))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    aliases: Mapped[list["TagAlias"]] = relationship(
        back_populates="tag", cascade="all, delete-orphan"
    )
    poem_tags: Mapped[list["PoemTag"]] = relationship(
        back_populates="tag", cascade="all, delete-orphan"
    )


class TagAlias(Base):
    __tablename__ = "tag_aliases"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tag_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tags.id", ondelete="CASCADE"), nullable=False
    )
    alias: Mapped[str] = mapped_column(String(40), nullable=False)
    normalized_alias: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)

    tag: Mapped[Tag] = relationship(back_populates="aliases")


class PoemTag(Base):
    __tablename__ = "poem_tags"
    __table_args__ = (
        CheckConstraint("weight > 0 AND weight <= 1", name="weight_range"),
        CheckConstraint("source IN ('manual', 'rule', 'model')", name="source_value"),
        Index("idx_poem_tags_lookup", "tag_id", "weight", "poem_id"),
    )

    poem_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("poems.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )
    weight: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    evidence_lines: Mapped[list[int]] = mapped_column(
        ARRAY(SmallInteger), default=list, nullable=False
    )
    source: Mapped[str] = mapped_column(String(20), default="manual", nullable=False)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    poem: Mapped["Poem"] = relationship(back_populates="poem_tags")  # noqa: F821
    tag: Mapped[Tag] = relationship(back_populates="poem_tags")
