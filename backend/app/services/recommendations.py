from sqlalchemy.orm import Session
from app.models import Customer,Opportunity
from app.services.intelligence import MockAIProvider,provider
from app.services.pdf_knowledge import retrieve_engagement_guidance

REVIEWED_STATUSES={"Approved","Email Sent"}

def _guidance(db:Session,query:str)->str|None:
    matches=retrieve_engagement_guidance(db,query,limit=4)
    return "\n\n".join(f"[{item['title']}, page {item['page']}] {item['content']}" for item in matches) or None

def _profile(customer:Customer,existing:list[Opportunity]|None=None)->dict:
    return {
        "customer_id":customer.id,"name":customer.name,"segment":customer.segment,
        "relationship_since":customer.relationship_since,"average_balance":customer.average_balance,
        "monthly_income":customer.monthly_income,"monthly_surplus":customer.monthly_surplus,
        "existing_signals":[{"product":item.product,"reason":item.reason,"trigger":item.trigger} for item in (existing or [])],
    }

def _clean(raw:dict,allowed_ids:set[int])->dict|None:
    try:
        customer_id=int(raw["customer_id"]);score=max(0,min(100,int(raw["score"])))
        product=str(raw["product"]).strip()[:60];product={"auto loan":"Vehicle Loan","car loan":"Vehicle Loan","housing loan":"Home Loan","term deposit":"Fixed Deposit","fd":"Fixed Deposit"}.get(product.lower(),product)
        reason=str(raw["reason"]).strip()[:2000]
        trigger=str(raw["trigger"]).strip()[:100];action=str(raw["suggested_action"]).strip()[:160]
        draft=str(raw["communication_draft"]).strip()[:2000]
        generated_by=str(raw.get("_generated_by","AI provider"))[:40]
    except (KeyError,TypeError,ValueError):return None
    if customer_id not in allowed_ids or not all([product,reason,trigger,action,draft]):return None
    return {"customer_id":customer_id,"product":product,"score":score,"reason":reason,"trigger":trigger,"suggested_action":action,"communication_draft":draft,"generated_by":generated_by}

def _upsert(db:Session,candidate:dict)->tuple[Opportunity,bool]:
    existing=db.query(Opportunity).filter_by(customer_id=candidate["customer_id"],product=candidate["product"]).first()
    if existing:
        if existing.status not in REVIEWED_STATUSES:
            candidate["score"]=max(existing.score,candidate["score"])
            for field in ["score","reason","trigger","suggested_action","communication_draft","generated_by"]:setattr(existing,field,candidate[field])
            if existing.status=="Dismissed":existing.status="Pending Review"
        return existing,False
    item=Opportunity(**candidate,status="Pending Review");db.add(item);db.flush();return item,True

def identify_chat_opportunity(db:Session,customer_id:int,conversation_id:int,text:str,history:list[dict]|None=None)->Opportunity|None:
    """Ask the configured AI provider for a recommendation grounded in conversation facts."""
    customer=db.get(Customer,customer_id)
    if not customer:return None
    context="\n".join([f"{item.get('role','user')}: {item.get('content','')}" for item in (history or [])]+[f"user: {text}"])
    existing=db.query(Opportunity).filter_by(customer_id=customer_id).all()
    guidance=_guidance(db,f"sales opportunity message product offer lead stage customer sentiment {context}")
    candidates=provider.opportunity_recommendations([_profile(customer,existing)],context,guidance)
    for raw in candidates:
        candidate=_clean(raw,{customer_id})
        if candidate:
            candidate["reason"]=f"Conversation #{conversation_id}: {candidate['reason']}"
            candidate["trigger"]=f"Chat signal · {candidate['trigger'][:70]} · Conversation #{conversation_id}"
            return _upsert(db,candidate)[0]
    return None

def identify_opportunities(db:Session)->list[Opportunity]:
    """Generate grounded recommendations in bounded batches using the active AI provider."""
    customers=db.query(Customer).all();existing=db.query(Opportunity).all();by_customer={}
    for item in existing:by_customer.setdefault(item.customer_id,[]).append(item)
    created=[]
    for offset in range(0,len(customers),10):
        batch=customers[offset:offset+10];allowed={customer.id for customer in batch}
        guidance=_guidance(db,"sales opportunity message approved products offers lead communication disclosures")
        raw_items=provider.opportunity_recommendations([_profile(customer,by_customer.get(customer.id,[])) for customer in batch],guidance=guidance)
        # Keep refresh useful if a model omits all baseline candidates for an eligible profile.
        baseline=MockAIProvider().opportunity_recommendations([_profile(customer,by_customer.get(customer.id,[])) for customer in batch])
        returned={(int(item.get("customer_id",-1)),str(item.get("product","")).lower()) for item in raw_items if isinstance(item,dict)}
        raw_items.extend(item for item in baseline if (item["customer_id"],item["product"].lower()) not in returned)
        seen=set()
        for raw in raw_items:
            candidate=_clean(raw,allowed)
            key=(candidate["customer_id"],candidate["product"].lower()) if candidate else None
            if not candidate or key in seen:continue
            seen.add(key);item,is_new=_upsert(db,candidate)
            if is_new:created.append(item)
    # Upgrade legacy pending cards through a focused AI rewrite. Reviewed content stays immutable.
    legacy=[item for item in db.query(Opportunity).filter_by(status="Pending Review").all() if item.generated_by=="rules"]
    customer_map={customer.id:customer for customer in customers}
    for item in legacy:
        customer=customer_map.get(item.customer_id)
        if not customer:continue
        instruction=f"Regenerate the existing {item.product} opportunity from this stored signal only. Keep the product exactly {item.product}. Existing reason: {item.reason}. Existing trigger: {item.trigger}."
        guidance=_guidance(db,f"sales opportunity message {item.product} approved offer disclosures")
        suggestions=provider.opportunity_recommendations([_profile(customer,[item])],instruction,guidance)
        if not suggestions:continue
        raw={**suggestions[0],"customer_id":customer.id,"product":item.product}
        candidate=_clean(raw,{customer.id})
        if candidate:_upsert(db,candidate)
    return created
