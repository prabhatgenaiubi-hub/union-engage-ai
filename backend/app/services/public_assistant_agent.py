"""Dedicated, read-only agent for the unauthenticated login-page assistant."""

import re

from sqlalchemy.orm import Session

from app.services.knowledge import knowledge_retriever
from app.services.pdf_knowledge import retrieve_pdf_chunks
from app.services.public_answers import UNKNOWN, PUBLIC_CAPABILITIES, broad_help, general_answer, is_general_question, pdf_answer, generated_answer, policy_answer, supports_question_focus
from app.services.public_context import understand
from app.services.public_conversation import social_reply
from app.services.public_retrieval import normalize, terms as query_terms, definition_term, definition_excerpt, rank_passages
from app.schemas.api import PublicChatTurn


class PublicAssistantAgent:
    """Routes a public request, searches approved knowledge, and returns a bounded answer."""

    @staticmethod
    def _reply(message: str, grounded: bool = False, sources: list[dict] | None = None) -> dict:
        return {"message": message, "grounded": grounded, "sources": sources or []}

    def respond(self, db: Session, message: str, history: list[PublicChatTurn] | None = None) -> dict:
        normalized = " ".join(message.lower().split())
        explanation_request = bool(re.search(r"\b(?:simpler|simplify|explain again|explain that|explain it|more simply|do not understand|don't understand|didn't understand)\b", normalized))
        conversational_reply = social_reply(message)
        if conversational_reply and not (explanation_request and history):
            return self._reply(conversational_reply)
        private_query = bool(re.search(r"\b(?:my|mine)\b.{0,40}\b(?:account|balance|transaction|statement|card|loan|application|service request|ticket)\b", normalized)) or any(phrase in normalized for phrase in ("account number", "transaction status"))
        if private_query:
            return self._reply("For privacy and security, please sign in to ask about your account, balance, transactions, applications, cards, or service requests.")
        if re.fullmatch(r"(?:hi+|hello+|hey+|namaste|namaskar)[,!. ]+how (?:are you|is it going|have you been)[!?., ]*", normalized):
            return self._reply("Hello! I'm here and ready to help. What banking question can I answer for you?")
        if re.fullmatch(r"(?:hi+|hello+|hey+|good (?:morning|afternoon|evening)|namaste|namaskar)[!., ]*", normalized):
            return self._reply("Hello! I can help with general questions about Union Bank accounts, cards, loans, deposits and banking services. What would you like to know?")
        help_response = broad_help(message)
        if help_response:
            return self._reply(help_response)
        understanding = understand(message, history)
        has_banking_terms = bool(re.search(r"\b(?:atm|accounts?|balance|cards?|loans?|deposits?|cheques?|transactions?|re.?imburse|compensat\w*|interest|payments?|branch|rights|polic\w*|documents?|eligibility|rates?|fees?|charges?)\b", normalized))
        if understanding and understanding.intent == "greeting" and not has_banking_terms and not is_general_question(message):
            if not explanation_request:
                return self._reply(understanding.reply or "Hello! What banking question can I help you with today?")
        if understanding and understanding.intent == "social" and not has_banking_terms and not is_general_question(message):
            if not explanation_request:
                return self._reply(understanding.reply or "I'm here to help. What would you like to know?")
        if understanding and understanding.intent == "capabilities" and not has_banking_terms and not is_general_question(message):
            return self._reply(understanding.reply or PUBLIC_CAPABILITIES)
        if understanding and understanding.intent == "clarify" and understanding.reply and not has_banking_terms and not history:
            return self._reply(understanding.reply)
        if re.fullmatch(r"(?:hi+|hello+|hey+|good (?:morning|afternoon|evening)|namaste|namaskar)[!., ]*", normalized):
            return self._reply("Hello! I can help with general questions about Union Bank accounts, cards, loans, deposits and banking services. What would you like to know?")
        if re.fullmatch(r"(?:how are you|how's it going|thank you|thanks)[!?., ]*", normalized):
            return self._reply("I'm here and ready to help. What banking question can I answer for you?")

        query = understanding.query if understanding and understanding.intent == "banking" and not is_general_question(message) else message
        # A named topic or definition is a new question, not a reference to the
        # earlier conversation. Do not let the intent model replace that topic.
        if definition_term(message) and not re.search(r"\b(?:it|that|this|those|they|them)\b", normalized):
            query = message
        query = re.sub(r"\bconsumers?\b", "customer", query, flags=re.I)
        earlier_questions = [turn.content for turn in reversed(history or []) if turn.role == "user"]
        if explanation_request and history:
            previous = next((text for text in earlier_questions if not social_reply(text) and not re.search(r"\b(?:simpler|simplify|explain again|explain that)\b", text, re.I)), None)
            if previous and (query == message or not understanding or understanding.intent != "banking"):
                query = f"{previous} Explain in simpler words."
        recent_atm = next((text for text in earlier_questions if re.search(r"\b(?:atm|cash not dispensed|failed transaction)\b", text, re.I)), None)
        if recent_atm and not re.search(r"\b(?:loans?|deposits?|credit cards?|home|personal)\b", normalized) and re.search(r"\b(?:amount|re.?imburse|compensat|eligible|debited|cash not dispensed)\b", normalized):
            query = f"failed ATM transaction cash not dispensed wrong debit compensation {recent_atm} {message}"
        elif query == message and len(re.findall(r"\w+", message)) <= 5 and re.search(r"\b(?:it|that|this|those|they|them)\b", normalized):
            previous = next((text for text in earlier_questions if len(text.split()) > 3), None)
            if previous:
                query = f"{previous} {message}"
        if bool(re.search(r"\b(?:my|mine)\b.{0,40}\b(?:account|balance|transaction|statement|card|loan|application|service request|ticket)\b", query.lower())):
            return self._reply("For privacy and security, please sign in to ask about your account, balance, transactions, applications, cards, or service requests.")

        if "atm" in query.lower() and re.search(r"\b(?:failed|cash not dispensed|wrongly debited|compensat|re.?imburse)\b", query, re.I):
            policy_matches = retrieve_pdf_chunks(db, "failed ATM transactions amount wrongfully debited compensation T+5 days Rs.100 cash not dispensed", audience="customer", limit=8)
            for match in policy_matches:
                answer = policy_answer(query, match["content"], message)
                if answer:
                    return self._reply(answer, True, [{"title": match["title"], "page": match["page"], "type": "pdf"}])

        # Search the same approved PDF and article stores as the signed-in assistant.
        # A wider candidate pool lets the public agent find relevant pages beyond the
        # first few vector hits; only the best evidence is sent to the local model.
        articles = knowledge_retriever.search(db, query, limit=8)
        pdf_matches = retrieve_pdf_chunks(db, query, audience="customer", limit=12)
        if is_general_question(message):
            return self._reply(general_answer(message) or PUBLIC_CAPABILITIES)
        terms = query_terms(query)
        articles = [article for article in articles if supports_question_focus(message, article.content) and terms & set(re.findall(r"[a-z]{4,}", article.title.lower())) and len(terms & set(re.findall(r"[a-z]{4,}", (article.title + " " + article.content).lower()))) >= min(2, len(terms))]
        pdf_matches = rank_passages(query, [match for match in pdf_matches if supports_question_focus(message, match["content"])])
        for item in pdf_matches:
            exact_definition = definition_excerpt(query, item["content"])
            if exact_definition and not explanation_request:
                return self._reply(exact_definition, True, [{"title": item["title"], "page": item["page"], "type": "pdf"}])
            policy_summary = policy_answer(normalize(query), item["content"], message)
            if policy_summary and not explanation_request:
                return self._reply(policy_summary, True, [{"title": item["title"], "page": item["page"], "type": "pdf"}])
        if pdf_matches and (not articles or pdf_matches[0]["score"] >= 0.70):
            selected = pdf_matches[:4]
            for item in selected:
                policy_summary = policy_answer(query, item["content"], message)
                if policy_summary and not explanation_request:
                    return self._reply(policy_summary, True, [{"title": item["title"], "page": item["page"], "type": "pdf"}])
            context = "\n\n".join(f"[{item['title']}, page {item['page']}] {item['content']}" for item in selected)
            answer = generated_answer(query, context, history)
            if answer:
                return self._reply(answer, True, [{"title": item["title"], "page": item["page"], "type": "pdf"} for item in selected])
        if articles:
            article = articles[0]
            answer = generated_answer(query, article.content, history) or article.content.strip()
            return self._reply(answer, True, [{"title": article.title, "page": None, "type": "article"}])

        pdf_result = pdf_answer(query, pdf_matches)
        if pdf_result:
            answer, match = pdf_result
            return self._reply(answer, True, [{"title": match["title"], "page": match["page"], "type": "pdf"}])
        return self._reply(UNKNOWN)


public_assistant_agent = PublicAssistantAgent()
