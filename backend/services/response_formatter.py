
"""
Conversational response formatter.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from backend.config import settings
from backend.schemas.drive import DriveFile
from backend.schemas.intent import SearchIntent
from backend.schemas.session import SessionState

logger = logging.getLogger(__name__)


class ResponseFormatter:
    """
    Generates concise conversational replies
    based on search results and intent.
    """

    def __init__(self):

        self._llm = ChatGroq(
            api_key=settings.groq_api_key,
            model_name=settings.llm_model,
            temperature=0.2
        )

        self._prompt = ChatPromptTemplate.from_messages([

            (
                "system",
                self._get_system_prompt()
            ),

            (
                "user",
                (
                    "Intent Summary: {intent_summary}\n"
                    "Results Found: {count}\n"
                    "Sample Files: {samples}\n"
                    "Used Content Search: {content_search}"
                )
            )
        ])

        self._chain = (
            self._prompt
            | self._llm
        )

    async def format(
        self,
        intent: SearchIntent,
        results: List[DriveFile],
        clarification_needed: bool = False,
        clarification_prompt: Optional[str] = None,
        session: Optional[SessionState] = None
    ) -> str:

        # ── Clarification ───────────────────────────────────────────

        if clarification_needed:

            return (
                clarification_prompt
                or
                "Could you give me more details about what you're looking for?"
            )

        # ── No Results ─────────────────────────────────────────────

        if not results:

            if intent.search_in_content:

                return (
                    "I searched inside file contents but couldn't "
                    "find any matching files."
                )

            return (
                "I couldn't find any files matching your search. "
                "Try using different keywords or broader filters."
            )

        # ── Generate Conversational Reply ──────────────────────────

        try:

            samples = ", ".join([
                f.name
                for f in results[:3]
            ])

            intent_summary = (
                intent.active_filter_summary()
                if hasattr(intent, "active_filter_summary")
                else {}
            )

            resp = await self._chain.ainvoke({

                "intent_summary": str(
                    intent_summary
                ),

                "count": len(results),

                "samples": samples,

                "content_search": (
                    "yes"
                    if intent.search_in_content
                    else "no"
                )
            })

            content = (
                resp.content.strip()
                if resp.content
                else ""
            )

            # Rich observability logging
            logger.info("=" * 40)
            logger.info("FINAL RESPONSE FORMATTED")
            logger.info(f"  Reply: {content}")
            logger.info("=" * 40)

            return content

        except Exception as e:

            logger.exception(
                f"Response formatting failed: {e}"
            )

            if intent.search_in_content:

                return (
                    f"I searched inside file contents and found "
                    f"{len(results)} matching files."
                )

            return (
                f"I found {len(results)} files matching your search."
            )

    def _get_system_prompt(self) -> str:

        return """
You are the conversational response layer for a Google Drive AI assistant.

━━━━━━━━━━━━━━━━━━━━
RULES
━━━━━━━━━━━━━━━━━━━━
- Keep replies VERY SHORT (1-2 sentences max).
- ALWAYS mention the count of files found.
- Do NOT list all filenames (the UI already shows them).
- Do NOT hallucinate or invent information.
- Be natural and professional.

EXAMPLES:
- "I found 12 PDF files from last month."
- "I searched inside file contents and found 3 matching documents."
- "I couldn't find any files matching those criteria."

Style: concise, clean, professional.
"""
