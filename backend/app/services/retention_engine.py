from sqlalchemy.orm import Session
from app.models import Conversation,Customer,CustomerFeedback,InteractionAnalysis,Lead,Message,RetentionScore,ServiceRequest

def refresh_customer_retention(db:Session,customer_id:int)->RetentionScore:
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
    draft=(f"Hello {customer.name}, we’re sorry that your recent experience has not met expectations. We would value the opportunity to understand and resolve your concerns, particularly: {primary_reason.lower()}. A relationship manager can contact you at a convenient time to review the situation. No action is required unless you would like us to follow up." if level in ["High","Critical"] else f"Hello {customer.name}, we’re checking whether your recent banking experience was resolved satisfactorily. If anything remains outstanding, please let us know and our team can review it.")
    item=db.query(RetentionScore).filter_by(customer_id=customer_id).order_by(RetentionScore.updated_at.desc()).first()
    if not item:item=RetentionScore(customer_id=customer_id,score=score,level=level,reasons=reasons,suggested_action=action);db.add(item)
    item.score=score;item.level=level;item.reasons=reasons or ["No material attrition signal detected"];item.suggested_action=action;item.case_type=case_type
    if item.status=="Closed" and level in ["High","Critical"]:item.status="Monitoring"
    if not item.communication_draft or item.status=="Monitoring":item.communication_draft=draft
    db.flush();return item

def refresh_all_retention(db:Session)->list[RetentionScore]:
    return [refresh_customer_retention(db,customer.id) for customer in db.query(Customer).all()]
