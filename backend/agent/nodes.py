"""
LangGraph agent nodes — upgraded for universal discovery and observability.
"""
from __future__ import annotations

import logging
import json
import time
from typing import Any, Dict, List, Optional

from backend.agent.state import AgentState
from backend.services.drive_client import DriveClient
from backend.services.intent_extractor import IntentExtractor
from backend.services.query_builder import QueryBuilder
from backend.services.ranking.engine import RankingService
from backend.services.response_formatter import ResponseFormatter
from backend.session.followup_merger import merge_followup
from backend.utils.logging_config import log_divider
from backend.config import settings

logger = logging.getLogger(__name__)

# Singletons (initialized on first use)
_intent_extractor = None
_query_builder = None
_drive_client = None
_ranking_service = None
_response_formatter = None


def _get_services():
    global _intent_extractor, _query_builder, _drive_client, _ranking_service, _response_formatter
    if not _intent_extractor:
        _intent_extractor = IntentExtractor()
        _query_builder = QueryBuilder()
        _drive_client = DriveClient()
        _ranking_service = RankingService()
        _response_formatter = ResponseFormatter()
    return _intent_extractor, _query_builder, _drive_client, _ranking_service, _response_formatter


# ── Routing Functions ────────────────────────────────────────────────────────

def route_after_intent(state: AgentState) -> str:
    """Determine where to go after intent extraction."""
    intent = state.get("intent")
    if not intent:
        return "error"
    
    if intent.ambiguity and intent.ambiguity.needs_clarification:
        return "clarify"
        
    if intent.followup and intent.followup.action == "open_file":
        return "open_file"
        
    return "search"


# ── Nodes ───────────────────────────────────────────────────────────────────

async def extract_intent(state: AgentState) -> AgentState:
    """Node: Extract search intent from NL."""
    start_time = time.time()
    state["start_time"] = start_time
    extractor, _, _, _, _ = _get_services()
    
    logger.info("\n" + "="*40)
    logger.info("NEW USER SEARCH")
    logger.info("="*40)
    logger.info(f"User Query: {state['user_message']}")

    intent = await extractor.extract(state["user_message"], state["session"])
    
    # Handle follow-up logic
    if intent and intent.followup.is_followup and state["session"] and state["session"].last_intent:
        logger.info("Follow-up detected. Merging with previous intent.")
        intent = merge_followup(state["session"].last_intent, intent)

    state["intent"] = intent
    state["extraction_latency"] = time.time() - start_time
    
    if intent:
        logger.info(f"Normalized Query: {intent.filename_query if intent.filename_query else 'N/A'}")
        logger.info(f"Extracted Intent JSON: {json.dumps(intent.model_dump(), indent=2)}")
    
    return state


async def check_clarify(state: AgentState) -> AgentState:
    """Node: Handle cases where the query is too vague."""
    intent = state["intent"]
    state["reply"] = intent.ambiguity.clarification_question or "Could you please provide more details?"
    return state


async def build_and_search(state: AgentState) -> AgentState:
    """Node: Build query, search Drive with FALLBACK logic."""
    start_time = time.time()
    _, builder, drive, _, _ = _get_services()
    intent = state["intent"]
    
    if not intent:
        return state

    # 1. Resolve recursive folder context
    target_root = intent.folder_id or settings.google_drive_root_folder_id
    
    allowed_ids = []
    if target_root:
        allowed_ids = await drive.get_recursive_folder_ids(target_root)
        
    state["recursive_folder_count"] = len(allowed_ids)
    
    # 2. Fallback Search Loop
    modes = ["strict", "broad", "contains"]
    results = []
    final_mode = "none"
    
    for mode in modes:
        logger.info(f"Attempting search mode: {mode}")
        params = builder.build(intent, allowed_folder_ids=allowed_ids, mode=mode)
        
        logger.info(f"Generated Drive Query: [ {params.q} ]")
        
        batch = await drive.search(params)
        if batch:
            results = batch
            final_mode = mode
            logger.info(f"Found {len(results)} files in {mode} mode.")
            break
        else:
            logger.info(f"Zero results in {mode} mode. Falling back...")

    state["raw_drive_results"] = results
    state["search_mode"] = final_mode
    state["search_latency"] = time.time() - start_time
    
    logger.info(f"Drive API Returned: {len(results)} files")
    if results:
        logger.info(f"Raw Returned Files: {', '.join([f.name for f in results[:10]])}")

    return state


async def post_process(state: AgentState) -> AgentState:
    """Node: Rank results with fuzzy matching."""
    start_time = time.time()
    _, _, _, ranker, _ = _get_services()
    
    files = state.get("raw_drive_results") or []
    intent = state["intent"]

    if files and intent:
        logger.info("\n" + "="*40)
        logger.info("FUZZY MATCH SCORES")
        logger.info("="*40)
        
        ranked = ranker.rank(files, intent)
        
        for f in ranked[:10]:
            logger.info(f"  {f.name:40} -> {f.relevance_score:5.1f}")
            
        logger.info("\nRANKING DECISIONS:")
        for f in ranked[:5]:
            logger.info(f"  - {f.name}: {', '.join(f.match_reason)}")
            
        state["ranked_results"] = ranked
        state["results"] = ranked # Backward compatibility
    else:
        state["ranked_results"] = []
        state["results"] = []

    state["ranking_latency"] = time.time() - start_time
    return state


async def handle_open_file(state: AgentState) -> AgentState:
    """Node: Handle the 'open file' intent."""
    intent = state["intent"]
    index = intent.followup.open_file_index or 1
    
    # Get last results from session
    last_results = state["session"].last_results if state["session"] else []
    
    if last_results and 0 < index <= len(last_results):
        target = last_results[index - 1]
        state["open_file"] = target
        state["reply"] = f"Opening **{target.name}** for you."
    else:
        state["reply"] = f"I couldn't find file #{index} in our previous results."
        
    return state


async def format_response(state: AgentState) -> AgentState:
    """Node: Generate final conversational reply."""
    start_time = time.time()
    _, _, _, _, formatter = _get_services()
    
    ranked = state.get("ranked_results") or []
    intent = state["intent"]
    
    reply = await formatter.format(
        intent=intent,
        results=ranked,
        session=state["session"]
    )
    
    state["reply"] = reply
    
    # Save to session
    if state.get("session"):
        state["session"].last_intent = intent
        if ranked:
            state["session"].last_results = ranked
        state["session"].add_turn(
            user_msg=state["user_message"],
            reply=reply,
            results_count=len(ranked)
        )

    total_latency = time.time() - state.get("start_time", start_time)
    
    logger.info(f"\nAI Response: {reply}")
    logger.info(f"Search Duration: {total_latency:.2f}s")
    logger.info("\n" + "="*40)
    logger.info("SEARCH COMPLETE")
    logger.info("="*40 + "\n")
    
    return state


async def handle_error(state: AgentState) -> AgentState:
    """Node: Graceful error handling."""
    state["reply"] = "I encountered an error while searching your Drive. Please try again later."
    return state
