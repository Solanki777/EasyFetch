# 📁 Drive Assistant — Conversational AI Google Drive Search

A **production-style** AI assistant that lets you search and discover Google Drive files through natural language conversation. Built with FastAPI, LangGraph, Pydantic v2, Groq LLM, and Streamlit.

---

## ✨ Features

- 🔍 **Natural language file search** — "find my Q3 reports from last month"
- 🔄 **Conversational follow-up refinement** — "only PDFs", "newest ones", "from this week"
- 📂 **Folder awareness** — search within specific folders
- 🧠 **Active filter memory** — filters persist across conversation turns
- 📊 **Scored result ranking** — explainable relevance scores
- 🔁 **Deduplication** — removes exact and near-duplicate results
- 🗂️ **Smart grouping** — groups similar files by folder and name similarity
- ❓ **Clarification handling** — asks follow-up questions for vague queries
- 🏗️ **Deterministic query builder** — LLM never generates raw Drive queries
- 📝 **Structured JSON intent extraction** — validated Pydantic v2 schemas
- 🔒 **Service Account auth** — no OAuth flow required

---

## 🏗️ Architecture

```
User Query (Streamlit)
        │
        ▼
  FastAPI Backend
        │
        ├─► Session Manager (in-memory / Redis)
        │
        ├─► Intent Extraction (LLM → SearchIntent Pydantic model)
        │
        ├─► Query Builder (deterministic Python → Drive q string)
        │
        ├─► Drive Client (Google Drive API files.list())
        │
        ├─► Post-Processing Pipeline
        │     ├─ Deduplication
        │     ├─ Ranking (scored 0–100)
        │     └─ Grouping (by folder / name similarity)
        │
        └─► Response Formatter (LLM → conversational reply)
```

**Key principle:** The LLM only handles language (intent extraction + response formatting). All Drive query logic is pure deterministic Python.

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone <repo>
cd drive_assistant
pip install -r requirements.txt
```

### 2. Set Up Credentials

```bash
cp .env.example .env
# Edit .env — add your GROQ_API_KEY and Google service account path
mkdir credentials
# Place your Google service account JSON at credentials/service_account.json
```

### 3. Google Drive Service Account Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → Enable **Google Drive API**
3. Create a **Service Account** → Download JSON key
4. Save to `credentials/service_account.json`
5. **Share your Drive folder** with the service account email

### 4. Run Locally

**Terminal 1 — Backend:**
```bash
uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
streamlit run frontend/app.py
```

Open [http://localhost:8501](http://localhost:8501)

### 5. Or with Docker

```bash
docker-compose up --build
```

---

## 📁 Project Structure

```
drive_assistant/
├── backend/
│   ├── main.py                    # FastAPI app entrypoint
│   ├── config.py                  # Settings (pydantic-settings)
│   ├── dependencies.py            # FastAPI DI
│   ├── api/routes/                # chat, session, health endpoints
│   ├── schemas/                   # intent, drive, session, api schemas
│   ├── services/                  # intent_extractor, query_builder, drive_client,
│   │                              #   ranking, deduplication, grouping, formatter
│   ├── agent/                     # LangGraph workflow (graph, nodes, state)
│   ├── session/                   # SessionManager (in-memory + Redis)
│   └── utils/                     # mime_types, date_utils, text_utils, logging
├── frontend/
│   ├── app.py                     # Streamlit entrypoint
│   ├── components/                # chat_interface, result_card, active_filters
│   ├── state/                     # st.session_state management
│   └── utils/                     # api_client, mime_icons
├── tests/
│   ├── unit/                      # query_builder, ranking, dedup, followup_merge
│   └── fixtures/                  # sample intents + drive results
├── docs/
│   ├── architecture.md
│   └── api_reference.md
├── .env.example
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

---

## 📡 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/chat` | Main conversational search endpoint |
| `GET` | `/api/v1/session/{id}` | Get session state |
| `DELETE` | `/api/v1/session/{id}` | Clear session |
| `GET` | `/health` | Health check |

---

## 🔧 Configuration

All settings via `.env` file. Key options:

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `groq` | `groq`, `gemini`, or `openai` |
| `LLM_MODEL` | `llama3-8b-8192` | Model name for your provider |
| `GROQ_API_KEY` | — | Your Groq API key |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | `credentials/service_account.json` | Path to service account |
| `SESSION_TTL_SECONDS` | `3600` | Session expiry (1 hour) |
| `REDIS_URL` | — | Optional Redis for scalable sessions |

---

## 💬 Example Conversation

```
User:  "find my project proposal"
Bot:   "Found 3 files named 'project proposal'. Newest is 'Project Proposal v3.docx' in Work folder."

User:  "only PDFs"
Bot:   "Filtered to PDFs — 1 PDF version found."

User:  "from this year"
Bot:   "Narrowed to PDFs from this year. 1 result remains."

User:  "open the first one"
Bot:   "Opening 'Project Proposal Final.pdf'..."
```

---

## 🚢 Deployment

- **Backend**: [Railway](https://railway.app) or [Render](https://render.com) — deploy the Dockerfile
- **Frontend**: [Streamlit Cloud](https://streamlit.io/cloud) — point to `frontend/app.py`
- Set `BACKEND_URL` env var in the frontend to point to your deployed backend URL

---

## 📄 License

MIT
