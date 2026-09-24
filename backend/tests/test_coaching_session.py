from app.models import FinancialGoal
from app.services.coaching_session import coach

def goal():
    return FinancialGoal(name="Savings Goal",coaching_plan={})

def test_budget_zeroes_confirmation_actions_and_resume():
    g=goal()
    for answer in ["budget","50000","30000","0","0","regular","0"]:
        result=coach(g,answer)
    assert result["plan"]["stage"]=="confirmation"
    assert result["plan"]["monthly_surplus"]==20000
    assert g.status=="Planning"
    coach(g,"confirm")
    result=coach(g,"choose track")
    assert result["plan"]["actions"][0]["id"]=="track"
    result=coach(g,"I kept a spending diary this week")
    assert result["plan"]["reviews"][-1]["note"]=="I kept a spending diary this week"
    assert result["plan"]["actions"][0]["review_on"]

def test_repayments_unknown_and_scenario_does_not_overwrite():
    g=goal()
    for answer in ["I want to save 500000 for a car","income 50000","expenses 30000","10000","0","variable","skip","100000","18","0","24 months","confirm"]:
        result=coach(g,answer)
    assert result["plan"]["monthly_surplus"]==10000
    assert result["plan"]["emergency_fund_target"]==240000
    assert result["plan"]["feasible"] is False
    result=coach(g,"what if 36 months")
    assert g.timeline_months==24
    assert result["plan"]["scenarios"][-1]["timeline_months"]==36
    assert result["plan"]["inputs"]["dependants"] is None
    coach(g,"income 40000")
    assert g.status=="Planning"
    assert g.coaching_plan["confirmed"] is False

def test_skip_does_not_invent_affordability():
    g=goal()
    for answer in ["budget","skip","30000","0","0","regular","0","confirm"]:
        result=coach(g,answer)
    assert result["plan"]["recommended_monthly_contribution"]==0
    assert "provisional" in result["plan"]["summary"]

def test_coach_mode_suppresses_sales_and_retrieves_only_coaching(client,customer_headers,monkeypatch):
    from app.services import chat
    calls=[]
    monkeypatch.setattr(chat,"retrieve_pdf_chunks",lambda *args,**kwargs:calls.append(kwargs.get("audience")) or [])
    monkeypatch.setattr(chat,"identify_chat_opportunity",lambda *args:(_ for _ in ()).throw(AssertionError("Sales in coach mode")))
    response=client.post("/api/chat",headers=customer_headers,json={"message":"Help with my credit card debt","mode":"coach"})
    assert response.status_code==200
    body=response.json()
    assert body["lead"] is None and body["opportunity"] is None
    assert body["goal"]["plan"]["inputs"]["focus"]=="debt"
    assert calls==["coaching"]
