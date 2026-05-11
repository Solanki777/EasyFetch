# Drive Assistant Architecture

## System Overview

```
User Query (Streamlit UI)
        │
        ▼
  FastAPI Backend  (/api/v1/chat)
        │
        ├─► Session Manager
        │       └─► SessionState {active_filters, last_results, history, folder_cache}
        │
        ├─► LangGraph Agent Pipeline
        │       │
        │       ├── [Node] extract_intent
        │       │       └─► IntentExtractor (LLM) → SearchIntent (Pydantic)
        │       │
        │       ├── [Router] route_after_intent
        │       │       ├── clarify    → check_clarify
        │       │       ├── search     → build_and_search
        │       │       ├── open_file  → handle_open_file
        │       │       └── error      → handle_error
        │       │
        │       ├── [Node] build_and_search
        │       │       ├─► QueryBuilder (pure Python) → DriveSearchParams
        │       │       └─► DriveClient → List[DriveFile]
        │       │
        │       ├── [Node] post_process
        │       │       ├─► DeduplicationService
        │       │       ├─► RankingService (0–100 score)
        │       │       └─► GroupingService (folder + similarity)
        │       │
        │       └── [Node] format_response
        │               └─► ResponseFormatter (LLM) → conversational reply
        │
        └─► ChatResponse {reply, results[], active_filters, clarification_needed}
```

## Key Design Principles

### 1. LLM Isolation
The LLM only handles language tasks:
- **IntentExtractor** — reads natural language, outputs `SearchIntent` JSON
- **ResponseFormatter** — reads result statistics, outputs conversational text

The LLM **never**:
- Generates Drive API query strings
- Calls any API directly
- Performs ranking or business logic

### 2. Deterministic Query Building
`QueryBuilder` converts `SearchIntent` → Drive `q` string using pure Python:
- Input validated by Pydantic before entering the builder
- All string escaping centralised in `text_utils.escape_drive_string()`
- No regex injection, no SQL injection possible
- Fully testable without LLM mocks

### 3. Conversational State
`SessionState` persists per-session:
| Field | Purpose |
|---|---|
| `active_filters` | Current `SearchIntent` — follow-ups merge into this |
| `last_results` | Last ranked `DriveFile[]` — enables "open the 2nd one" |
| `history` | Last N turns — sent to LLM as context |
| `folder_cache` | Name → ID cache to avoid repeat API calls |

### 4. Follow-up Merging
`merge_followup(base, update)` merges new intent into session intent per action type:
- `filter_mime` → replace type filters only
- `filter_date` → replace date filter only
- `sort` → replace sort_by only
- `expand_results` → increment result_limit
- `search_content` → enable fullText search
- `open_file` → resolve index into last_results
- `new_search` → full replacement

### 5. Ranking Model
```
Score = name_match (40) + recency (25) + position (20) + type_match (10) + content_match (5)
```
- **name_match**: exact=40pts, starts_with=34pts, contains=24pts
- **recency**: exponential decay, half-life 30 days
- **position**: Drive's own ordering preserved as a signal
- **type_match**: bonus for exact MIME match
- All scores capped at 100; `match_reason[]` exposes why each file ranked

### 6. Deduplication
- Pass 1: exact ID dedup (Drive IDs globally unique)
- Pass 2: (normalised_name, parent_folder_id) dedup — same file in same folder, keep newest
- Files with same name in different folders are **not** duplicates

## Deployment Architecture

```
┌─────────────────────────────────────────────┐
│              Railway / Render               │
│                                             │
│  ┌─────────────┐    ┌─────────────────────┐ │
│  │  FastAPI    │◄───│  Streamlit          │ │
│  │  :8000      │    │  :8501              │ │
│  └──────┬──────┘    └─────────────────────┘ │
│         │                                   │
│         ▼                                   │
│  ┌─────────────┐                            │
│  │  Redis      │  (optional)                │
│  └─────────────┘                            │
└─────────────────────────────────────────────┘
         │
         ▼
  Google Drive API (Service Account)
```

## Technology Choices

| Decision | Choice | Rationale |
|---|---|---|
| LLM generates q string | ❌ Never | Non-deterministic, untestable, security risk |
| Pydantic for intent schema | ✅ | Validated, typed, self-documenting contract |
| LangGraph for workflow | ✅ | Explicit routing, testable nodes, observable |
| In-memory session (default) | ✅ | Zero deps for local dev; swap to Redis trivially |
| Service Account auth | ✅ | No OAuth flow, server-to-server only |
| Groq LLM | ✅ recommended | Free tier, fast inference, llama3 quality |
| Score-based ranking | ✅ | Explainable, tunable, no black box |
| Follow-up merging | ✅ | Natural conversation; filters accumulate |
