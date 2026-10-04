import json
import pytest

from app.services import public_lead_context


@pytest.mark.parametrize("intent,product,evidence,expected", [
    ("interest", "Personal Loan", "I need 10 lakhs", "Personal Loan"),
    ("information", "Personal Loan", "I need 10 lakhs", None),
    ("decline", "Personal Loan", "I need 10 lakhs", None),
    ("interest", "Imaginary Product", "I need 10 lakhs", None),
    ("interest", "Personal Loan", "previous interest", None),
])
def test_model_decision_requires_supported_product_and_current_evidence(monkeypatch, intent, product, evidence, expected):
    class Response:
        def raise_for_status(self): pass
        def json(self): return {"response": json.dumps({"intent": intent, "product": product, "evidence": evidence})}
    monkeypatch.setattr(public_lead_context.httpx, "post", lambda *args, **kwargs: Response())
    assert public_lead_context.contextual_product("I need 10 lakhs", [], ["Personal Loan"]) == expected


def test_followup_uses_own_session_and_saves_inferred_product(client, monkeypatch):
    from app.services import public_chat_session as service
    from app.db.session import SessionLocal
    from app.models import PublicLead

    seen = []
    def classify(message, history, products):
        seen.append(history)
        if message == "I need 10 lakhs" and any("personal loan" in item["content"].lower() for item in history):
            return "Personal Loan"
        return None
    monkeypatch.setattr(service, "contextual_product", classify)
    monkeypatch.setattr(service, "_answer", lambda *args: {"message": "General information.", "grounded": False, "sources": []})
    first = client.post("/api/public/chat", json={"message": "Tell me about personal loans"}).json()
    assert first["contact_step"] == ""
    session = first["session_id"]
    response = client.post("/api/public/chat", json={"message": "I need 10 lakhs", "session_id": session}).json()
    assert response["contact_step"] == "name" and "personal loan" in response["message"]
    other = client.post("/api/public/chat", json={"message": "I need 10 lakhs"}).json()
    assert other["contact_step"] == "" and seen[-1] == []
    for message in ("Asha Sharma", "9876543210", "asha@example.com"):
        client.post("/api/public/chat", json={"message": message, "session_id": session})
    with SessionLocal() as db:
        assert db.query(PublicLead).one().product == "Personal Loan"
