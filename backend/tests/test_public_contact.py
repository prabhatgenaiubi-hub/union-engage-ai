from app.services.public_chat_session import detect_product_interest
import pytest


@pytest.mark.parametrize("message,product", [
    ("I have need of personal loan.", "Personal Loan"),
    ("I have need of personal loan of 10 lakhs.", "Personal Loan"),
    ("I have need of home loan of 50 lakh rupees.", "Home Loan"),
    ("I have a requirement for a personal loan", "Personal Loan"),
    ("I require a home loan", "Home Loan"),
])
def test_loan_requirement_prompts_for_optional_contact(client, message, product):
    assert detect_product_interest(message) == product
    answer = client.post("/api/public/chat", json={"message": message}).json()
    assert answer["contact_step"] == "name" and "optional" in answer["message"]


def test_repeated_requirements_are_not_saved_as_customer_name(client):
    from app.db.session import SessionLocal
    from app.models import PublicConversation

    first = client.post("/api/public/chat", json={"message": "I have need of personal loan."}).json()
    for message in ("I have need of personal loan of 10 lakhs.", "I have need of home loan of 50 lakh rupees."):
        answer = client.post("/api/public/chat", json={"message": message, "session_id": first["session_id"]}).json()
        assert answer["contact_step"] == "name"
    with SessionLocal() as db:
        conversation = db.query(PublicConversation).filter_by(session_token=first["session_id"]).one()
        assert not conversation.contact_name and conversation.pending_product == "Home Loan"
    answer = client.post("/api/public/chat", json={"message": "Skip", "session_id": first["session_id"]}).json()
    assert "home loan" in answer["message"] and "application process" in answer["message"]
    assert "processing charge" not in answer["message"]


def test_information_and_declined_interest_are_not_leads():
    for message in ("Hello", "What documents do I need for a home loan?", "I am not interested in a home loan", "Don't call me about a credit card"):
        assert detect_product_interest(message) is None
    assert detect_product_interest("Please call me about a home loan") == "Home Loan"


def test_optional_contact_can_be_interrupted_and_requested_later(client, monkeypatch):
    from app.services import public_chat_session as service
    from app.db.session import SessionLocal
    from app.models import PublicConversation, PublicLead

    monkeypatch.setattr(service, "_answer", lambda db, conversation, question: {"message": "Answer to: " + question, "grounded": False, "sources": []})
    first = client.post("/api/public/chat", json={"message": "I want a home loan"}).json()
    session = first["session_id"]
    assert first["contact_step"] == "name" and "optional" in first["message"]

    def send(message):
        return client.post("/api/public/chat", json={"message": message, "session_id": session}).json()

    assert send("Asha Sharma")["contact_step"] == "phone"
    answer = send("What documents do I need?")
    assert answer["contact_step"] == "" and "Answer to: What documents" in answer["message"]
    assert send("I want a credit card")["contact_step"] == ""
    with SessionLocal() as db:
        conversation = db.query(PublicConversation).filter_by(session_token=session).one()
        assert conversation.contact_declined and not conversation.contact_name
        assert db.query(PublicLead).count() == 0
    assert send("Please call me about a home loan")["contact_step"] == "name"
    assert send("No thank you")["contact_step"] == ""
