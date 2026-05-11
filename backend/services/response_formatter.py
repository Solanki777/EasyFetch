"""
Conversational response formatter.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from backend.config import settings
from backend.schemas.intent import SearchIntent
from backend.schemas.drive import DriveFile
from backend.schemas.session import SessionState

logger = logging.getLogger(__name__)


class ResponseFormatter:
    """
    Generates conversational replies based on search results and intent.
    """

    def __init__(self):
        self._llm = ChatGroq(
            api_key=settings.groq_api_key.get_secret_value(),
            model_name="llama3-70b-8192",
            temperature=0.3
        )
        self._prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt()),
            ("user", "Intent: {intent_summary}\nResults found: {count}\nResult samples: {samples}")
        ])
        self._chain = self._prompt | self._llm

    async def format(
        self,
        intent: SearchIntent,
        results: List[DriveFile],
        clarification_needed: bool = False,
        clarification_prompt: Optional[str] = None,
        session: Optional[SessionState] = None
    ) -> str:
        if clarification_needed:
            return clarification_prompt or "Could you give me more details about what you're looking for?"

        if not results:
            return "I couldn't find any files matching those criteria. Try broadening your search or checking the filename."

        try:
            samples = ", ".join([f.name for f in results[:3]])
            resp = await self._chain.ainvoke({
                "intent_summary": str(intent.active_filter_summary()),
                "count": len(results),
                "samples": samples
            })
            return resp.content
        except Exception:
            logger.exception("Response formatting failed")
            return f"I found {len(results)} files matching your search."

    def _get_system_prompt(self) -> str:
        return """
You are the conversational response layer for a Google Drive file search assistant.
Lead with the result, be efficient (1-2 sentences), and mention actual counts.
Do NOT list all filenames; result cards will handle that.
"""
