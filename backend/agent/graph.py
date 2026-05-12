
"""
LangGraph orchestration of the search pipeline.
"""
from __future__ import annotations

import logging
from typing import TypedDict, List, Optional

from langgraph.graph import StateGraph, END

from backend.schemas.intent import SearchIntent
from backend.schemas.session import SessionState
from backend.schemas.drive import DriveFile
from backend.services.intent_extractor import IntentExtractor
from backend.services.query_builder import QueryBuilder
from backend.services.drive_client import DriveClient
from backend.services.ranking.engine import RankingService
from backend.services.deduplication import DeduplicationService
from backend.services.response_formatter import ResponseFormatter
from backend.session.followup_merger import FollowUpMerger

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    user_message: str
    session: SessionState
    intent: Optional[SearchIntent]
    results: List[DriveFile]
    reply: Optional[str]
    clarification_needed: bool
    clarification_prompt: Optional[str]
    open_file: Optional[DriveFile]


# ─────────────────────────────────────────────────────────────
# Services
# ─────────────────────────────────────────────────────────────

extractor = IntentExtractor()
merger = FollowUpMerger()
query_builder = QueryBuilder()
drive_client = DriveClient()
ranker = RankingService()
deduper = DeduplicationService()
formatter = ResponseFormatter()


# ─────────────────────────────────────────────────────────────
# Intent Extraction Node
# ─────────────────────────────────────────────────────────────

async def extract_intent_node(state: AgentState):

    print("\n===== EXTRACT_INTENT_NODE START =====", flush=True)
    intent = await extractor.extract(
        state["user_message"],
        state["session"]
    )

    print("\n===== EXTRACTED INTENT =====", flush=True)
    print(intent, flush=True)

    # Merge follow-up filters
    if intent and getattr(intent, "is_followup", False):

        intent = merger.merge(
            state["session"].active_filters,
            intent
        )

    # Clarification handling
    if intent and getattr(intent, "needs_clarification", False):

        return {
            **state,
            "intent": intent,
            "clarification_needed": True,
            "clarification_prompt": getattr(
                intent,
                "clarification_question",
                None
            )
        }

    return {
        **state,
        "intent": intent
    }


# ─────────────────────────────────────────────────────────────
# Retrieval Node
# ─────────────────────────────────────────────────────────────

async def retrieval_node(state: AgentState):

    print("\n===== RETRIEVAL_NODE START =====", flush=True)
    if state["clarification_needed"] or not state["intent"]:
        print("Skipping retrieval: clarification needed or no intent", flush=True)
        return state

    intent = state["intent"]

    # Open file follow-up
    if getattr(intent, "followup_action", None) == "open_file":

        idx = getattr(intent, "open_file_index", None)

        f = (
            state["session"].get_file_by_index(idx)
            if idx
            else None
        )

        if f:
            return {
                **state,
                "open_file": f,
                "results": [f]
            }

    # Build query
    params = query_builder.build(intent)

    print("\n===== QUERY PARAMS =====", flush=True)
    print(params, flush=True)

    # Drive search
    results = await drive_client.search(params)

    print("\n===== SEARCH RESULTS =====", flush=True)
    print(results, flush=True)

    print("\n===== RESULT COUNT =====", flush=True)
    print(len(results), flush=True)

    return {
        **state,
        "results": results
    }


# ─────────────────────────────────────────────────────────────
async def processing_node(state: AgentState):

    print("\n===== PROCESSING_NODE START =====", flush=True)
    if state["clarification_needed"] or not state["results"]:
        print("Skipping processing: no results", flush=True)
        return state

    results = deduper.deduplicate(state["results"])

    print("\n===== AFTER DEDUP =====", flush=True)
    print(len(results), flush=True)

    results = ranker.rank(results, state["intent"])

    print("\n===== AFTER RANKING =====", flush=True)
    print(len(results), flush=True)

    return {
        **state,
        "results": results
    }


# ─────────────────────────────────────────────────────────────
async def response_node(state: AgentState):

    print("\n===== RESPONSE_NODE START =====", flush=True)
    print("\n===== FINAL RESULTS TO FORMAT =====", flush=True)
    print(state["results"], flush=True)

    reply = await formatter.format(
        intent=state["intent"],
        results=state["results"],
        clarification_needed=state["clarification_needed"],
        clarification_prompt=state["clarification_prompt"],
        session=state["session"]
    )

    print("\n===== FINAL REPLY =====", flush=True)
    print(reply, flush=True)

    # Update session
    new_session = state["session"].model_copy(deep=True)

    new_session.active_filters = state["intent"]
    new_session.last_results = state["results"]

    new_session.add_turn(
        state["user_message"],
        reply,
        len(state["results"]),
        state["intent"]
    )

    return {
        **state,
        "reply": reply,
        "session": new_session
    }


# ─────────────────────────────────────────────────────────────
# Graph Builder
# ─────────────────────────────────────────────────────────────

def build_graph():

    workflow = StateGraph(AgentState)

    workflow.add_node("intent", extract_intent_node)
    workflow.add_node("retrieve", retrieval_node)
    workflow.add_node("process", processing_node)
    workflow.add_node("respond", response_node)

    workflow.set_entry_point("intent")

    workflow.add_edge("intent", "retrieve")
    workflow.add_edge("retrieve", "process")
    workflow.add_edge("process", "respond")
    workflow.add_edge("respond", END)

    return workflow.compile()
