from sqlalchemy.orm import Session
from app.models import *
import re
from app.services.intelligence import provider, lead_score, retention, route
from app.services.knowledge import knowledge_retriever
from app.services.pdf_knowledge import retrieve_pdf_chunks

def service_request_draft(a,text:str)->dict|None:
    if not a.complaint:
        return None
    category={
        "Debit Card Complaint":"Debit Card",
        "Debit Dispute":"Transaction Dispute",
        "Account Closure":"Account Service",
    }.get(a.intent,"Customer Service")
    priority="High" if a.urgency=="High" or a.sentiment=="Highly Negative" else "Medium"
    return {"category":category,"issue":text[:500],"priority":priority}

def process_message(db:Session,customer_id:int,text:str,conversation_id:int|None=None,language_code:str="auto")->dict:
    conv=db.get(Conversation,conversation_id) if conversation_id else None
    if not conv or conv.customer_id!=customer_id:
        conv=Conversation(customer_id=customer_id,title=text[:80]); db.add(conv); db.flush()
    previous=db.query(Message).filter_by(conversation_id=conv.id).order_by(Message.created_at.desc()).limit(6).all()
    history=[{"role":item.role,"content":item.content} for item in reversed(previous)]
    contextual_query=" ".join([item["content"] for item in history[-2:] if item["role"]=="user"]+[text])
    analysis_query=provider.to_english(contextual_query,language_code)
    msg=Message(conversation_id=conv.id,role="user",content=text); db.add(msg); db.flush()
    a=provider.analyze(analysis_query); conv.primary_intent=a.intent; conv.sentiment=a.sentiment; conv.resolution_status="Unresolved" if a.complaint else "Answered"; conv.summary=f"Customer contacted the bank regarding {a.intent.lower()}. Current sentiment is {a.sentiment.lower()}. The interaction is {'at risk and requires service recovery' if a.sentiment=='Highly Negative' else 'awaiting confirmation that the customer is satisfied'}."
    db.add(InteractionAnalysis(message_id=msg.id,intent=a.intent,sentiment=a.sentiment,score=a.score,emotion=a.emotion,urgency=a.urgency,complaint=a.complaint,repeat_contact=a.repeat,entities=a.entities))
    pdf_matches=retrieve_pdf_chunks(db,analysis_query)
    matches=knowledge_retriever.search(db,analysis_query)
    pdf_context="\n\n".join(f"[{item['title']}, page {item['page']}] {item['content']}" for item in pdf_matches)
    article_context="\n\n".join(f"[{item.title}] {item.content}" for item in matches)
    knowledge="\n\n".join(item for item in [pdf_context,article_context] if item) or None
    service_draft=service_request_draft(a,text)
    response=provider.response(text,a,knowledge,history,language_code,bool(service_draft)); assistant=Message(conversation_id=conv.id,role="assistant",content=response); db.add(assistant)
    queue,route_reason=route(a); db.add(RoutingDecision(conversation_id=conv.id,recommended_queue=queue,reason=route_reason))
    service_suggested=service_draft is not None
    lead=None
    if a.intent=="Home Loan Interest":
        count=db.query(Message).filter_by(conversation_id=conv.id,role="user").count(); score,reasons=lead_score(text,count)
        lead=db.query(Lead).filter_by(conversation_id=conv.id,product="Home Loan").first()
        temp="Hot" if score>=70 else "Warm" if score>=40 else "Cold"
        if lead: lead.score=max(lead.score,score); lead.temperature="Hot" if lead.score>=70 else "Warm" if lead.score>=40 else "Cold"; lead.reasons=list(set(lead.reasons+reasons)); lead.journey_stage="Eligibility" if score>=60 else "Discovery"
        else: lead=Lead(customer_id=customer_id,conversation_id=conv.id,product="Home Loan",score=score,temperature=temp,reasons=reasons,next_action="Relationship Manager callback" if score>=70 else "Continue qualification"); db.add(lead)
        db.add(Notification(title="Home-loan lead generated",severity="info",customer_id=customer_id))
    goal=None
    if a.intent=="Financial Coaching":
        values=[float(x) for x in re.findall(r"(?:₹|rs\.?\s*)?([0-9]+(?:\.[0-9]+)?)",text.lower())]
        income=values[0] if values else 0
        target=values[-1] if len(values)>1 else 500000
        if "lakh" in text.lower() and target<1000: target*=100000
        timeline=24; monthly=max(0,target/timeline)
        goal=FinancialGoal(customer_id=customer_id,name="Car Goal" if "car" in text.lower() else "Savings Goal",target_amount=target,saved_amount=0,timeline_months=timeline,monthly_required=monthly)
        db.add(goal)
    risk_score,risk_level,risk_reasons=retention(a)
    if risk_score>=30:
        db.add(RetentionScore(customer_id=customer_id,score=risk_score,level=risk_level,reasons=risk_reasons,suggested_action="Priority RM intervention" if risk_level in ["High","Critical"] else "Monitor next interaction"))
        if risk_level in ["High","Critical"]: db.add(Notification(title=f"{risk_level} attrition risk detected",severity="critical",customer_id=customer_id))
    db.commit(); db.refresh(conv)
    sources=[{"id":item["id"],"title":item["title"],"category":item["category"],"page":item["page"],"source_type":"pdf"} for item in pdf_matches]+[{"id":item.article_id,"title":item.title,"category":item.category,"page":None,"source_type":"article"} for item in matches]
    return {"conversation_id":conv.id,"message":response,"language_code":language_code,"analysis":{"intent":a.intent,"sentiment":a.sentiment,"emotion":a.emotion,"urgency":a.urgency,"complaint":a.complaint,"repeat_contact":a.repeat},"knowledge_sources":sources,"grounded":bool(sources),"service_request_suggested":service_suggested,"service_request_draft":service_draft,"lead":{"score":lead.score,"temperature":lead.temperature,"stage":lead.journey_stage,"reasons":lead.reasons} if lead else None,"goal":{"name":goal.name,"target_amount":goal.target_amount,"timeline_months":goal.timeline_months,"monthly_required":goal.monthly_required} if goal else None,"routing":{"queue":queue,"reason":route_reason}}
