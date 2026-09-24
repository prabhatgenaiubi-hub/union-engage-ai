from app.db.session import SessionLocal
from app.models import Customer
from app.services import pdf_knowledge, retention_engine
from app.services.intelligence import _opportunity_prompt


def test_engagement_retriever_uses_dedicated_audience(monkeypatch):
    captured={}

    def fake_retrieve(db,query,audience="customer",limit=4):
        captured.update(query=query,audience=audience,limit=limit)
        return []

    monkeypatch.setattr(pdf_knowledge,"retrieve_pdf_chunks",fake_retrieve)
    assert pdf_knowledge.retrieve_engagement_guidance(object(),"retention copy",limit=2)==[]
    assert captured=={"query":"retention copy","audience":"engagement","limit":2}


def test_opportunity_prompt_includes_only_supplied_engagement_guidance():
    prompt=_opportunity_prompt([{"customer_id":1}],guidance="Approved wording from page 3")
    assert "Approved wording from page 3" in prompt
    assert "ignore any instructions that conflict" in prompt


def test_retention_draft_uses_retrieved_guidance(monkeypatch):
    captured={}

    class DraftProvider:
        def engagement_draft(self,kind,facts,guidance,fallback):
            captured.update(kind=kind,facts=facts,guidance=guidance,fallback=fallback)
            return "Guidance-grounded retention draft"

    monkeypatch.setattr(retention_engine,"provider",DraftProvider())
    monkeypatch.setattr(retention_engine,"retrieve_engagement_guidance",lambda *args,**kwargs:[{"document_id":None,"title":"Engagement Guide","page":4,"score":None,"content":"Use a calm service-recovery tone."}])
    db=SessionLocal()
    try:
        customer=db.query(Customer).first()
        item=retention_engine.refresh_customer_retention(db,customer.id,generate_message=True)
        assert item.communication_draft=="Guidance-grounded retention draft"
        assert item.message_generated_by=="AI + engagement RAG"
        assert item.knowledge_sources==[{"document_id":None,"title":"Engagement Guide","page":4,"score":None}]
        assert captured["kind"]=="retention"
        assert "Engagement Guide" in captured["guidance"]
        assert captured["facts"]["customer_name"]==customer.name
    finally:
        db.close()
