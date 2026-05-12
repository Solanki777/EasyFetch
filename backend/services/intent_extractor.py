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
            ("system", self._get_system_prompt()),
            ("user", "User message: {user_message}\n\nToday's date: {today}")
        ])

        self._chain = self._prompt | self._llm

    async def extract(
        self,
        user_message: str,
        session: SessionState
    ) -> SearchIntent | None:
        """
        Extracts search intent with defensive validation and detailed logging.
        """
        try:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            logger.debug(f"Extracting intent for message: '{user_message}'")
            
            # Debug info for session
            if session and session.history:
                logger.debug(f"Conversation history depth: {len(session.history)}")

            resp = await self._chain.ainvoke({
                "user_message": user_message,
                "today": today
            })

            # Defensive parsing
            try:
                data = json.loads(resp.content)
            except json.JSONDecodeError as je:
                logger.error(f"LLM returned invalid JSON: {resp.content}")
                return None

            # Preserve original query
            data["raw_query"] = user_message

            # Log extracted data for debugging
            logger.info("===== EXTRACTED INTENT =====")
            logger.info(json.dumps(data, indent=2))

            # Validate with Pydantic
            try:
                intent = SearchIntent(**data)
                
                # Debug specific logic results
                if intent.mime_types:
                    logger.debug(f"Detected MIME types: {intent.mime_types}")
                if intent.filename_query:
                    logger.debug(f"Filename query: '{intent.filename_query}'")
                if intent.followup.is_followup:
                    logger.debug(f"Follow-up detected: {intent.followup.action}")
                
                return intent
            except Exception as ve:
                logger.error(f"Pydantic validation failed for LLM output: {ve}")
                logger.error(f"Raw data: {data}")
                return None

        except Exception as e:
            logger.exception(f"Unexpected error during intent extraction: {e}")
            return None

    def _get_system_prompt(self) -> str:
        return """
You are a precision structured-output extraction engine for a Google Drive search assistant.
Your goal is to convert natural language queries into a structured 'SearchIntent' JSON object.

### CORE RULES:

1. **Output Format**: Return ONLY valid JSON matching the schema.
2. **filename_query**: 
   - Extract only specific keywords for file names.
   - STRIP vague verbs and filler words: "show", "find", "search", "give", "list", "files", "documents", "stuff", "get", "me".
   - If the user says "show all files" or "list everything", set filename_query to null.
3. **MIME Type Detection**:
   - PDFs -> ["application/pdf"]
   - Images -> ["image/jpeg", "image/png", "image/gif", "image/svg+xml", "image/webp"]
   - Folders/Directories -> ["application/vnd.google-apps.folder"]
   - Spreadsheets (Excel/CSV/Sheets) -> ["application/vnd.google-apps.spreadsheet", "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "text/csv"]
   - Docs (Word/Google Docs) -> ["application/vnd.google-apps.document", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
   - Presentations (PPT/Slides) -> ["application/vnd.google-apps.presentation", "application/vnd.ms-powerpoint", "application/vnd.openxmlformats-officedocument.presentationml.presentation"]
   - Archives (Zip/Tar) -> ["application/zip", "application/x-tar"]
4. **FullText Search**:
   - Detect phrases like "containing", "contains", "mentioning", "talking about", "inside".
   - Set search_in_content = true and populate fulltext_query.
5. **Date Filters**:
   - Resolve relative dates using today's date.
   - Values: "today", "yesterday", "this_week", "last_week", "this_month", "last_month", "this_year".
6. **Sorting**:
   - "latest", "newest", "recent", "newly uploaded" -> set sort.field = "createdTime" or "modifiedTime" and sort.direction = "desc".
7. **Follow-ups**:
   - Detect if the message is a refinement of a previous search (e.g., "now only PDFs", "from last week").
   - Set followup.is_followup = true and appropriate action.
8. **Ambiguity**:
   - If the query is too vague (e.g., "find stuff"), set ambiguity.needs_clarification = true.

### SCHEMA STRUCTURE:
{{
  "filename_query": string | null,
  "fulltext_query": string | null,
  "search_in_content": boolean,
  "mime_types": string[],
  "file_extensions": string[],
  "date_filter": {{
    "relative": "today" | "yesterday" | "this_week" | "last_week" | "this_month" | "last_month" | "this_year" | null,
    "field": "modifiedTime" | "createdTime"
  }} | null,
  "sort": {{
    "field": "modifiedTime" | "createdTime" | "name" | "relevance",
    "direction": "asc" | "desc"
  }},
  "followup": {{
    "is_followup": boolean,
    "action": string | null
  }},
  "ambiguity": {{
    "needs_clarification": boolean,
    "clarification_question": string | null
  }}
}}

### EXAMPLES:

- "show pdf files" -> {{ "filename_query": null, "mime_types": ["application/pdf"] }}
- "find spreadsheets about revenue" -> {{ "filename_query": "revenue", "mime_types": ["application/vnd.google-apps.spreadsheet", ...], "followup": {{"is_followup": false}} }}
- "latest uploaded images" -> {{ "mime_types": ["image/jpeg", ...], "sort": {{"field": "createdTime", "direction": "desc"}} }}
- "files containing budget" -> {{ "search_in_content": true, "fulltext_query": "budget" }}
"""

