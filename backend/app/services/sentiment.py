from app.models import Conversation, InteractionAnalysis, RoutingDecision, ServiceRequest
from app.services.engagement import engagement_decision

def conversation_insights(conversation:Conversation,analyses:list[InteractionAnalysis],routing:RoutingDecision|None,request:ServiceRequest|None,feedback=None)->dict:
    latest=analyses[-1] if analyses else None
    sentiment=latest.sentiment if latest else conversation.sentiment
    if sentiment=="Highly Negative": quality="At Risk"
    elif sentiment=="Negative": quality="Poor"
    elif sentiment=="Positive": quality="Good"
    else: quality="Stable"
    reasons=[]
    if latest:
        if latest.repeat_contact: reasons.append("Customer reported repeated contact without resolution")
        if latest.complaint: reasons.append("An unresolved complaint or service failure was detected")
        if latest.sentiment=="Highly Negative": reasons.append(f"Language indicates {latest.emotion.lower()} and strong dissatisfaction")
        elif latest.sentiment=="Negative": reasons.append(f"Language indicates {latest.emotion.lower()} sentiment")
    if not reasons: reasons.append("No explicit dissatisfaction signal detected")
    expectation={
        "Debit Card Complaint":"Restore card access and receive a clear resolution update",
        "Debit Dispute":"Investigate the debit and communicate the outcome",
        "Account Closure":"Receive urgent service recovery and a clear account-resolution path",
    }.get(conversation.primary_intent,"Have the unresolved issue investigated and receive a clear resolution update" if latest and latest.complaint else "Receive an accurate answer and clear next steps")
    if request and request.status not in ["Resolved","Closed"]: next_action=f"Progress {request.request_code} in the {request.priority.lower()}-priority queue and update the customer"
    elif quality=="At Risk": next_action="Arrange priority human follow-up and confirm resolution with the customer"
    elif latest and latest.complaint: next_action="Create or review a service request and provide a response timeline"
    else: next_action="Confirm the answer resolved the query and invite feedback"
    engagement=engagement_decision(sentiment,conversation.resolution_status,latest.complaint if latest else False,bool(request and request.status not in ["Resolved","Closed"]))
    return {
        "conversation_summary":conversation.summary,
        "customer_issue":conversation.title,
        "sentiment":sentiment,
        "emotion":latest.emotion if latest else "Unknown",
        "intent":conversation.primary_intent,
        "interaction_quality":quality,
        "resolution_status":conversation.resolution_status,
        "dissatisfaction_reasons":reasons,
        "customer_expectation":expectation,
        "suggested_next_action":next_action,
        "sentiment_progression":[{"sentiment":item.sentiment,"emotion":item.emotion,"score":item.score,"urgency":item.urgency} for item in analyses],
        "feedback":{"csat":feedback.csat,"nps":feedback.nps,"created_at":feedback.created_at} if feedback else None,
        "recommended_route":routing.recommended_queue if routing else "Standard Queue",
        "engagement":engagement,
    }
