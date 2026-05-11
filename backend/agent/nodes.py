"""
LangGraph node functions — each node is a pure async function.

Nodes:
  extract_intent    → LLM extracts SearchIntent from user message
  check_clarify     → returns early with clarification prompt
  resolve_folder    → folder_name → folder_id lookup
  build_and_search  → QueryBuilder + DriveClient
  post_process      → dedup + rank + group
  format_response   → LLM generates conversational reply
  handle_open_file  → returns file URL for "open file" actions
  handle_error      → graceful fallback reply
"""
from __future__ import annotations

import logging

from backend.agent.state import AgentState
from backend.services.deduplication import DeduplicationService
from backend.services.drive_client import DriveClient
from backend.services.grouping import GroupingService
from backend.services.intent_extractor import IntentExtractor
from backend.services.query_builder import QueryBuilder
from backend.services.ranking import RankingService
from backend.services.response_formatter import ResponseFormatter
from backend.session.followup_merger import merge_followup

logger = logging.getLogger(__name__)

# ── Service singletons (instantiated once per process) ────────────────────────
_intent_extractor = IntentExtractor()
_query_builder = QueryBuilder()
_drive_client = DriveClient()
_ranking = RankingService()
_dedup = DeduplicationService()
_grouping = GroupingService()
_formatter = ResponseFormatter()


# ── Node: extract_intent ──────────────────────────────────────────────────────

async def extract_intent(state: AgentState) -> AgentState:
    intent = await _intent_extractor.extract(
        user_message=state["user_message"],
        session=state["session"],
    )

    if intent is None:
        state["error"] = "intent_extraction_failed"
        return state

    # Merge with active session filters if this is a follow-up
    if intent.is_followup and state["session"].active_filters:
        intent = merge_followup(
            base=state["session"].active_filters,
            update=intent,
        )

    # Resolve folder name → ID (cache-first)
    if intent.folder_name and not intent.folder_id:
        cache = state["session"].folder_cache
        if intent.folder_name in cache:
            intent.folder_id = cache[intent.folder_name]
        else:
            folder_id = await _drive_client.get_folder_id(intent.folder_name)
            if folder_id:
                intent.folder_id = folder_id
                state["session"].folder_cache[intent.folder_name] = folder_id

    state["intent"] = intent
    return state


# ── Router ────────────────────────────────────────────────────────────────────

def route_after_intent(state: AgentState) -> str:
    if state.get("error"):
        return "error"
    intent = state.get("intent")
    if intent is None:
        return "error"
    if intent.needs_clarification:
        return "clarify"
    if intent.followup_action == "open_file":
        return "open_file"
    return "search"


# ── Node: check_clarify ───────────────────────────────────────────────────────

async def check_clarify(state: AgentState) -> AgentState:
    state["clarification_needed"] = True
    state["clarification_prompt"] = state["intent"].clarification_question
    state["results"] = []
    return state


# ── Node: build_and_search ────────────────────────────────────────────────────

async def build_and_search(state: AgentState) -> AgentState:
    params = _query_builder.build(state["intent"])
    results = await _drive_client.search(params)
    state["raw_drive_results"] = results
    return state


# ── Node: post_process ────────────────────────────────────────────────────────

async def post_process(state: AgentState) -> AgentState:
    files = state.get("raw_drive_results") or []
    files = _dedup.deduplicate(files)
    files = _ranking.rank(files, state["intent"])

    # Limit to requested result count
    limit = state["intent"].result_limit or 10
    files = files[:limit]

    groups = _grouping.group(files)
    state["ranked_results"] = files
    state["grouped_results"] = {k: [f.id for f in v] for k, v in groups.items()}
    return state


# ── Node: handle_open_file ────────────────────────────────────────────────────

async def handle_open_file(state: AgentState) -> AgentState:
    intent = state["intent"]
    idx = intent.open_file_index
    file = state["session"].get_file_by_index(idx) if idx else None
    if file:
        state["open_file"] = file.model_dump()
        state["reply"] = f"Opening **{file.name}** — click the link below."
        state["results"] = [file.model_dump()]
    else:
        state["reply"] = (
            f"I couldn't find file #{idx} in the previous results. "
            "Please run a search first or specify a different number."
        )
        state["results"] = []
    return state


# ── Node: format_response ─────────────────────────────────────────────────────

async def format_response(state: AgentState) -> AgentState:
    ranked = state.get("ranked_results") or []
    reply = await _formatter.format(
        intent=state.get("intent"),
        results=ranked,
        clarification_needed=state.get("clarification_needed", False),
        clarification_prompt=state.get("clarification_prompt"),
        session=state["session"],
    )
    state["reply"] = reply
    state["results"] = [r.model_dump() for r in ranked]

    # Update session memory
    intent = state.get("intent")
    if intent and not intent.needs_clarification:
        state["session"].active_filters = intent
        state["session"].last_results = ranked

    state["session"].add_turn(
        user_msg=state["user_message"],
        reply=reply,
        results_count=len(ranked),
    )
    return state


# ── Node: handle_error ────────────────────────────────────────────────────────

async def handle_error(state: AgentState) -> AgentState:
    error = state.get("error", "unknown")
    logger.warning("Agent error node reached", extra={"error": error})

    messages = {
        "intent_extraction_failed": (
            "I didn't quite catch that. Could you rephrase? "
            "For example: 'find my PDF reports from last month'."
        ),
        "drive_api_error": (
            "I couldn't reach Google Drive right now. Please try again in a moment."
        ),
    }
    state["reply"] = messages.get(error, "Something went wrong. Please try again.")
    state["results"] = []
    state["clarification_needed"] = False
    return state
