"""Unit tests for the deterministic QueryBuilder service."""
import pytest
from backend.services.query_builder import QueryBuilder
from backend.schemas.intent import SearchIntent, DateFilter, SortSpec


@pytest.fixture
def builder():
    return QueryBuilder()


# ── Filename ──────────────────────────────────────────────────────────────────

def test_filename_query_produces_name_contains(builder):
    intent = SearchIntent(filename_query="Q3 Report", raw_query="find Q3 Report")
    params = builder.build(intent)
    assert "name contains 'Q3 Report'" in params.q


def test_always_excludes_trashed(builder):
    intent = SearchIntent(raw_query="anything")
    params = builder.build(intent)
    assert "trashed = false" in params.q


def test_empty_intent_only_trashed_clause(builder):
    intent = SearchIntent(raw_query="")
    params = builder.build(intent)
    assert params.q.strip() == "trashed = false"


# ── MIME / Extension ──────────────────────────────────────────────────────────

def test_pdf_extension_resolves_to_mime(builder):
    intent = SearchIntent(file_extensions=["pdf"], raw_query="find PDFs")
    params = builder.build(intent)
    assert "application/pdf" in params.q


def test_multiple_extensions_or_joined(builder):
    intent = SearchIntent(file_extensions=["pdf", "docx"], raw_query="find PDFs and docs")
    params = builder.build(intent)
    assert "application/pdf" in params.q
    assert "openxmlformats" in params.q
    assert " or " in params.q


def test_unknown_extension_ignored(builder):
    intent = SearchIntent(file_extensions=["xyz_unknown"], raw_query="test")
    params = builder.build(intent)
    # Unknown extension produces no MIME clause
    assert "mimeType" not in params.q


# ── Date filter ───────────────────────────────────────────────────────────────

def test_relative_date_this_month(builder):
    intent = SearchIntent(
        filename_query="report",
        date_filter=DateFilter(relative="this_month"),
        raw_query="reports from this month",
    )
    params = builder.build(intent)
    assert "modifiedTime >=" in params.q


def test_relative_date_today(builder):
    intent = SearchIntent(date_filter=DateFilter(relative="today"), raw_query="today")
    params = builder.build(intent)
    assert "modifiedTime >=" in params.q


# ── Folder ────────────────────────────────────────────────────────────────────

def test_folder_id_in_parents(builder):
    intent = SearchIntent(folder_id="abc123", raw_query="files in projects")
    params = builder.build(intent)
    assert "'abc123' in parents" in params.q


def test_no_folder_clause_without_folder_id(builder):
    intent = SearchIntent(folder_name="Projects", raw_query="files in Projects")
    params = builder.build(intent)
    assert "in parents" not in params.q


# ── Security ──────────────────────────────────────────────────────────────────

def test_single_quote_escaped(builder):
    intent = SearchIntent(filename_query="O'Brien's file", raw_query="test")
    params = builder.build(intent)
    assert "DROP" not in params.q
    assert "\\'" in params.q


def test_sql_injection_neutralised(builder):
    intent = SearchIntent(
        filename_query="'; DROP TABLE files; --",
        raw_query="injection test",
    )
    params = builder.build(intent)
    assert "\\'" in params.q
    assert "DROP TABLE" in params.q  # It's there, but escaped


# ── Sort / Ordering ───────────────────────────────────────────────────────────

def test_sort_modified_desc(builder):
    intent = SearchIntent(sort=SortSpec(field="modifiedTime", direction="desc"), raw_query="newest")
    params = builder.build(intent)
    assert params.order_by == "modifiedTime desc"


def test_sort_name_asc(builder):
    intent = SearchIntent(sort=SortSpec(field="name", direction="asc"), raw_query="alphabetical")
    params = builder.build(intent)
    assert params.order_by == "name"


# ── Combined ──────────────────────────────────────────────────────────────────

def test_combined_all_filters(builder):
    intent = SearchIntent(
        filename_query="budget",
        file_extensions=["xlsx"],
        date_filter=DateFilter(relative="this_year"),
        folder_id="folder_finance",
        raw_query="budget xlsx this year in finance",
    )
    params = builder.build(intent)
    assert "name contains 'budget'" in params.q
    assert "openxmlformats" in params.q
    assert "modifiedTime >=" in params.q
    assert "'folder_finance' in parents" in params.q
    assert "trashed = false" in params.q


def test_fulltext_only_when_search_in_content_true(builder):
    intent = SearchIntent(
        fulltext_query="revenue",
        search_in_content=False,
        raw_query="revenue",
    )
    params = builder.build(intent)
    assert "fullText" not in params.q

    intent2 = SearchIntent(
        fulltext_query="revenue",
        search_in_content=True,
        raw_query="search inside for revenue",
    )
    params2 = builder.build(intent2)
    assert "fullText contains 'revenue'" in params2.q
