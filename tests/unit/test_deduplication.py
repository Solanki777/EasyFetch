"""Unit tests for DeduplicationService."""
import pytest
from datetime import datetime, timezone, timedelta
from backend.services.deduplication import DeduplicationService
from backend.schemas.drive import DriveFile


@pytest.fixture
def dedup():
    return DeduplicationService()


def _file(
    file_id: str,
    name: str,
    folder_id: str = "folder_a",
    days_old: int = 10,
) -> DriveFile:
    return DriveFile(
        id=file_id,
        name=name,
        mime_type="application/pdf",
        modified_time=datetime.now(timezone.utc) - timedelta(days=days_old),
        parent_folder_id=folder_id,
    )


# ── ID deduplication ──────────────────────────────────────────────────────────

def test_removes_exact_id_duplicates(dedup):
    files = [
        _file("id_001", "report.pdf"),
        _file("id_001", "report.pdf"),   # same ID — duplicate
        _file("id_002", "other.pdf"),
    ]
    result = dedup.deduplicate(files)
    ids = [f.id for f in result]
    assert ids.count("id_001") == 1
    assert len(result) == 2


def test_unique_ids_all_preserved(dedup):
    files = [_file(f"id_{i}", f"file_{i}.pdf") for i in range(5)]
    result = dedup.deduplicate(files)
    assert len(result) == 5


# ── Same name / same folder ───────────────────────────────────────────────────

def test_same_name_same_folder_keeps_newest(dedup):
    newer = _file("id_new", "Q3 Report.pdf", folder_id="folder_a", days_old=2)
    older = _file("id_old", "Q3 Report.pdf", folder_id="folder_a", days_old=30)
    result = dedup.deduplicate([older, newer])
    assert len(result) == 1
    assert result[0].id == "id_new"


def test_same_name_different_folder_both_kept(dedup):
    finance = _file("id_fin", "Q3 Report.pdf", folder_id="folder_finance")
    hr      = _file("id_hr",  "Q3 Report.pdf", folder_id="folder_hr")
    result = dedup.deduplicate([finance, hr])
    assert len(result) == 2


def test_three_duplicates_keeps_only_newest(dedup):
    files = [
        _file("id_a", "report.pdf", days_old=5),
        _file("id_b", "report.pdf", days_old=20),
        _file("id_c", "report.pdf", days_old=1),   # newest
    ]
    result = dedup.deduplicate(files)
    assert len(result) == 1
    assert result[0].id == "id_c"


# ── Case normalisation ────────────────────────────────────────────────────────

def test_case_insensitive_name_comparison(dedup):
    lower  = _file("id_1", "annual report.pdf", folder_id="folder_a", days_old=10)
    upper  = _file("id_2", "Annual Report.pdf", folder_id="folder_a", days_old=20)
    result = dedup.deduplicate([lower, upper])
    assert len(result) == 1
    assert result[0].id == "id_1"   # newer (lower days_old)


# ── Duplicate group ID assigned ───────────────────────────────────────────────

def test_duplicate_group_id_set(dedup):
    newer = _file("id_new", "report.pdf", days_old=2)
    older = _file("id_old", "report.pdf", days_old=30)
    # Run dedup — both get a group id; older is filtered out
    dedup.deduplicate([newer, older])
    # The newer one should have a group id set
    assert newer.duplicate_group_id is not None


# ── Empty input ───────────────────────────────────────────────────────────────

def test_empty_list_returns_empty(dedup):
    assert dedup.deduplicate([]) == []


def test_single_file_returned_unchanged(dedup):
    f = _file("id_001", "solo.pdf")
    result = dedup.deduplicate([f])
    assert len(result) == 1
    assert result[0].id == "id_001"
