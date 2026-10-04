import pytest

from app.services.public_context import Understanding
from app.services.public_retrieval import definition_excerpt, rank_passages


def test_general_capability_question_uses_local_model_after_search(client, monkeypatch):
    from app.services import public_assistant_agent as agent

    searched = []
    monkeypatch.setattr(agent.knowledge_retriever, "search", lambda db, query, limit: searched.append(query) or [])
    monkeypatch.setattr(agent, "retrieve_pdf_chunks", lambda db, query, audience, limit: searched.append(query) or [])
    monkeypatch.setattr(agent, "understand", lambda *args: Understanding("banking", "unrelated previous topic"))
    monkeypatch.setattr(agent, "general_answer", lambda question: "I can explain general banking services and policies. Please sign in for personal account details.")
    answer = client.post("/api/public/chat", json={"message": "what helps you provide?"}).json()
    assert searched == ["what helps you provide?"] * 2
    assert "general banking services" in answer["message"]
    assert answer["grounded"] is False and answer["sources"] == []


@pytest.mark.parametrize("question", [
    '“Composite Cash Credit” means?',
    'What is Composite Cash Credit?',
    'Define Composite Cash Credit',
])
def test_definitions_rank_above_incidental_mentions(question):
    definition = '“Composite Cash Credit” means a loan product with a cash credit limit and a savings module for farmers.'
    matches = [
        {"title": "Deposits", "page": 30, "score": .8, "content": "Interest on a composite cash credit account is described here. " * 4},
        {"title": "Deposits", "page": 29, "score": .6, "content": definition},
    ]
    ranked = rank_passages(question, matches)
    assert ranked[0]["page"] == 29
    assert "savings module for farmers" in definition_excerpt(question, ranked[0]["content"])
    assert definition_excerpt(question, '“Current Account” means a non-interest-bearing deposit.') is None


def test_public_agent_handles_synonym_and_topic_switch_in_one_session(client, monkeypatch):
    from app.services import public_assistant_agent as agent

    # Simulate the context model incorrectly carrying the previous topic forward.
    monkeypatch.setattr(agent, "understand", lambda *args: Understanding("banking", "customer rights"))
    monkeypatch.setattr(agent.knowledge_retriever, "search", lambda *args, **kwargs: [])
    queries = []
    rights = "Right to Fair Treatment. Right to Transparency, Fair and Honest Dealing. Right to Suitability. Right to Privacy. Right to Grievance Redressal and Compensation."
    definition = '“Composite Cash Credit” means a type of loan product having a cash credit limit with a savings module designed for farmers.'

    def retrieve(db, query, audience, limit):
        assert audience == "customer"
        queries.append(query)
        if "Composite" in query:
            return [{"title": "Deposit policy", "page": 29, "content": definition, "score": .61}]
        return [{"title": "Customer Rights Policy", "page": 3, "content": rights, "score": .68}]

    monkeypatch.setattr(agent, "retrieve_pdf_chunks", retrieve)
    def no_generation(*args, **kwargs):
        raise AssertionError("Complete policy evidence should not depend on model availability")
    monkeypatch.setattr(agent, "generated_answer", no_generation)
    first = client.post("/api/public/chat", json={"message": "what are the rights of consumer?"}).json()
    assert first["grounded"] and "fair treatment" in first["message"] and "privacy" in first["message"]
    second = client.post("/api/public/chat", json={"message": '“Composite Cash Credit” means?', "session_id": first["session_id"]}).json()
    assert second["grounded"] and "savings module" in second["message"]
    assert second["sources"][0]["page"] == 29
    assert "customer" in queries[0] and "Composite" in queries[-1]
