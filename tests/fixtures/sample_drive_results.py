"""Sample DriveFile fixtures for unit tests."""
from datetime import datetime, timezone, timedelta
from backend.schemas.drive import DriveFile


def _dt(days_ago: int = 0) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days_ago)


def file_pdf_recent() -> DriveFile:
    return DriveFile(
        id="file_pdf_001",
        name="Q3 Report.pdf",
        mime_type="application/pdf",
        web_view_link="https://drive.google.com/file/d/001",
        modified_time=_dt(2),
        parent_folder_id="folder_finance",
        parent_folder_name="Finance",
    )


def file_docx_old() -> DriveFile:
    return DriveFile(
        id="file_docx_001",
        name="Q3 Report.docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        web_view_link="https://drive.google.com/file/d/002",
        modified_time=_dt(120),
        parent_folder_id="folder_finance",
        parent_folder_name="Finance",
    )


def file_xlsx_recent() -> DriveFile:
    return DriveFile(
        id="file_xlsx_001",
        name="Budget 2024.xlsx",
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        web_view_link="https://drive.google.com/file/d/003",
        modified_time=_dt(5),
        parent_folder_id="folder_finance",
        parent_folder_name="Finance",
    )


def file_exact_match() -> DriveFile:
    return DriveFile(
        id="file_exact_001",
        name="Q3 Report",
        mime_type="application/pdf",
        modified_time=_dt(1),
        parent_folder_id="folder_root",
        parent_folder_name="My Drive",
    )


def file_duplicate_same_folder() -> DriveFile:
    """Same name + same folder as file_pdf_recent — should be deduped."""
    return DriveFile(
        id="file_pdf_002",
        name="Q3 Report.pdf",
        mime_type="application/pdf",
        modified_time=_dt(30),
        parent_folder_id="folder_finance",
        parent_folder_name="Finance",
    )


def file_same_name_different_folder() -> DriveFile:
    """Same name but different folder — NOT a duplicate."""
    return DriveFile(
        id="file_pdf_003",
        name="Q3 Report.pdf",
        mime_type="application/pdf",
        modified_time=_dt(10),
        parent_folder_id="folder_hr",
        parent_folder_name="HR",
    )


def sample_result_list() -> list:
    return [
        file_pdf_recent(),
        file_docx_old(),
        file_xlsx_recent(),
        file_exact_match(),
    ]
