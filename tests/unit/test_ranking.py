"""Unit tests for the RankingService."""
import pytest
from datetime import datetime, timezone, timedelta
from backend.services.ranking import RankingService
from backend.schemas.drive import DriveFile
from backend.schemas.intent import SearchIntent


@pytest.fixture
def ranker():
    return RankingService()


def _file(name: str, days_old: int = 10, mime: str = "application/pdf") -> DriveFile:
    return DriveFile(
        id=f"id_{name.replace(' ', '_')}",
        name=name,
        mime_type=mime,
        modified_time=datetime.now(timezone.utc) - timedelta(days=days_old),
    )


# ── Name match scoring ────────────────────────────────────────────────────────

def test_exact_name_ranks_highest(ranker):
    intent = SearchIntent(filename_query="Q3 Report", raw_query="Q3 Report")
    files = [
        _file("Q3 Report Analysis"),
        _file("Q3 Report"),
        _file("Summary Document"),
    ]
    ranked = ranker.rank(files, intent)
    assert ranked[0].name == "Q3 Report"


def test_exact_match_produces_highest_name_score(ranker):
    intent = SearchIntent(filename_query="budget", raw_query="budget")
    exact = _file("budget")
    partial = _file("budget report 2024")
    ranked = ranker.rank([partial, exact], intent)
    assert ranked[0].name == "budget"


def test_contains_match_scores_lower_than_starts_with(ranker):
    intent = SearchIntent(filename_query="report", raw_query="report")
    starts = _file("report 2024")
    contains = _file("annual report 2024")
    ranked = ranker.rank([contains, starts], intent)
    assert ranked[0].name == "report 2024"


def test_no_query_produces_zero_name_score(ranker):
    intent = SearchIntent(raw_query="anything")
    f = _file("some file", days_old=1)
    result = ranker.rank([f], intent)
    # The new service uses "strong name match" etc.
    assert "strong name match" not in result[0].match_reason


# ── Recency scoring ───────────────────────────────────────────────────────────

def test_recent_file_scores_higher_than_old(ranker):
    intent = SearchIntent(raw_query="anything")
    new_file = _file("file A", days_old=1)
    old_file = _file("file B", days_old=365)
    ranked = ranker.rank([old_file, new_file], intent)
    assert ranked[0].name == "file A"


def test_no_modified_time_scores_zero_recency(ranker):
    intent = SearchIntent(raw_query="test")
    f = DriveFile(id="x", name="no date file", mime_type="application/pdf")
    result = ranker.rank([f], intent)
    assert result[0].relevance_score < 50  # no recency boost


# ── Type match ────────────────────────────────────────────────────────────────

def test_mime_match_bonus_applied(ranker):
    intent = SearchIntent(
        filename_query="data",
        mime_types=["application/pdf"],
        raw_query="data PDF",
    )
    pdf = _file("data report", mime="application/pdf")
    docx = _file("data report", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    ranked = ranker.rank([docx, pdf], intent)
    assert ranked[0].mime_type == "application/pdf"
    assert "exact type match" in ranked[0].match_reason


def test_extension_resolves_to_mime_for_type_bonus(ranker):
    intent = SearchIntent(
        file_extensions=["pdf"],
        raw_query="find PDFs",
    )
    pdf = _file("report.pdf", mime="application/pdf")
    txt = _file("report.txt", mime="text/plain")
    ranked = ranker.rank([txt, pdf], intent)
    assert ranked[0].mime_type == "application/pdf"


# ── Score bounds ──────────────────────────────────────────────────────────────

def test_score_never_exceeds_100(ranker):
    intent = SearchIntent(
        filename_query="Q3 Report",
        mime_types=["application/pdf"],
        search_in_content=True,
        fulltext_query="Q3 Report",
        raw_query="Q3 Report",
    )
    f = _file("Q3 Report", days_old=0, mime="application/pdf")
    result = ranker.rank([f], intent)
    assert result[0].relevance_score <= 100.0


def test_match_reason_list_populated(ranker):
    intent = SearchIntent(filename_query="budget", raw_query="budget")
    f = _file("budget 2024", days_old=3)
    result = ranker.rank([f], intent)
    assert len(result[0].match_reason) > 0


# ── Ordering ──────────────────────────────────────────────────────────────────

def test_ranking_returns_sorted_descending(ranker):
    intent = SearchIntent(filename_query="report", raw_query="report")
    files = [_file("other file", days_old=200), _file("report", days_old=1)]
    ranked = ranker.rank(files, intent)
    scores = [f.relevance_score for f in ranked]
    assert scores == sorted(scores, reverse=True)
