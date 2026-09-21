import re
from datetime import datetime
from app.models import Lead

FIELDS=["required_amount","monthly_income","employment_type","existing_emi","location","timeline"]
QUESTIONS={
 "required_amount":"What home-loan amount do you require?",
 "monthly_income":"What is your approximate monthly income?",
 "employment_type":"Are you salaried, self-employed, or employed in another way?",
 "existing_emi":"What is your total existing monthly EMI? You can say zero.",
 "location":"In which city is the property located?",
 "timeline":"When are you planning to purchase the property?",
}
STAGES={"required_amount":"Amount","monthly_income":"Income","employment_type":"Employment","existing_emi":"Existing EMI","location":"Location","timeline":"Timeline"}

def _amount(text:str)->float|None:
    match=re.search(r"(?:₹|rs\.?\s*)?([0-9]+(?:\.[0-9]+)?)\s*(lakh|lac|crore|k)?",text.lower())
    if not match:return None
    value=float(match.group(1));unit=match.group(2)
    return value*(10000000 if unit=="crore" else 100000 if unit in ["lakh","lac"] else 1000 if unit=="k" else 1)

def qualify(lead:Lead,text:str)->dict:
    data=dict(lead.qualification_data or {})
    missing=next((field for field in FIELDS if field not in data),None)
    t=text.lower().strip()
    if missing=="required_amount":
        value=_amount(text)
        if value:data[missing]=value
    elif missing=="monthly_income":
        value=_amount(text)
        if value:data[missing]=value
    elif missing=="employment_type":
        employment=next((value for value in ["salaried","self-employed","business owner","retired"] if value in t),None)
        if employment:data[missing]=employment
    elif missing=="existing_emi":
        value=0 if t in ["zero","none","no","no emi","no existing emi"] else _amount(text)
        if value is not None:data[missing]=value
    elif missing=="location" and len(t)>1:data[missing]=text.strip()[:80]
    elif missing=="timeline" and len(t)>1:data[missing]=text.strip()[:80]
    next_field=next((field for field in FIELDS if field not in data),None)
    score=40
    reasons=["Product intent explicitly expressed"]
    weights={"required_amount":15,"monthly_income":15,"employment_type":10,"existing_emi":8,"location":5,"timeline":7}
    for field,weight in weights.items():
        if field in data:score+=weight;reasons.append(f"{field.replace('_',' ').title()} provided")
    lead.qualification_data=data;lead.score=min(score,100);lead.temperature="Hot" if lead.score>=80 else "Warm" if lead.score>=55 else "Cold"
    lead.journey_stage="Qualified" if not next_field else STAGES[next_field]
    lead.status="Qualified" if not next_field else "In Qualification";lead.drop_off_detected=False
    lead.next_action="Relationship Manager callback" if not next_field else f"Collect {next_field.replace('_',' ')}"
    lead.reasons=reasons
    return {"complete":not next_field,"next_field":next_field,"next_question":QUESTIONS.get(next_field),"collected":data,"score":lead.score,"temperature":lead.temperature,"stage":lead.journey_stage,"reasons":reasons}
