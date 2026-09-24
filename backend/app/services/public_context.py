"""Local conversation understanding for the public assistant."""

import json
import logging
import re
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.services.public_prompt import PUBLIC_SYSTEM, conversation_context

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class Understanding:
    intent: str
    query: str
    reply: str = ""

def understand(message: str, history: list | None = None) -> Understanding | None:
    """Classify the turn and resolve references using recent public chat context."""
    earlier = conversation_context(history)
    prompt = (
        "You route messages for a public banking assistant. Read the current message and recent visitor messages. "
        "Return JSON only with keys intent, query, reply. intent must be one of greeting, social, capabilities, banking, clarify. "
        "Use social for pleasantries or thanks. Use capabilities for asking what the assistant can do. "
        "Use banking for a real banking question. For banking, rewrite short follow-ups as one complete search query "
        "using the most recent relevant banking topic. Preserve the current question's meaning and do not invent facts. "
        "If the current message starts a new topic, use it alone. For other intents, query is the current message.\n"
        "For greeting or social, reply is a warm, relevant response under 45 words, with no bank facts. "
        "For capabilities, reply briefly explains general banking help and sign-in for personal account access. "
        "For banking, reply must be empty; query must retain all substantive questions, including a request for a simpler explanation. "
        "If the visitor asks to explain or simplify a previous answer, use that answer and its topic to write the query. "
        "Use clarify only if a missing subject cannot be resolved from history; reply asks one short question. "
        "Examples: 'thanks, what documents are needed?' is banking, not social. "
        "'That really helped, appreciate it!' is social. 'How are you and what can you help with?' is capabilities.\n"
        f"Recent conversation: {json.dumps(earlier, ensure_ascii=False)}\n"
        f"Current message: {json.dumps(message[:500], ensure_ascii=False)}\nJSON:"
    )
    try:
        response = httpx.post(
            f"{settings.ollama_base_url.rstrip('/')}/api/generate",
            json={"model": settings.ollama_model, "system": PUBLIC_SYSTEM, "prompt": prompt, "format": "json", "stream": False, "options": {"temperature": 0, "num_predict": 240}},
            timeout=min(settings.ollama_timeout_seconds, 20),
        )
        response.raise_for_status()
        result = json.loads(response.json()["response"])
        intent = result.get("intent")
        query = result.get("query")
        # Social turns do not need a retrieval query. Some models correctly
        # leave it empty even when their intent and conversational reply are valid.
        if intent in {"greeting", "social", "capabilities", "clarify"} and (not isinstance(query, str) or not query.strip()):
            query = message[:500]
        if intent in {"greeting", "social", "capabilities", "banking", "clarify"} and isinstance(query, str) and 0 < len(query) <= 500:
            current = " ".join(message.lower().split())
            asks_capabilities = bool(re.search(r"\b(?:services?|help|capabilities)\b", current) and re.search(r"\b(?:you|your|provide|offer|do)\b", current) and not re.search(r"\b(?:loan|card|deposit|account|branch|atm|rights|policy)\b", current))
            substantive = bool(re.search(r"\b(?:loans?|cards?|deposits?|accounts?|branch|atm|rights|policy|policies|documents?|eligibility|rates?|fees?|charges?|compensation|cheques?|transactions?|payments?|interest|kyc)\b", current))
            if asks_capabilities:
                intent = "capabilities"
            elif intent in {"greeting", "social", "capabilities"} and substantive:
                intent = "banking"
                query = message
            reply = result.get("reply", "")
            if not isinstance(reply, str) or len(reply) > 500 or re.search(r"\d|\b(?:otp|pin|cvv|password)\b", reply, re.I):
                reply = ""
            return Understanding(intent, query.strip(), reply)
    except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError) as exc:
        logger.warning("Local public context understanding unavailable: %s", exc)
    return None
