"""
LLM-powered intent extraction with production prompt engineering.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from backend.config import settings
from backend.schemas.intent import SearchIntent
from backend.schemas.session import SessionState

logger = logging.getLogger(__name__)


class IntentExtractor:
    """
    Extracts structured SearchIntent from user messages.
    Uses Groq for high-speed, low-latency extraction.
    """

    def __init__(self):
        self._llm = ChatGroq(
            api_key=settings.groq_api_key.get_secret_value(),
            model_name="llama3-70b-8192",
            temperature=0,
            model_kwargs={"response_format": {"type": "json_object"}}
        )
        self._prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt()),
            ("user", "User message: {user_message}\n\nToday's date: {today}")
        ])
        self._chain = self._prompt | self._llm

    async def extract(self, user_message: str, session: SessionState) -> SearchIntent:
        try:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            resp = await self._chain.ainvoke({
                "user_message": user_message,
                "today": today
            })
            
            data = json.loads(resp.content)
            # Ensure raw_query is preserved
            data["raw_query"] = user_message
            
            return SearchIntent(**data)
        except Exception:
            logger.exception("Intent extraction failed")
            return None

    def _get_system_prompt(self) -> str:
        return """
You are a precision structured-output extraction engine for a Google Drive search assistant.
Extract the user's search intent into the specified JSON format.

RULES:
- filename_query: Core subject keywords.
- search_in_content: Set to true if the user implies searching INSIDE the file.
- date_filter: Resolve relative terms (today, last week, etc.)
- followup: Identify if this message continues from a previous context.
- ambiguity: Flag if the query is too vague to search.

Return ONLY the JSON object.
"""
