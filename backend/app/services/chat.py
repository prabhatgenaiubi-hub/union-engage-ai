from sqlalchemy.orm import Session
from app.models import *
from app.services.intelligence import provider, routing_intelligence
from app.services.lead_qualification import qualify
from app.services.financial_coach import coach
from app.services.retention_engine import refresh_customer_retention
from app.services.knowledge import knowledge_retriever
from app.services.pdf_knowledge import retrieve_pdf_chunks
from app.services.recommendations import identify_chat_opportunity

SCRIPT_LANGUAGES=[("\u0900","\u097f","hi-IN"),("\u0980","\u09ff","bn-IN"),("\u0a80","\u0aff","gu-IN"),("\u0c80","\u0cff","kn-IN"),("\u0d00","\u0d7f","ml-IN"),("\u0b00","\u0b7f","od-IN"),("\u0a00","\u0a7f","pa-IN"),("\u0b80","\u0bff","ta-IN"),("\u0c00","\u0c7f","te-IN")]
def detected_language(text:str)->str:
    for start,end,code in SCRIPT_LANGUAGES:
        if any(start<=character<=end for character in text): return code
    return "en-IN"

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
    response_language=detected_language(text) if language_code=="auto" else language_code
    conv=db.get(Conversation,conversation_id) if conversation_id else None
    if not conv or conv.customer_id!=customer_id:
        conv=Conversation(customer_id=customer_id,title=text[:80]); db.add(conv); db.flush()
    previous=db.query(Message).filter_by(conversation_id=conv.id).order_by(Message.created_at.desc()).limit(6).all()
    history=[{"role":item.role,"content":item.content} for item in reversed(previous)]
    contextual_query=" ".join([item["content"] for item in history[-2:] if item["role"]=="user"]+[text])
    analysis_query=provider.to_english(contextual_query,response_language)
    msg=Message(conversation_id=conv.id,role="user",content=text); db.add(msg); db.flush()
    a=provider.analyze(analysis_query); conv.primary_intent=a.intent; conv.sentiment=a.sentiment; conv.resolution_status="Unresolved" if a.complaint else "Answered"; conv.summary=f"Customer contacted the bank regarding {a.intent.lower()}. Current sentiment is {a.sentiment.lower()}. The interaction is {'at risk and requires service recovery' if a.sentiment=='Highly Negative' else 'awaiting confirmation that the customer is satisfied'}."
    interaction=InteractionAnalysis(message_id=msg.id,intent=a.intent,sentiment=a.sentiment,score=a.score,emotion=a.emotion,urgency=a.urgency,complaint=a.complaint,repeat_contact=a.repeat,entities=a.entities);db.add(interaction);db.flush()
    pdf_matches=retrieve_pdf_chunks(db,analysis_query)
    matches=knowledge_retriever.search(db,analysis_query)
    pdf_context="\n\n".join(f"[{item['title']}, page {item['page']}] {item['content']}" for item in pdf_matches)
    article_context="\n\n".join(f"[{item.title}] {item.content}" for item in matches)
    knowledge="\n\n".join(item for item in [pdf_context,article_context] if item) or None
    if a.intent=="Financial Coaching":
        pdf_matches=[]; matches=[]; knowledge=None
    service_draft=service_request_draft(a,text)
    lead=db.query(Lead).filter_by(conversation_id=conv.id,product="Home Loan").first()
    qualification=None
    if a.intent=="Home Loan Interest" or lead:
        if not lead:
            lead=Lead(customer_id=customer_id,conversation_id=conv.id,product="Home Loan",score=40,temperature="Cold",reasons=["Product intent explicitly expressed"],next_action="Collect required amount",journey_stage="Amount",status="In Qualification",qualification_data={});db.add(lead);db.flush()
            db.add(Notification(title="Home-loan lead identified",severity="info",customer_id=customer_id))
        qualification=qualify(lead,text)
    guidance=None
    if qualification:
        guidance=(f"Acknowledge the information just provided, then ask exactly one concise qualification question: {qualification['next_question']}" if not qualification["complete"] else "Confirm that qualification is complete and explain that a relationship manager can review the home-loan requirement and follow up. Do not promise approval.")
    goal=db.query(FinancialGoal).filter_by(conversation_id=conv.id).first()
    coaching=None
    if a.intent=="Financial Coaching" or goal:
        if not goal:
            goal=FinancialGoal(customer_id=customer_id,conversation_id=conv.id,name="Savings Goal",target_amount=0,saved_amount=0,timeline_months=0,monthly_required=0,monthly_income=0,monthly_expenses=0,status="Planning",coaching_plan={});db.add(goal);db.flush()
        coaching=coach(goal,text)
        if coaching["complete"]:
            plan=coaching["plan"]
            guidance=f"Provide a concise guidance-first financial plan using these exact figures: monthly income ₹{goal.monthly_income:,.0f}, expenses ₹{goal.monthly_expenses:,.0f}, surplus ₹{plan['monthly_surplus']:,.0f}, goal ₹{goal.target_amount:,.0f}, timeline {goal.timeline_months} months, required monthly saving ₹{goal.monthly_required:,.0f}, emergency fund target ₹{plan['emergency_fund_target']:,.0f}, feasible {plan['feasible']}. Mention budgeting, emergency fund, tracking, and discipline. Do not recommend or sell any bank product."
        else:guidance=f"Act as a financial coach, not a salesperson. Acknowledge the information and ask exactly one concise question: {coaching['next_question']} Do not mention bank products."
    response=provider.response(text,a,knowledge,history,response_language,bool(service_draft),guidance); assistant=Message(conversation_id=conv.id,role="assistant",content=response); db.add(assistant)
    routing=routing_intelligence(a); db.add(RoutingDecision(conversation_id=conv.id,interaction_analysis_id=interaction.id,recommended_queue=routing["queue"],reason=routing["reason"],issue=routing["issue"],urgency=routing["urgency"],sentiment=routing["sentiment"],repeat_contact=routing["repeat_contact"],escalation=routing["escalation"]))
    opportunity=None if a.complaint or a.sentiment in ["Negative","Highly Negative"] or a.intent=="Financial Coaching" else identify_chat_opportunity(db,customer_id,conv.id,text,history)
    service_suggested=service_draft is not None
    risk=refresh_customer_retention(db,customer_id)
    if risk.level in ["High","Critical"]: db.add(Notification(title=f"{risk.level} attrition risk detected",severity="critical",customer_id=customer_id))
    db.commit(); db.refresh(conv)
    sources=[{"id":item["id"],"title":item["title"],"category":item["category"],"page":item["page"],"source_type":"pdf"} for item in pdf_matches]+[{"id":item.article_id,"title":item.title,"category":item.category,"page":None,"source_type":"article"} for item in matches]
    return {"conversation_id":conv.id,"message":response,"language_code":response_language,"analysis":{"intent":a.intent,"sentiment":a.sentiment,"emotion":a.emotion,"urgency":a.urgency,"complaint":a.complaint,"repeat_contact":a.repeat},"knowledge_sources":sources,"grounded":bool(sources),"service_request_suggested":service_suggested,"service_request_draft":service_draft,"lead":{"id":lead.id,"score":lead.score,"temperature":lead.temperature,"stage":lead.journey_stage,"status":lead.status,"next_question":qualification["next_question"] if qualification else None,"collected":lead.qualification_data,"reasons":lead.reasons} if lead else None,"goal":{"id":goal.id,"name":goal.name,"status":goal.status,"monthly_income":goal.monthly_income,"monthly_expenses":goal.monthly_expenses,"target_amount":goal.target_amount,"timeline_months":goal.timeline_months,"monthly_required":goal.monthly_required,"plan":goal.coaching_plan,"next_question":coaching["next_question"] if coaching else None} if goal else None,"opportunity":{"id":opportunity.id,"product":opportunity.product,"score":opportunity.score,"status":opportunity.status} if opportunity else None,"routing":routing}
