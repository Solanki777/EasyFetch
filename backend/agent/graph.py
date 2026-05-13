"""
LangGraph orchestration — unified to use backend.agent.nodes.
"""
from __future__ import annotations

import logging
from langgraph.graph import StateGraph, END

from backend.agent.state import AgentState
from backend.agent.nodes import (
    extract_intent,
    route_after_intent,
    check_clarify,
    build_and_search,
    post_process,
    format_response,
    handle_open_file,
    handle_error
)

logger = logging.getLogger(__name__)


def build_graph():
    """Build and compile the search pipeline graph."""
    
    workflow = StateGraph(AgentState)

    # 1. Define nodes
    workflow.add_node("extract", extract_intent)
    workflow.add_node("clarify", check_clarify)
    workflow.add_node("search", build_and_search)
    workflow.add_node("process", post_process)
    workflow.add_node("format", format_response)
    workflow.add_node("open_file", handle_open_file)
    workflow.add_node("error", handle_error)

    # 2. Define edges and routing
    workflow.set_entry_point("extract")
    
    workflow.add_conditional_edges(
        "extract",
        route_after_intent,
        {
            "clarify": "clarify",
            "search": "search",
            "open_file": "open_file",
            "error": "error"
        }
    )

    workflow.add_edge("search", "process")
    workflow.add_edge("process", "format")
    
    # Terminal nodes
    workflow.add_edge("clarify", END)
    workflow.add_edge("format", END)
    workflow.add_edge("open_file", END)
    workflow.add_edge("error", END)

    return workflow.compile()
