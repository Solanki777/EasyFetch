"""
LangGraph orchestration of the search pipeline.
"""
from __future__ import annotations

import logging
from typing import TypedDict, List, Optional, Any

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


# Services
extractor = IntentExtractor()
merger = FollowUpMerger()
query_builder = QueryBuilder()
drive_client = DriveClient()
ranker = RankingService()
deduper = DeduplicationService()
formatter = ResponseFormatter()


async def extract_intent_node(state: AgentState):
    """LLM extracts intent and merges with session filters."""
    intent = await extractor.extract(state["user_message"], state["session"])
    
    if intent and intent.followup.is_followup:
        intent = merger.merge(state["session"].active_filters, intent)
    
    # Check for ambiguity
    if intent and intent.ambiguity.needs_clarification:
        return {
            **state,
            "intent": intent,
            "clarification_needed": True,
            "clarification_prompt": intent.ambiguity.clarification_question
        }

    return {**state, "intent": intent}


async def retrieval_node(state: AgentState):
    """Deterministic Drive retrieval."""
    if state["clarification_needed"] or not state["intent"]:
        return state

    intent = state["intent"]
    
    # Check if we should open a file instead of searching
    if intent.followup.action == "open_file":
        idx = intent.followup.open_file_index
        f = state["session"].get_file_by_index(idx) if idx else None
        if f:
            return {**state, "open_file": f, "results": [f]}

    params = query_builder.build(intent)
    results = await drive_client.search(params)
    
    return {**state, "results": results}


async def processing_node(state: AgentState):
    """Ranking and deduplication."""
    if state["clarification_needed"] or not state["results"]:
        return state

    results = deduper.deduplicate(state["results"])
    results = ranker.rank(results, state["intent"])
    
    return {**state, "results": results}


async def response_node(state: AgentState):
    """Conversational formatting."""
    reply = await formatter.format(
        intent=state["intent"],
        results=state["results"],
        clarification_needed=state["clarification_needed"],
        clarification_prompt=state["clarification_prompt"],
        session=state["session"]
    )
    
    # Update session state
    new_session = state["session"].model_copy(deep=True)
    new_session.active_filters = state["intent"]
    new_session.last_results = state["results"]
    new_session.add_turn(state["user_message"], reply, len(state["results"]), state["intent"])

    return {**state, "reply": reply, "session": new_session}


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
