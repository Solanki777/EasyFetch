# Drive Assistant — API Reference

## Base URL
```
http://localhost:8000
```

---

## POST /api/v1/chat

Main conversational search endpoint.

### Request
```json
{
  "session_id": "abc-123",
  "message": "find my Q3 reports from last month"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `session_id` | string | No | Auto-generated UUID if omitted |
| `message` | string | Yes | User's natural language query (1–2000 chars) |

### Response
```json
{
  "session_id": "abc-123",
  "reply": "I found 4 files matching 'Q3 report' from the past month.",
  "results": [
    {
      "id": "1BxiMVs0XRA5nFMdKv...",
      "name": "Q3 2024 Revenue Report.pdf",
      "mime_type": "application/pdf",
      "web_view_link": "https://drive.google.com/file/d/...",
      "modified_time": "2024-09-28T10:30:00+00:00",
      "parent_folder_name": "Finance",
      "size_bytes": 204800,
      "relevance_score": 87.5,
      "match_reason": ["filename contains query", "recently modified", "exact type match"],
      "is_duplicate": false,
      "similarity_group": "sim_0"
    }
  ],
  "active_filters": {
    "filename_query": "Q3 report",
    "date_filter": {"relative": "this_month"},
    "sort_by": "relevance"
  },
  "clarification_needed": false,
  "clarification_prompt": null,
  "result_count": 4,
  "open_file": null
}
```

---

## GET /api/v1/session/{session_id}

Inspect current session state.

### Response
```json
{
  "session_id": "abc-123",
  "created_at": "2024-09-28T10:00:00+00:00",
  "last_active": "2024-09-28T10:30:00+00:00",
  "turn_count": 3,
  "active_filters": {"filename_query": "Q3 report"},
  "last_results_count": 4
}
```

---

## DELETE /api/v1/session/{session_id}

Clear a session. Returns `204 No Content`.

---

## GET /health

Liveness probe.

### Response
```json
{
  "status": "ok",
  "version": "1.0.0",
  "session_count": 12
}
```

---

## Example Conversation Flow

### Turn 1 — Fresh search
```
POST /chat  { "message": "find my project proposal" }
→ reply: "Found 3 files named 'project proposal'. Newest is 'Project Proposal v3.docx'."
→ active_filters: { "filename_query": "project proposal" }
```

### Turn 2 — Follow-up: filter type
```
POST /chat  { "message": "only PDFs" }
→ reply: "Filtered to PDFs — 1 PDF version found."
→ active_filters: { "filename_query": "project proposal", "file_extensions": ["pdf"] }
```

### Turn 3 — Follow-up: date
```
POST /chat  { "message": "from this year" }
→ reply: "Narrowed to PDFs from this year. 1 result."
→ active_filters: { "filename_query": "project proposal", "file_extensions": ["pdf"], "date_filter": {"relative": "this_year"} }
```

### Turn 4 — Follow-up: open file
```
POST /chat  { "message": "open the first one" }
→ reply: "Opening 'Project Proposal Final.pdf'..."
→ open_file: { "name": "Project Proposal Final.pdf", "web_view_link": "https://..." }
```

### Turn 5 — New search (resets filters)
```
POST /chat  { "message": "find my tax documents" }
→ reply: "Starting fresh. Found 6 tax-related files across 3 folders."
→ active_filters: { "filename_query": "tax documents" }
```

---

## Error Responses

| Status | Scenario |
|---|---|
| `400` | Invalid request body (Pydantic validation failure) |
| `404` | Session not found (GET/DELETE session) |
| `500` | Unhandled backend error (LLM timeout, Drive API failure) |

All `500` errors return:
```json
{ "detail": "Internal server error" }
```
Structured error details appear in backend logs (JSON format).
