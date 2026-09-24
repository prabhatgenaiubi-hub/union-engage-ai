import json
import pytest
from types import SimpleNamespace

from app.services.public_context import Understanding


@pytest.mark.parametrize("query", ["", None])
def test_social_reply_does_not_require_a_search_query(monkeypatch, query):
    from app.services import public_context
    class Response:
        def raise_for_status(self): pass
        def json(self):
            return {"response": json.dumps({"intent": "social", "query": query, "reply": "You're welcome! Glad I could help."})}
    monkeypatch.setattr(public_context.httpx, "post", lambda *args, **kwargs: Response())
    result = public_context.understand("Much appreciated, you made my day!")
    assert result.intent == "social" and "welcome" in result.reply


def test_context_uses_both_roles_and_accepts_unfamiliar_small_talk(monkeypatch):
    from app.services import public_context
    seen = []
    class Response:
        def raise_for_status(self): pass
        def json(self):
            return {"response": json.dumps({"intent": "social", "query": "Much appreciated, you made my day!", "reply": "Happy I could help!"})}
    def post(*args, **kwargs):
        seen.append(kwargs["json"])
        return Response()
    monkeypatch.setattr(public_context.httpx, "post", post)
    result = public_context.understand("Much appreciated, you made my day!", [SimpleNamespace(role="assistant", content="Here is the explanation.")])
    assert result.intent == "social" and result.reply == "Happy I could help!"
    assert "Here is the explanation." in seen[0]["prompt"]
    assert "public Union Bank" in seen[0]["system"]


def test_explanation_request_retrieves_previous_topic(monkeypatch):
    from app.services import public_assistant_agent as agent
    queries = []
    monkeypatch.setattr(agent, "understand", lambda *args: Understanding("social", "Please simplify"))
    monkeypatch.setattr(agent.knowledge_retriever, "search", lambda db, query, limit: queries.append(query) or [])
    monkeypatch.setattr(agent, "retrieve_pdf_chunks", lambda *args, **kwargs: [])
    history = [SimpleNamespace(role="user", content="What are customer rights?"), SimpleNamespace(role="assistant", content="The policy explains fair treatment and privacy.")]
    agent.public_assistant_agent.respond(None, "Please simplify", history)
    assert "customer rights" in queries[0] and "simpler" in queries[0]


def test_new_loan_question_does_not_reuse_old_atm_topic(monkeypatch):
    from app.services import public_assistant_agent as agent
    queries = []
    monkeypatch.setattr(agent, "understand", lambda message, history: Understanding("banking", message))
    monkeypatch.setattr(agent.knowledge_retriever, "search", lambda db, query, limit: queries.append(query) or [])
    monkeypatch.setattr(agent, "retrieve_pdf_chunks", lambda *args, **kwargs: [])
    history = [SimpleNamespace(role="user", content="Failed ATM compensation?")]
    agent.public_assistant_agent.respond(None, "What amount of home loan am I eligible for?", history)
    assert "ATM" not in queries[0] and "home loan" in queries[0]


def test_answer_generation_uses_history_but_requires_evidence(monkeypatch):
    from app.services import public_answers
    captured = []
    class Response:
        def raise_for_status(self): pass
        def json(self): return {"response": "INSUFFICIENT"}
    def post(*args, **kwargs):
        captured.append(kwargs["json"])
        return Response()
    monkeypatch.setattr(public_answers.httpx, "post", post)
    history = [SimpleNamespace(role="assistant", content="An earlier unverified statement.")]
    assert public_answers.generated_answer("Explain that", "Approved but unrelated passage.", history) is None
    assert "An earlier unverified statement." in captured[0]["prompt"]
    assert "never proof" in captured[0]["system"]
