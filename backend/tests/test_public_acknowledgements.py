import pytest

from app.services.public_assistant_agent import public_assistant_agent


@pytest.mark.parametrize("message", ["Okay Thanks.", "Okay, thanks!", "Thanks", "Thank you very much", "Got it, thank you", "Thanks for your help"])
def test_acknowledgement_does_not_search_knowledge(monkeypatch, message):
    from app.services import public_assistant_agent as module

    def unexpected(*args, **kwargs):
        raise AssertionError("Acknowledgments should not call the model or search knowledge")
    monkeypatch.setattr(module, "understand", unexpected)
    monkeypatch.setattr(module.knowledge_retriever, "search", unexpected)
    monkeypatch.setattr(module, "retrieve_pdf_chunks", unexpected)
    answer = public_assistant_agent.respond(None, message)
    assert "welcome" in answer["message"] and answer["sources"] == []


def test_thanks_with_banking_question_still_retrieves(monkeypatch):
    from app.services import public_assistant_agent as module
    seen = []
    monkeypatch.setattr(module, "understand", lambda *args: None)
    monkeypatch.setattr(module.knowledge_retriever, "search", lambda db, query, limit: seen.append(query) or [])
    monkeypatch.setattr(module, "retrieve_pdf_chunks", lambda *args, **kwargs: [])
    public_assistant_agent.respond(None, "Okay thanks, what are the customer rights?")
    assert seen == ["Okay thanks, what are the customer rights?"]


@pytest.mark.parametrize("message", ["Good night!", "Have a nice day", "That was very helpful", "Sorry about that", "One moment", "Are you there?", "I'm fine, thanks", "Okay great thanks", "Nothing else", "I don't understand"])
def test_everyday_chat_gets_a_friendly_reply(message, monkeypatch):
    from app.services import public_assistant_agent as module
    def unexpected(*args, **kwargs):
        raise AssertionError("Everyday small talk should not search bank documents")
    monkeypatch.setattr(module, "understand", unexpected)
    answer = public_assistant_agent.respond(None, message)
    assert answer["message"] and "couldn't find" not in answer["message"]
    assert not answer["grounded"] and answer["sources"] == []


def test_small_talk_during_contact_collection_is_not_a_name(client, monkeypatch):
    from app.services import public_chat_session as service
    from app.db.session import SessionLocal
    from app.models import PublicConversation
    monkeypatch.setattr(service, "contextual_product", lambda *args: "Personal Loan")
    first = client.post("/api/public/chat", json={"message": "I want a personal loan"}).json()
    response = client.post("/api/public/chat", json={"message": "Thanks for your help", "session_id": first["session_id"]}).json()
    assert "welcome" in response["message"] and response["contact_step"] == "name"
    with SessionLocal() as db:
        assert not db.query(PublicConversation).filter_by(session_token=first["session_id"]).one().contact_name
