from sqlalchemy.orm import Session
from app.models import Conversation,Customer,CustomerFeedback,InteractionAnalysis,Lead,Message,RetentionScore,ServiceRequest
from app.services.intelligence import provider
from app.services.pdf_knowledge import retrieve_engagement_guidance

def refresh_customer_retention(db:Session,customer_id:int,generate_message:bool=False)->RetentionScore:
    customer=db.get(Customer,customer_id)
    conversation_ids=db.query(Conversation.id).filter_by(customer_id=customer_id)
    analyses=db.query(InteractionAnalysis).join(Message).filter(Message.conversation_id.in_(conversation_ids)).order_by(Message.created_at.desc()).limit(10).all()
    open_requests=db.query(ServiceRequest).filter(ServiceRequest.customer_id==customer_id,ServiceRequest.status.notin_(["Resolved","Closed"])).count()
    feedback=db.query(CustomerFeedback).join(Conversation,CustomerFeedback.conversation_id==Conversation.id).filter(Conversation.customer_id==customer_id).order_by(CustomerFeedback.created_at.desc()).first()
    abandoned=db.query(Lead).filter_by(customer_id=customer_id,drop_off_detected=True).count()
    negative=sum(item.sentiment in ["Negative","Highly Negative"] for item in analyses);repeats=sum(item.repeat_contact for item in analyses);closures=sum(item.intent=="Account Closure" for item in analyses)
    score=10;reasons=[]
    if closures:score+=45;reasons.append("Account-closure intent detected")
    if negative:score+=min(30,negative*10);reasons.append(f"{negative} negative interaction(s) in recent history")
    if repeats:score+=15;reasons.append("Repeated-contact signal without confirmed resolution")
    if open_requests:score+=min(20,open_requests*10);reasons.append(f"{open_requests} unresolved service request(s)")
    if feedback and feedback.csat is not None and feedback.csat<=2:score+=15;reasons.append(f"Low CSAT of {feedback.csat}/5")
    if feedback and feedback.nps is not None and feedback.nps<=6:score+=10;reasons.append(f"Detractor/low NPS of {feedback.nps}/10")
    if abandoned:score+=min(10,abandoned*5);reasons.append("Abandoned customer journey detected")
    score=min(100,score);level="Critical" if score>=80 else "High" if score>=60 else "Medium" if score>=30 else "Low";case_type="Win-back" if closures else "Retention"
    action="Priority relationship-manager intervention; resolve service failures before any offer" if level in ["High","Critical"] else "Monitor upcoming interactions and confirm satisfaction" if level=="Medium" else "Continue normal service and monitor experience"
    primary_reason=reasons[0] if reasons else "No material attrition signal is currently present"
    fallback=(f"Hello {customer.name}, we’re sorry that your recent experience has not met expectations. We would value the opportunity to understand and resolve your concerns, particularly: {primary_reason.lower()}. A relationship manager can contact you at a convenient time to review the situation. No action is required unless you would like us to follow up." if level in ["High","Critical"] else f"Hello {customer.name}, we’re checking whether your recent banking experience was resolved satisfactorily. If anything remains outstanding, please let us know and our team can review it.")
    item=db.query(RetentionScore).filter_by(customer_id=customer_id).order_by(RetentionScore.updated_at.desc()).first()
    should_update=not item or not item.communication_draft or item.status=="Monitoring"
    draft=fallback
    message_generated_by="Deterministic fallback"
    knowledge_sources=[]
    if generate_message and should_update:
        guidance_matches=retrieve_engagement_guidance(db,f"{case_type} message {level} risk service recovery {' '.join(reasons)}",limit=4)
        guidance="\n\n".join(f"[{match['title']}, page {match['page']}] {match['content']}" for match in guidance_matches) or None
        if guidance:
            facts={"customer_name":customer.name,"case_type":case_type,"risk_level":level,"reasons":reasons,"open_service_requests":open_requests,"negative_interactions":negative,"repeat_contact_count":repeats}
            draft=provider.engagement_draft(case_type.lower(),facts,guidance,fallback)
            if draft!=fallback:
                message_generated_by="AI + engagement RAG"
                knowledge_sources=[{"document_id":match["document_id"],"title":match["title"],"page":match["page"],"score":match["score"]} for match in guidance_matches]
    if not item:item=RetentionScore(customer_id=customer_id,score=score,level=level,reasons=reasons,suggested_action=action);db.add(item)
    item.score=score;item.level=level;item.reasons=reasons or ["No material attrition signal detected"];item.suggested_action=action;item.case_type=case_type
    if item.status=="Closed" and level in ["High","Critical"]:item.status="Monitoring"
    if not item.communication_draft or item.status=="Monitoring":
        item.communication_draft=draft;item.message_generated_by=message_generated_by;item.knowledge_sources=knowledge_sources
    db.flush();return item

def refresh_all_retention(db:Session,generate_messages:bool=False)->list[RetentionScore]:
    return [refresh_customer_retention(db,customer.id,generate_messages) for customer in db.query(Customer).all()]
