
"""
LLM-powered intent extraction with production prompt engineering.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from backend.config import settings
from backend.schemas.intent import SearchIntent
from backend.schemas.session import SessionState

logger = logging.getLogger(__name__)


class IntentExtractor:
    """
    Extracts structured SearchIntent from user messages.
    """

    def __init__(self):

        self._llm = ChatGroq(
            api_key=settings.groq_api_key,
            model_name=settings.llm_model,
            temperature=0,
            model_kwargs={
                "response_format": {
                    "type": "json_object"
                }
            }
        )

        self._prompt = ChatPromptTemplate.from_messages([

            (
                "system",
                self._get_system_prompt()
            ),

            (
                "user",
                (
                    "User message: {user_message}\n\n"
                    "Today's date: {today}"
                )
            )
        ])

        self._chain = (
            self._prompt
            | self._llm
        )

    async def extract(
        self,
        user_message: str,
        session: SessionState
    ) -> SearchIntent | None:
        """
        Extract search intent from natural language.
        """

        try:

            today = datetime.now(
                timezone.utc
            ).strftime("%Y-%m-%d")

            logger.info(
                f"Extracting intent: {user_message}"
            )

            if session and session.history:

                logger.debug(
                    f"History size: "
                    f"{len(session.history)}"
                )

            resp = await self._chain.ainvoke({
                "user_message": user_message,
                "today": today
            })

            logger.debug(
                f"Raw LLM output: {resp.content}"
            )

            try:

                data = json.loads(
                    resp.content
                )

            except json.JSONDecodeError:

                logger.error(
                    "Invalid JSON from LLM"
                )

                logger.error(resp.content)

                return None

            # Preserve original query
            data["raw_query"] = user_message

            logger.info(
                "===== EXTRACTED INTENT ====="
            )

            logger.info(
                json.dumps(
                    data,
                    indent=2
                )
            )

            try:

                intent = SearchIntent(
                    **data
                )

                # Safety fix:
                # Never allow accidental fullText search
                # unless explicitly requested.

                explicit_content_terms = [
                    "inside file",
                    "inside files",
                    "inside document",
                    "inside documents",
                    "search within",
                    "within files",
                    "content search",
                    "text inside",
                    "mentioned in",
                    "containing text",
                ]

                lowered = user_message.lower()

                explicit = any(
                    t in lowered
                    for t in explicit_content_terms
                )

                if not explicit:

                    intent.search_in_content = False

                    if (
                        intent.fulltext_query
                        and not explicit
                    ):
                        intent.fulltext_query = None

                # Rich observability logging
                import json as json_lib
                logger.info("=" * 40)
                logger.info("INTENT EXTRACTION COMPLETE")
                logger.info(f"  Intent: {json_lib.dumps(intent.model_dump(), indent=2)}")
                logger.info("=" * 40)

                return intent

            except Exception as ve:

                logger.exception(
                    "Pydantic validation failed"
                )

                logger.error(str(ve))

                logger.error(data)

                return None

        except Exception as e:

            logger.exception(
                f"Intent extraction failed: {e}"
            )

            return None

    def _get_system_prompt(self) -> str:

        return """
You are a universal intelligent file search engine for Google Drive.
Your goal is to extract structured search intent from natural language.

Return ONLY valid JSON.

━━━━━━━━━━━━━━━━━━━━
1. UNIVERSAL CATEGORIES (mime_types)
━━━━━━━━━━━━━━━━━━━━
Map natural language terms to these categories or specific MIME types:
- "images", "photos", "pictures" -> CATEGORY: images
- "spreadsheets", "excel", "sheets", "csv" -> CATEGORY: spreadsheets
- "documents", "word", "docs", "pdfs" -> CATEGORY: documents
- "presentations", "slides", "powerpoint" -> CATEGORY: presentations
- "archives", "zip", "rar", "7z" -> CATEGORY: archives
- "code", "scripts", "python", "javascript", "json" -> CATEGORY: code
- "video", "movies", "mp4", "mov" -> CATEGORY: video
- "audio", "music", "mp3" -> CATEGORY: audio
- "folders" -> application/vnd.google-apps.folder

━━━━━━━━━━━━━━━━━━━━
2. SMART FILENAME QUERY (filename_query)
━━━━━━━━━━━━━━━━━━━━
- Extract the core subject.
- STRIP extension words if you already set the MIME/Extension filter. 
  Example: "find sekiro.jpg" -> filename_query: "sekiro", file_extensions: ["jpg"]
- STRIP category words. 
  Example: "show me project images" -> filename_query: "project", mime_types: ["image/jpeg", "image/png"...]
- REMOVE fillers: "show", "find", "get", "me", "list", "files", "stuff".

━━━━━━━━━━━━━━━━━━━━
3. CONTENT SEARCH (search_in_content)
━━━━━━━━━━━━━━━━━━━━
- ONLY true if user says: "inside", "content", "mentioned in", "text within".
- Otherwise FALSE (default).

━━━━━━━━━━━━━━━━━━━━
4. DATE FILTERS (date_filter)
━━━━━━━━━━━━━━━━━━━━
- today, yesterday, this_week, last_week, this_month, last_month, this_year.

━━━━━━━━━━━━━━━━━━━━
5. FOLLOW-UP & AMBIGUITY
━━━━━━━━━━━━━━━━━━━━
- followup.is_followup: true if this refines previous results.
- ambiguity.needs_clarification: true if query is empty or nonsense.

Return ONLY valid JSON.
"""
