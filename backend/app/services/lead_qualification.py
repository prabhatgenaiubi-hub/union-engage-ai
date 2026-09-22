import re
from app.models import Lead

FIELDS=["required_amount","monthly_income","employment_type","existing_emi","location","timeline"]
STAGES={"required_amount":"Amount","monthly_income":"Income","employment_type":"Employment","existing_emi":"Existing EMI","location":"Location","timeline":"Timeline"}
PRODUCT_TERMS={
 "Home Loan":["home loan","housing loan","loan for a house","loan to buy a house","buying a house","buy a house","buying a home","purchase a house"],
 "Personal Loan":["personal loan","unsecured loan","loan for personal use"],
 "Vehicle Loan":["vehicle loan","car loan","auto loan","loan for a car"],
}
INTEREST_SIGNALS=["i need","i have need","have need of","i want","i require","looking for","interested in","want to apply","apply for","considering","thinking about","planning to take","would like","eligibility","how can i get","tell me about"]

def detect_lead_context(messages:list[str])->dict|None:
    """Infer supported product interest from the full customer conversation, not one keyword."""
    normalized=" ".join(" ".join(messages).lower().split())
    candidates=[]
    for product,terms in PRODUCT_TERMS.items():
        mentions=sum(normalized.count(term) for term in terms)
        if not mentions:continue
        explicit_intent=any(signal in normalized for signal in INTEREST_SIGNALS)
        qualification_detail=bool(re.search(r"(?:₹|rs\.?\s*)?\d+(?:\.\d+)?\s*(?:lakh|lac|crore|k)?",normalized)) or any(term in normalized for term in ["salary","income","salaried","self-employed","engineer","teacher","business owner","emi"])
        confidence=min(1.0,.45+(.3 if explicit_intent else 0)+(.15 if qualification_detail else 0)+(.1 if mentions>1 else 0))
        if explicit_intent or (mentions>1 and qualification_detail):candidates.append((confidence,product,mentions))
    if not candidates:return None
    confidence,product,mentions=max(candidates)
    return {"product":product,"confidence":round(confidence,2),"evidence_count":mentions}

def _amount_value(value:str,unit:str|None)->float:
    number=float(value.replace(",",""));unit=(unit or "").lower()
    return number*(10000000 if unit=="crore" else 100000 if unit in ["lakh","lac"] else 1000 if unit=="k" else 1)

def _amount_near(text:str,labels:list[str])->float|None:
    unit_pattern=r"(?:₹|rs\.?\s*)?([0-9][0-9,]*(?:\.[0-9]+)?)\s*(lakh|lac|crore|k)?"
    for label in labels:
        match=re.search(rf"{label}[^\d₹]{{0,35}}{unit_pattern}",text,re.I)
        if match:return _amount_value(match.group(1),match.group(2))
    return None

def _employment(text:str)->str|None:
    patterns=[
        ("Software Engineer",["software engineer","sofware engineer","software developer"]),("Engineer",["engineer"]),("Teacher",["teacher"]),
        ("Doctor",["doctor"]),("Government Employee",["government employee","government job"]),("Salaried",["salaried"]),
        ("Self-employed",["self-employed","self employed","freelancer"]),("Business Owner",["business owner","own a business"]),("Retired",["retired"]),
    ]
    return next((label for label,terms in patterns if any(term in text for term in terms)),None)

def _question(product:str,field:str)->str|None:
    return {
      "required_amount":f"What {product.lower()} amount do you require?",
      "monthly_income":"What is your approximate monthly income?",
      "employment_type":"What is your occupation or employment type?",
      "existing_emi":"What is your total existing monthly EMI? You can say zero.",
      "location":"Which city are you based in?",
      "timeline":f"When are you planning to take the {product.lower()}?",
    }.get(field)

def qualify(lead:Lead,text:str,latest_text:str|None=None)->dict:
    """Update every fact found in accumulated conversation context on every turn."""
    data=dict(lead.qualification_data or {});t=" ".join(text.lower().split());latest=" ".join((latest_text or text).lower().split())
    required=_amount_near(t,[r"(?:loan|amount|need|require|want)"])
    income=_amount_near(t,[r"(?:monthly\s+)?(?:income|salary|earn(?:ing|s)?|in[ -]?hand)"])
    emi=_amount_near(t,[r"(?:existing\s+)?emi"])
    employment=_employment(t)
    if required:data["required_amount"]=required
    if income:data["monthly_income"]=income
    if employment:data["employment_type"]=employment
    if emi is not None:data["existing_emi"]=emi
    elif any(term in t for term in ["no emi","no existing emi","zero emi"]):data["existing_emi"]=0
    city=re.search(r"(?:live in|based in|city is|located in)\s+([a-z][a-z .-]{1,40})",t)
    if city:data["location"]=city.group(1).strip().title()
    timeline=re.search(r"(?:within|in the next|after)\s+(\d+\s+(?:day|week|month|year)s?)",t)
    if timeline:data["timeline"]=timeline.group(1)
    missing=next((field for field in FIELDS if field not in data),None)
    plain_amount=re.fullmatch(r"(?:₹|rs\.?\s*)?([0-9][0-9,]*(?:\.[0-9]+)?)\s*(lakh|lac|crore|k)?(?:\s+per\s+month)?",latest,re.I)
    if missing in ["required_amount","monthly_income","existing_emi"] and plain_amount:data[missing]=_amount_value(plain_amount.group(1),plain_amount.group(2))
    elif missing=="existing_emi" and latest in ["zero","none","no"]:data[missing]=0
    elif missing=="location" and re.fullmatch(r"[a-z][a-z .-]{1,40}",latest):data[missing]=(latest_text or text).strip().title()
    elif missing=="timeline" and len(latest)>1:data[missing]=(latest_text or text).strip()[:80]
    next_field=next((field for field in FIELDS if field not in data),None)
    score=40;reasons=[f"Context indicates active {lead.product.lower()} interest"]
    weights={"required_amount":15,"monthly_income":15,"employment_type":10,"existing_emi":8,"location":5,"timeline":7}
    for field,weight in weights.items():
        if field in data:score+=weight;reasons.append(f"{field.replace('_',' ').title()} provided")
    lead.qualification_data=data;lead.score=min(score,100);lead.temperature="Hot" if lead.score>=80 else "Warm" if lead.score>=55 else "Cold"
    lead.journey_stage="Qualified" if not next_field else STAGES[next_field]
    lead.status="Qualified" if not next_field else "In Qualification";lead.drop_off_detected=False
    lead.next_action="Relationship Manager callback" if not next_field else f"Collect {next_field.replace('_',' ')}"
    lead.reasons=reasons
    return {"complete":not next_field,"next_field":next_field,"next_question":_question(lead.product,next_field) if next_field else None,"collected":data,"score":lead.score,"temperature":lead.temperature,"stage":lead.journey_stage,"reasons":reasons}
