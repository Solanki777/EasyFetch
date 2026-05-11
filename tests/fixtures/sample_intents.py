"""Sample SearchIntent fixtures for unit tests."""
from backend.schemas.intent import SearchIntent, DateFilter


def intent_filename_only() -> SearchIntent:
    return SearchIntent(filename_query="Q3 Report", raw_query="find Q3 Report")


def intent_pdf_filter() -> SearchIntent:
    return SearchIntent(file_extensions=["pdf"], raw_query="find PDFs")


def intent_date_month() -> SearchIntent:
    return SearchIntent(
        filename_query="report",
        date_filter=DateFilter(relative="this_month"),
        raw_query="reports from this month",
    )


def intent_folder_scoped() -> SearchIntent:
    return SearchIntent(folder_id="abc123", raw_query="files in projects folder")


def intent_sql_injection() -> SearchIntent:
    return SearchIntent(
        filename_query="'; DROP TABLE files; --",
        raw_query="malicious input test",
    )


def intent_combined() -> SearchIntent:
    return SearchIntent(
        filename_query="budget",
        file_extensions=["xlsx"],
        date_filter=DateFilter(relative="this_year"),
        raw_query="budget spreadsheets from this year",
    )


def intent_followup_mime() -> SearchIntent:
    return SearchIntent(
        file_extensions=["pdf"],
        is_followup=True,
        followup_action="filter_mime",
        raw_query="only PDFs",
    )


def intent_followup_sort() -> SearchIntent:
    return SearchIntent(
        sort_by="modified_desc",
        is_followup=True,
        followup_action="sort",
        raw_query="newest ones",
    )


def intent_new_search() -> SearchIntent:
    return SearchIntent(
        filename_query="tax documents",
        is_followup=False,
        followup_action="new_search",
        raw_query="find tax documents",
    )
