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
            api_key=settings.groq_api_key,
            model_name=settings.llm_model,
            temperature=0,
            model_kwargs={
                "response_format": {"type": "json_object"}
            }
        )

        self._prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                self._get_system_prompt()
            ),
            (
                "user",
                "User message: {user_message}\n\nToday's date: {today}"
            )
        ])

        self._chain = self._prompt | self._llm

    async def extract(
        self,
        user_message: str,
        session: SessionState
    ) -> SearchIntent:

        try:
            today = datetime.now(
                timezone.utc
            ).strftime("%Y-%m-%d")

            print(
                f"--- Calling Groq LLM for message: '{user_message}'",
                flush=True
            )

            resp = await self._chain.ainvoke({
                "user_message": user_message,
                "today": today
            })

            data = json.loads(resp.content)

            # Preserve original query
            data["raw_query"] = user_message

            print(
                "\n===== EXTRACTED INTENT =====",
                flush=True
            )

            print(
                json.dumps(data, indent=2),
                flush=True
            )

            return SearchIntent(**data)

        except Exception as e:

            print(
                f"\n!!! Intent extraction ERROR: {e}",
                flush=True
            )

            logger.exception(
                "Intent extraction failed"
            )

            return None

    def _get_system_prompt(self) -> str:

        return """
You are a precision structured-output extraction engine
for a Google Drive search assistant.

Extract the user's search intent into structured JSON.

RULES:

- filename_query:
  ONLY important filename keywords.

- search_in_content:
  true if the user wants to search INSIDE file contents.

- date_filter:
  resolve relative dates like:
  today,
  last week,
  this month.

- followup MUST ALWAYS be an object:

{{
  "is_followup": boolean,
  "action": string | null,
  "open_file_index": integer | null
}}

- ambiguity MUST ALWAYS be an object:

{{
  "needs_clarification": boolean,
  "clarification_question": string | null
}}

SPECIAL CASES:

If the user says:
- "show all files"
- "show everything"
- "list all"
- "list everything"
- "give me all files"

Then:
- filename_query = null
- do NOT generate restrictive keywords.

Do NOT use words like:
- all
- everything
- files

as filename keywords.

If the user asks for:
- PDFs → detect PDF mime type
- folders → detect folder mime type
- images → detect image mime types
- spreadsheets → detect spreadsheet mime types

EXAMPLE RESPONSE:

{{
  "filename_query": null,
  "search_in_content": false,
  "date_filter": null,

  "followup": {{
    "is_followup": false,
    "action": null,
    "open_file_index": null
  }},

  "ambiguity": {{
    "needs_clarification": false,
    "clarification_question": null
  }}
}}

Return ONLY valid JSON.
"""
