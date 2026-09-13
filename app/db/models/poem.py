from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Enum, ForeignKey, Index, Numeric, SmallInteger, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import PoemGenre, VerificationStatus


def enum_values(enum_class: type) -> list[str]:
    return [item.value for item in enum_class]


class Poem(Base):
    __tablename__ = "poems"
    __table_args__ = (
        CheckConstraint("popularity >= 0 AND popularity <= 1", name="popularity_range"),
        Index("idx_poems_verified", "verification_status", "dynasty", "genre"),
        Index("idx_poems_author", "author_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    slug: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    normalized_title: Mapped[str] = mapped_column(String(120), nullable=False)
    author_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("authors.id"), nullable=False)
    dynasty: Mapped[str] = mapped_column(String(20), nullable=False)
    genre: Mapped[PoemGenre] = mapped_column(
        Enum(PoemGenre, name="poem_genre", values_callable=enum_values), nullable=False
    )
    tune: Mapped[str | None] = mapped_column(String(120))
    canonical_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text: Mapped[str] = mapped_column(Text, nullable=False)
    aliases: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    popularity: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), default=Decimal("0.500"), nullable=False
    )
    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(
            VerificationStatus,
            name="verification_status",
            values_callable=enum_values,
        ),
        default=VerificationStatus.PENDING,
        nullable=False,
    )
    source_name: Mapped[str | None] = mapped_column(String(200))
    source_url: Mapped[str | None] = mapped_column(Text)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    schema_version: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    author: Mapped["Author"] = relationship(back_populates="poems")  # noqa: F821
    lines: Mapped[list["PoemLine"]] = relationship(  # noqa: F821
        back_populates="poem", cascade="all, delete-orphan", order_by="PoemLine.line_no"
    )
    poem_tags: Mapped[list["PoemTag"]] = relationship(  # noqa: F821
        back_populates="poem", cascade="all, delete-orphan"
    )


class PoemLine(Base):
    __tablename__ = "poem_lines"
    __table_args__ = (
        Index("idx_poem_lines_poem", "poem_id", "line_no"),
        UniqueConstraint("poem_id", "line_no", name="uq_poem_lines_poem_line"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    poem_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("poems.id", ondelete="CASCADE"), nullable=False
    )
    line_no: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_featured: Mapped[bool] = mapped_column(default=False, nullable=False)

    poem: Mapped[Poem] = relationship(back_populates="lines")
