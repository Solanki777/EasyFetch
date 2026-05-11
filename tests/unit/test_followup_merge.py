"""Unit tests for follow-up intent merging logic."""
import pytest
from backend.schemas.intent import SearchIntent, DateFilter, FollowUpContext, SortSpec
from backend.session.followup_merger import merge_followup


def _base() -> SearchIntent:
    return SearchIntent(
        filename_query="report",
        file_extensions=["docx"],
        sort=SortSpec(field="relevance", direction="desc"),
        result_limit=10,
        raw_query="find reports",
    )


# ── filter_mime ───────────────────────────────────────────────────────────────

def test_filter_mime_replaces_type_keeps_filename():
    base = _base()
    update = SearchIntent(
        file_extensions=["pdf"],
        followup=FollowUpContext(is_followup=True, action="filter_mime"),
        raw_query="only PDFs",
    )
    merged = merge_followup(base, update)
    assert "pdf" in merged.file_extensions
    assert "docx" not in merged.file_extensions
    assert merged.filename_query == "report"  # preserved


def test_filter_mime_does_not_mutate_base():
    base = _base()
    update = SearchIntent(
        file_extensions=["pdf"],
        followup=FollowUpContext(is_followup=True, action="filter_mime"),
        raw_query="only PDFs",
    )
    merge_followup(base, update)
    assert "docx" in base.file_extensions   # base unchanged


# ── filter_date ───────────────────────────────────────────────────────────────

def test_filter_date_preserves_all_other_filters():
    base = _base()
    update = SearchIntent(
        date_filter=DateFilter(relative="this_month"),
        followup=FollowUpContext(is_followup=True, action="filter_date"),
        raw_query="from this month",
    )
    merged = merge_followup(base, update)
    assert merged.filename_query == "report"
    assert merged.file_extensions == ["docx"]
    assert merged.date_filter.relative == "this_month"


def test_filter_date_replaces_existing_date():
    base = SearchIntent(
        filename_query="report",
        date_filter=DateFilter(relative="this_year"),
        raw_query="report this year",
    )
    update = SearchIntent(
        date_filter=DateFilter(relative="this_week"),
        followup=FollowUpContext(is_followup=True, action="filter_date"),
        raw_query="from this week",
    )
    merged = merge_followup(base, update)
    assert merged.date_filter.relative == "this_week"


# ── sort ──────────────────────────────────────────────────────────────────────

def test_sort_only_changes_sort_by():
    base = _base()
    update = SearchIntent(
        sort=SortSpec(field="modifiedTime", direction="desc"),
        followup=FollowUpContext(is_followup=True, action="sort"),
        raw_query="newest ones",
    )
    merged = merge_followup(base, update)
    assert merged.sort.field == "modifiedTime"
    assert merged.filename_query == "report"
    assert merged.file_extensions == ["docx"]


# ── expand_results ────────────────────────────────────────────────────────────

def test_expand_results_increases_limit():
    base = SearchIntent(filename_query="file", result_limit=10, raw_query="find file")
    update = SearchIntent(
        followup=FollowUpContext(is_followup=True, action="expand_results"),
        raw_query="show more",
    )
    merged = merge_followup(base, update)
    assert merged.result_limit == 20


def test_expand_results_capped_at_50():
    base = SearchIntent(filename_query="file", result_limit=45, raw_query="find file")
    update = SearchIntent(
        followup=FollowUpContext(is_followup=True, action="expand_results"),
        raw_query="show more",
    )
    merged = merge_followup(base, update)
    assert merged.result_limit == 50


# ── search_content ────────────────────────────────────────────────────────────

def test_search_content_enables_flag_and_promotes_query():
    base = SearchIntent(filename_query="revenue", raw_query="find revenue")
    update = SearchIntent(
        followup=FollowUpContext(is_followup=True, action="search_content"),
        raw_query="search inside the file",
    )
    merged = merge_followup(base, update)
    assert merged.search_in_content is True
    assert merged.fulltext_query == "revenue"   # promoted from filename_query


def test_search_content_uses_explicit_fulltext_if_provided():
    base = SearchIntent(filename_query="report", raw_query="find report")
    update = SearchIntent(
        fulltext_query="annual revenue",
        followup=FollowUpContext(is_followup=True, action="search_content"),
        raw_query="search for annual revenue inside",
    )
    merged = merge_followup(base, update)
    assert merged.fulltext_query == "annual revenue"


# ── open_file ─────────────────────────────────────────────────────────────────

def test_open_file_sets_index_and_returns_early():
    base = _base()
    update = SearchIntent(
        followup=FollowUpContext(is_followup=True, action="open_file", open_file_index=2),
        raw_query="open the second file",
    )
    merged = merge_followup(base, update)
    assert merged.followup.open_file_index == 2
    assert merged.followup.action == "open_file"


# ── new_search ────────────────────────────────────────────────────────────────

def test_new_search_fully_replaces_intent():
    base = _base()
    fresh = SearchIntent(
        filename_query="tax documents",
        file_extensions=["pdf"],
        followup=FollowUpContext(is_followup=False, action="new_search"),
        raw_query="find tax documents",
    )
    merged = merge_followup(base, fresh)
    assert merged.filename_query == "tax documents"
    assert "docx" not in merged.file_extensions
    assert merged.raw_query == "find tax documents"


# ── Metadata ──────────────────────────────────────────────────────────────────

def test_merged_intent_carries_followup_metadata():
    base = _base()
    update = SearchIntent(
        sort=SortSpec(field="name", direction="asc"),
        followup=FollowUpContext(is_followup=True, action="sort"),
        raw_query="sort by name",
    )
    merged = merge_followup(base, update)
    assert merged.followup.is_followup is True
    assert merged.followup.action == "sort"
    assert merged.raw_query == "sort by name"
