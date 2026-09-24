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


def test_external_lead_saves_requested_amount_and_requirement(client, admin_headers):
    from app.db.session import SessionLocal
    from app.models import PublicLead

    first = client.post("/api/public/chat", json={"message": "I need a home loan of 50 lakh rupees within 6 months"}).json()
    session = first["session_id"]
    for value in ("Asha Sharma", "9876543210", "asha@example.com"):
        final = client.post("/api/public/chat", json={"message": value, "session_id": session}).json()
    assert final["contact_step"] == ""
    with SessionLocal() as db:
        lead = db.query(PublicLead).one()
        assert lead.requested_amount == 5_000_000
        assert "50 lakh" in lead.enquiry
        assert lead.details["timeline_as_shared"] == "within 6 months"
        assert lead.details["amount_as_shared"] == "50 lakh rupees"
    row = client.get("/api/bank/public-leads", headers=admin_headers).json()[0]
    assert row["requested_amount"] == 5_000_000 and "50 lakh" in row["enquiry"]


def test_phone_only_is_saved_when_visitor_skips_email(client, monkeypatch):
    from app.services import public_chat_session as service
    from app.db.session import SessionLocal
    from app.models import PublicLead

    monkeypatch.setattr(service, "_answer", lambda *args: {"message": "General loan information.", "grounded": False, "sources": []})
    first = client.post("/api/public/chat", json={"message": "I need a personal loan of 10 lakhs"}).json()
    session = first["session_id"]
    phone = client.post("/api/public/chat", json={"message": "9876543210", "session_id": session}).json()
    assert phone["contact_step"] == "email" and "email" in phone["message"].lower()
    with SessionLocal() as db:
        lead = db.query(PublicLead).one()
        assert lead.phone == "9876543210" and lead.email == ""
        assert lead.requested_amount == 1_000_000
        assert lead.status == "Contact details incomplete"
    skipped = client.post("/api/public/chat", json={"message": "Skip", "session_id": session}).json()
    assert skipped["contact_step"] == "" and "saved" in skipped["message"].lower()
    with SessionLocal() as db:
        assert db.query(PublicLead).count() == 1


def test_email_first_is_saved_and_bot_asks_for_phone(client, monkeypatch):
    from app.services import public_chat_session as service
    from app.db.session import SessionLocal
    from app.models import PublicLead

    monkeypatch.setattr(service, "_answer", lambda *args: {"message": "General information.", "grounded": False, "sources": []})
    first = client.post("/api/public/chat", json={"message": "I want a home loan"}).json()
    session = first["session_id"]
    email = client.post("/api/public/chat", json={"message": "asha@example.com", "session_id": session}).json()
    assert email["contact_step"] == "phone" and "phone" in email["message"].lower()
    client.post("/api/public/chat", json={"message": "Skip", "session_id": session})
    with SessionLocal() as db:
        lead = db.query(PublicLead).one()
        assert lead.email == "asha@example.com" and lead.phone == ""
        assert lead.status == "Contact details incomplete"


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
