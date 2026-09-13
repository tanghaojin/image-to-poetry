from app.db.base import Base
from app.db.models import Author, Poem, PoemLine, PoemTag, Tag, TagAlias


def test_initial_schema_contains_expected_tables() -> None:
    expected = {"authors", "poems", "poem_lines", "tags", "tag_aliases", "poem_tags"}
    assert expected == set(Base.metadata.tables)


def test_removed_tables_are_absent() -> None:
    assert "poem_variants" not in Base.metadata.tables
    assert "rate_limit_counters" not in Base.metadata.tables


def test_imports_are_registered() -> None:
    assert all([Author, Poem, PoemLine, PoemTag, Tag, TagAlias])

