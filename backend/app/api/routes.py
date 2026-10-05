from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import *
from app.schemas.api import *
from app.core.security import verify_password, create_token
from app.api.deps import current_user, bank_user, admin_user
from app.services.chat import process_message
from app.services.intelligence import format_customer_message,provider, routing_intelligence
from app.core.config import settings
from app.services.pdf_knowledge import ingest_pdf, MAX_PDF_BYTES
from app.services.speech import transcribe_audio, transcribe_audio_batch, MAX_AUDIO_BYTES, MAX_BATCH_AUDIO_BYTES
from app.services.sentiment import conversation_insights
from app.services.engagement import engagement_decision
from app.services.recommendations import identify_opportunities
from app.services.retention_engine import refresh_all_retention,refresh_customer_retention
from app.services.email import send_transactional_email
from app.services.public_chat_session import public_chat as public_chat_service

router=APIRouter(prefix="/api")
def serialize(obj):
    return {c.name:getattr(obj,c.name) for c in obj.__table__.columns}
def customer_engagement(db:Session,customer_id:int)->dict:
    conversation=db.query(Conversation).filter_by(customer_id=customer_id).order_by(Conversation.updated_at.desc()).first()
    if not conversation:return engagement_decision("Neutral","In Progress")
    latest=db.query(InteractionAnalysis).join(Message).filter(Message.conversation_id==conversation.id).order_by(Message.created_at.desc()).first()
    open_request=db.query(ServiceRequest).filter(ServiceRequest.customer_id==customer_id,ServiceRequest.status.notin_(["Resolved","Closed"])).order_by(ServiceRequest.created_at.desc()).first()
    return engagement_decision(latest.sentiment if latest else conversation.sentiment,conversation.resolution_status,latest.complaint if latest else False,bool(open_request),open_request.request_code if open_request else None)
def customer_experience_scores(db:Session,customer_id:int,limit:int=10)->dict:
    conversations=db.query(Conversation).filter_by(customer_id=customer_id).order_by(Conversation.updated_at.desc(),Conversation.id.desc()).limit(limit).all()
    scores=[];defaulted=0
    for conversation in conversations:
        feedback=db.query(CustomerFeedback).filter_by(conversation_id=conversation.id).order_by(CustomerFeedback.created_at.desc(),CustomerFeedback.id.desc()).first()
        if feedback and feedback.csat is not None:scores.append(feedback.csat)
        else:scores.append(3);defaulted+=1
    csat=sum(scores)/len(scores) if scores else 3
    return {"csat":round(csat,1),"nps":round(((csat-3)/2)*100),"sessions":len(scores),"defaulted_sessions":defaulted}
def login(payload:LoginRequest,user_type:str,db:Session):
    user=db.query(User).filter_by(login_id=payload.login_id,user_type=user_type).first()
    if not user or not verify_password(payload.password,user.password_hash): raise HTTPException(401,"Invalid credentials")
    db.add(AuditLog(user_id=user.id,action="LOGIN",entity="session",entity_id=str(user.id))); db.commit()
    return TokenResponse(access_token=create_token(user.id,user.role,user.user_type),role=user.role,user_type=user.user_type,display_name=user.display_name,customer_id=user.customer_id)

@router.post("/auth/customer/login",response_model=TokenResponse,tags=["Authentication"])
def customer_login(payload:LoginRequest,db:Session=Depends(get_db)): return login(payload,"customer",db)
@router.post("/auth/employee/login",response_model=TokenResponse,tags=["Authentication"])
def employee_login(payload:LoginRequest,db:Session=Depends(get_db)): return login(payload,"employee",db)
@router.get("/me",tags=["Authentication"])
def me(user:User=Depends(current_user)): return {"id":user.id,"name":user.display_name,"role":user.role,"type":user.user_type,"customer_id":user.customer_id}

@router.post("/public/chat",tags=["Public Assistant"])
def public_chat_endpoint(payload:PublicChatRequest,db:Session=Depends(get_db)):
    return public_chat_service(db,payload.message,payload.session_id,payload.language_code)

@router.get("/public/chat/{session_id}",tags=["Public Assistant"])
def public_chat_history(session_id:str,db:Session=Depends(get_db)):
    conversation=db.query(PublicConversation).filter_by(session_token=session_id).first()
    if not conversation:raise HTTPException(404,"Public chat session not found")
    return {"session_id":conversation.session_token,"messages":[{"role":item.role,"content":item.content,"sources":item.sources or []} for item in conversation.messages]}

@router.post("/public/speech-to-text",tags=["Public Assistant"])
async def public_speech_to_text(file:UploadFile=File(...),language_code:str=Form("auto")):
    data=await file.read(MAX_AUDIO_BYTES+1)
    try:return transcribe_audio(data,file.filename or "recording.webm",file.content_type or "application/octet-stream",language_code)
    except ValueError as exc:raise HTTPException(400,str(exc))

@router.get("/customer/profile",tags=["Customer"])
def customer_profile(user:User=Depends(current_user),db:Session=Depends(get_db)):
    if user.user_type!="customer" or not user.customer_id:raise HTTPException(403,"Customer access required")
    customer=db.get(Customer,user.customer_id)
    if not customer:raise HTTPException(404,"Customer profile not found")
    return {**serialize(customer),"display_name":user.display_name,"login_id":user.login_id}

@router.post("/chat",tags=["Customer AI"])
def chat(payload:ChatRequest,user:User=Depends(current_user),db:Session=Depends(get_db)):
    if user.user_type!="customer" or not user.customer_id: raise HTTPException(403,"Customer access required")
    return process_message(db,user.customer_id,payload.message,payload.conversation_id,payload.language_code)
@router.post("/speech-to-text",tags=["Customer AI"])
async def speech_to_text(file:UploadFile=File(...),language_code:str=Form("auto"),user:User=Depends(current_user)):
    if user.user_type!="customer":raise HTTPException(403,"Customer access required")
    data=await file.read(MAX_AUDIO_BYTES+1)
    try:return transcribe_audio(data,file.filename or "recording.webm",file.content_type or "application/octet-stream",language_code)
    except ValueError as exc:raise HTTPException(400,str(exc))
@router.post("/admin/voice-sentiment",tags=["Administration"])
async def analyze_voice_sentiment(file:UploadFile=File(...),customer_id:int=Form(...),user:User=Depends(admin_user),db:Session=Depends(get_db)):
    customer=db.get(Customer,customer_id)
    if not customer:raise HTTPException(404,"Customer not found")
    data=await file.read(MAX_BATCH_AUDIO_BYTES+1)
    try:transcription=transcribe_audio_batch(data,file.filename or "recording",file.content_type or "application/octet-stream")
    except ValueError as exc:raise HTTPException(400,str(exc))
    detected_language=transcription.get("language_code") or "auto"
    analysis_text=provider.to_english(transcription["transcript"],detected_language)
    analysis=provider.analyze(analysis_text); routing=routing_intelligence(analysis)
    transcript=transcription["transcript"]
    conversation=Conversation(customer_id=customer.id,title=transcript[:160],primary_intent=analysis.intent,sentiment=analysis.sentiment,resolution_status="Unresolved" if analysis.complaint else "Answered",summary=f"Uploaded voice recording analyzed as {analysis.sentiment.lower()} sentiment with {analysis.intent.lower()} intent.");db.add(conversation);db.flush()
    message=Message(conversation_id=conversation.id,role="user",content=transcript);db.add(message);db.flush()
    interaction=InteractionAnalysis(message_id=message.id,intent=analysis.intent,sentiment=analysis.sentiment,score=analysis.score,emotion=analysis.emotion,urgency=analysis.urgency,complaint=analysis.complaint,repeat_contact=analysis.repeat,entities=analysis.entities);db.add(interaction);db.flush()
    db.add(RoutingDecision(conversation_id=conversation.id,interaction_analysis_id=interaction.id,recommended_queue=routing["queue"],reason=routing["reason"],issue=routing["issue"],urgency=routing["urgency"],sentiment=routing["sentiment"],repeat_contact=routing["repeat_contact"],escalation=routing["escalation"]))
    result={"conversation_id":conversation.id,"customer_id":customer.id,"customer_name":customer.name,"transcript":transcript,"language_code":detected_language,"language_probability":transcription.get("language_probability"),"sentiment":analysis.sentiment,"sentiment_score":analysis.score,"emotion":analysis.emotion,"intent":analysis.intent,"urgency":analysis.urgency,"complaint":analysis.complaint,"repeat_contact":analysis.repeat,"recommended_route":routing["queue"],"routing_reason":routing["reason"]}
    db.add(AuditLog(user_id=user.id,action="VOICE_SENTIMENT_ANALYZED",entity="conversation",entity_id=str(conversation.id),metadata_json={"customer_id":customer.id,"filename":file.filename,"language_code":detected_language,"sentiment":analysis.sentiment,"intent":analysis.intent,"urgency":analysis.urgency}));db.commit()
    return result
@router.get("/conversations",tags=["Conversations"])
def conversations(user:User=Depends(current_user),db:Session=Depends(get_db)):
    q=db.query(Conversation)
    if user.user_type=="customer": q=q.filter_by(customer_id=user.customer_id)
    items=q.order_by(Conversation.updated_at.desc()).all()
    if user.user_type=="customer": return [serialize(x) for x in items]
    customers={customer.id:customer for customer in db.query(Customer).all()}
    return [{**serialize(item),"customer_name":customers[item.customer_id].name if item.customer_id in customers else "Unknown customer","customer_code":customers[item.customer_id].customer_code if item.customer_id in customers else str(item.customer_id),"message_count":db.query(Message).filter_by(conversation_id=item.id).count()} for item in items]
@router.get("/sentiment/recent",tags=["Bank Intelligence"])
def recent_sentiment(limit:int=10,user:User=Depends(bank_user),db:Session=Depends(get_db)):
    limit=max(1,min(limit,50))
    rows=db.query(InteractionAnalysis,Message,Conversation,Customer).join(Message,InteractionAnalysis.message_id==Message.id).join(Conversation,Message.conversation_id==Conversation.id).join(Customer,Conversation.customer_id==Customer.id).order_by(Message.created_at.desc()).limit(limit).all()
    return [{"analysis_id":analysis.id,"conversation_id":conversation.id,"customer_id":customer.id,"customer_name":customer.name,"message":message.content,"sentiment":analysis.sentiment,"emotion":analysis.emotion,"score":analysis.score,"intent":analysis.intent,"urgency":analysis.urgency,"created_at":message.created_at} for analysis,message,conversation,customer in reversed(rows)]
@router.get("/customers/{customer_id}/sentiment-history",tags=["Bank Intelligence"])
def customer_sentiment_history(customer_id:int,limit:int=10,user:User=Depends(bank_user),db:Session=Depends(get_db)):
    customer=db.get(Customer,customer_id)
    if not customer: raise HTTPException(404,"Customer not found")
    limit=max(1,min(limit,50))
    conversations=db.query(Conversation).filter_by(customer_id=customer_id).order_by(Conversation.updated_at.desc()).limit(limit).all()
    score_map={"Highly Negative":-.9,"Negative":-.5,"Neutral":0,"Positive":.6}
    result=[]
    for conversation in reversed(conversations):
        latest=db.query(InteractionAnalysis).join(Message).filter(Message.conversation_id==conversation.id).order_by(Message.created_at.desc()).first()
        feedback=db.query(CustomerFeedback).filter_by(conversation_id=conversation.id).order_by(CustomerFeedback.created_at.desc()).first()
        result.append({"conversation_id":conversation.id,"title":conversation.title,"intent":conversation.primary_intent,"sentiment":latest.sentiment if latest else conversation.sentiment,"emotion":latest.emotion if latest else "Unknown","score":latest.score if latest else score_map.get(conversation.sentiment,0),"resolution_status":conversation.resolution_status,"csat":feedback.csat if feedback else None,"nps":feedback.nps if feedback else None,"updated_at":conversation.updated_at})
    return {"customer_id":customer.id,"customer_name":customer.name,"sessions":result}
@router.get("/conversations/{conversation_id}",tags=["Conversations"])
def conversation(conversation_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    c=db.get(Conversation,conversation_id)
    if not c or (user.user_type=="customer" and c.customer_id!=user.customer_id): raise HTTPException(404,"Conversation not found")
    analysis=db.query(InteractionAnalysis).join(Message).filter(Message.conversation_id==c.id).order_by(Message.created_at.asc()).all()
    routing=db.query(RoutingDecision).filter_by(conversation_id=c.id).order_by(RoutingDecision.id.desc()).first()
    lead=db.query(Lead).filter_by(conversation_id=c.id).first()
    request=db.query(ServiceRequest).filter_by(conversation_id=c.id).first()
    feedback=db.query(CustomerFeedback).filter_by(conversation_id=c.id).order_by(CustomerFeedback.created_at.desc()).first()
    return {**serialize(c),"messages":[serialize(x) for x in c.messages],"analysis":[serialize(x) for x in analysis],"routing":serialize(routing) if routing else None,"lead":serialize(lead) if lead else None,"service_request":serialize(request) if request else None,"insights":conversation_insights(c,analysis,routing,request,feedback)}

@router.post("/service-requests",tags=["Service Requests"])
def create_request(payload:ServiceCreate,user:User=Depends(current_user),db:Session=Depends(get_db)):
    if user.user_type!="customer" or not user.customer_id: raise HTTPException(403)
    decision=db.query(RoutingDecision).filter_by(conversation_id=payload.conversation_id).order_by(RoutingDecision.id.desc()).first() if payload.conversation_id else None
    priority="High" if decision and decision.recommended_queue!="Standard Queue" else payload.priority
    count=db.query(ServiceRequest).count()+1; item=ServiceRequest(request_code=f"SR-{datetime.utcnow().year}-{count:06d}",customer_id=user.customer_id,conversation_id=payload.conversation_id,category=payload.category,issue=payload.issue,priority=priority,assigned_queue=decision.current_queue if decision else "Standard Queue",escalation_level="None",routing_reason=decision.reason if decision else "")
    db.add(item);db.flush()
    if decision:decision.service_request_id=item.id
    db.add(Notification(title=f"New {priority.lower()} priority service request requires review",severity="critical" if priority=="High" else "warning",customer_id=user.customer_id)); db.commit(); db.refresh(item); return serialize(item)
@router.get("/service-requests",tags=["Service Requests"])
def requests(user:User=Depends(current_user),db:Session=Depends(get_db)):
    q=db.query(ServiceRequest)
    if user.user_type=="customer": q=q.filter_by(customer_id=user.customer_id)
    items=q.order_by(ServiceRequest.created_at.desc()).all();customers={item.id:item for item in db.query(Customer).filter(Customer.id.in_([row.customer_id for row in items])).all()} if items else {}
    return [{**serialize(item),"customer_code":customers[item.customer_id].customer_code if item.customer_id in customers else str(item.customer_id),"customer_name":customers[item.customer_id].name if item.customer_id in customers else "Unknown customer"} for item in items]
@router.patch("/service-requests/{request_id}",tags=["Service Requests"])
def update_service_request(request_id:int,payload:ServiceRequestUpdate,user:User=Depends(bank_user),db:Session=Depends(get_db)):
    item=db.get(ServiceRequest,request_id)
    if not item: raise HTTPException(404,"Service request not found")
    previous=item.status; item.status=payload.status
    if item.conversation_id:
        conversation=db.get(Conversation,item.conversation_id)
        if conversation: conversation.resolution_status="Resolved" if payload.status in ["Resolved","Closed"] else "Unresolved"
    refresh_customer_retention(db,item.customer_id);db.add(AuditLog(user_id=user.id,action="SERVICE_REQUEST_STATUS_CHANGED",entity="service_request",entity_id=str(item.id),metadata_json={"from":previous,"to":payload.status}))
    db.commit();db.refresh(item);customer=db.get(Customer,item.customer_id);return {**serialize(item),"customer_code":customer.customer_code if customer else str(item.customer_id),"customer_name":customer.name if customer else "Unknown customer"}
@router.get("/service-requests/{request_id}/comments",tags=["Service Requests"])
def service_request_comments(request_id:int,user:User=Depends(bank_user),db:Session=Depends(get_db)):
    if not db.get(ServiceRequest,request_id): raise HTTPException(404,"Service request not found")
    rows=db.query(ServiceRequestComment,User.display_name).join(User,User.id==ServiceRequestComment.author_id).filter(ServiceRequestComment.service_request_id==request_id).order_by(ServiceRequestComment.created_at.asc()).all()
    return [{**serialize(comment),"author_name":author_name} for comment,author_name in rows]
@router.post("/service-requests/{request_id}/comments",tags=["Service Requests"])
def add_service_request_comment(request_id:int,payload:ServiceRequestCommentCreate,user:User=Depends(bank_user),db:Session=Depends(get_db)):
    if not db.get(ServiceRequest,request_id): raise HTTPException(404,"Service request not found")
    item=ServiceRequestComment(service_request_id=request_id,author_id=user.id,comment=payload.comment.strip());db.add(item);db.flush()
    db.add(AuditLog(user_id=user.id,action="SERVICE_REQUEST_COMMENT_ADDED",entity="service_request",entity_id=str(request_id),metadata_json={"comment_id":item.id}))
    db.commit();db.refresh(item);return {**serialize(item),"author_name":user.display_name}
def accessible_service_request(request_id:int,user:User,db:Session)->ServiceRequest:
    item=db.get(ServiceRequest,request_id)
    if not item: raise HTTPException(404,"Service request not found")
    if user.user_type=="customer" and item.customer_id!=user.customer_id: raise HTTPException(403,"This request belongs to another customer")
    return item
@router.get("/service-requests/{request_id}/messages",tags=["Service Requests"])
def service_request_messages(request_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    accessible_service_request(request_id,user,db)
    rows=db.query(ServiceRequestMessage,User.display_name).join(User,User.id==ServiceRequestMessage.sender_id).filter(ServiceRequestMessage.service_request_id==request_id).order_by(ServiceRequestMessage.created_at.asc()).all()
    return [{**serialize(message),"sender_name":sender_name} for message,sender_name in rows]
@router.post("/service-requests/{request_id}/messages",tags=["Service Requests"])
def add_service_request_message(request_id:int,payload:ServiceRequestMessageCreate,user:User=Depends(current_user),db:Session=Depends(get_db)):
    request=accessible_service_request(request_id,user,db)
    item=ServiceRequestMessage(service_request_id=request_id,sender_id=user.id,sender_type=user.user_type,message=payload.message.strip());db.add(item);db.flush()
    if user.user_type=="customer": db.add(Notification(title=f"Customer replied on {request.request_code}",severity="info",customer_id=request.customer_id))
    db.add(AuditLog(user_id=user.id,action="SERVICE_REQUEST_MESSAGE_SENT",entity="service_request",entity_id=str(request_id),metadata_json={"message_id":item.id,"sender_type":user.user_type}))
    db.commit();db.refresh(item);return {**serialize(item),"sender_name":user.display_name}
@router.post("/feedback",tags=["Customer AI"])
def feedback(payload:FeedbackCreate,user:User=Depends(current_user),db:Session=Depends(get_db)):
    conversation=db.get(Conversation,payload.conversation_id)
    if not conversation: raise HTTPException(404,"Conversation not found")
    if user.user_type=="customer" and conversation.customer_id!=user.customer_id: raise HTTPException(403,"This conversation belongs to another customer")
    item=CustomerFeedback(**payload.model_dump()); db.add(item);db.flush();refresh_customer_retention(db,conversation.customer_id);db.commit(); return {"status":"recorded","csat":item.csat,"nps":item.nps}
@router.get("/financial-goals",tags=["Financial Goals"])
def goals(user:User=Depends(current_user),db:Session=Depends(get_db)):
    q=db.query(FinancialGoal)
    if user.user_type=="customer": q=q.filter_by(customer_id=user.customer_id)
    return [serialize(x) for x in q.all()]

@router.get("/dashboard",tags=["Bank Intelligence"])
def dashboard(user:User=Depends(bank_user),db:Session=Depends(get_db)):
    now=datetime.utcnow();today=now.replace(hour=0,minute=0,second=0,microsecond=0);trend_start=today-timedelta(days=6)
    conv=db.query(Conversation).filter(Conversation.created_at>=today).count()
    open_sr=db.query(ServiceRequest).filter(ServiceRequest.status.notin_(["Resolved","Closed"])).count()
    hot=db.query(Lead).filter(Lead.temperature=="Hot",Lead.status.notin_(["Abandoned","Converted"])).count()
    latest_retention={}
    for item in db.query(RetentionScore).order_by(RetentionScore.updated_at.desc(),RetentionScore.id.desc()).all():
        latest_retention.setdefault(item.customer_id,item)
    high=sum(item.level in ["High","Critical"] and item.status!="Closed" for item in latest_retention.values())
    sentiments=dict(db.query(Conversation.sentiment,func.count(Conversation.id)).group_by(Conversation.sentiment).all())
    customer_ids=[row[0] for row in db.query(Customer.id).all()]
    experience=[customer_experience_scores(db,customer_id) for customer_id in customer_ids]
    csat=round(sum(item["csat"] for item in experience)/len(experience),1) if experience else 3.0
    nps=round(sum(item["nps"] for item in experience)/len(experience)) if experience else 0
    scored_sessions=sum(item["sessions"] for item in experience);defaulted_sessions=sum(item["defaulted_sessions"] for item in experience)
    trend_counts={}
    for row in db.query(Conversation).filter(Conversation.created_at>=trend_start).all():trend_counts[row.created_at.date()]=trend_counts.get(row.created_at.date(),0)+1
    conversation_trend=[{"day":(trend_start+timedelta(days=offset)).strftime("%a"),"date":(trend_start+timedelta(days=offset)).date().isoformat(),"count":trend_counts.get((trend_start+timedelta(days=offset)).date(),0)} for offset in range(7)]
    lead_stages=[("New","New"),("In Qualification","In Qualification"),("Qualified","Qualified"),("Abandoned","Abandoned"),("Converted","Converted")]
    lead_funnel=[{"stage":label,"value":db.query(Lead).filter(Lead.status==status).count()} for label,status in lead_stages]
    priority=db.query(RoutingDecision).filter(RoutingDecision.recommended_queue!="Standard Queue",RoutingDecision.status=="Recommended").count()
    return {"kpis":{"conversations":conv,"active_customers":len(customer_ids),"open_requests":open_sr,"hot_leads":hot,"high_risk":high,"priority_escalations":priority,"csat":csat,"nps":nps,"experience_customers":len(experience),"experience_sessions":scored_sessions,"defaulted_sessions":defaulted_sessions},"sentiments":sentiments,"conversation_trend":conversation_trend,"lead_funnel":lead_funnel}
@router.get("/customers",tags=["Customer 360"])
def customers(user:User=Depends(bank_user),db:Session=Depends(get_db)): return [serialize(x) for x in db.query(Customer).all()]
@router.get("/customers/{customer_id}/360",tags=["Customer 360"])
def customer360(customer_id:int,user:User=Depends(bank_user),db:Session=Depends(get_db)):
    c=db.get(Customer,customer_id)
    if not c: raise HTTPException(404)
    db.add(AuditLog(user_id=user.id,action="CUSTOMER_PROFILE_VIEWED",entity="customer",entity_id=str(c.id))); db.commit()
    conv=db.query(Conversation).filter_by(customer_id=c.id).all(); req=db.query(ServiceRequest).filter_by(customer_id=c.id).all(); leads=db.query(Lead).filter_by(customer_id=c.id).all(); opp=db.query(Opportunity).filter_by(customer_id=c.id).all(); risk=db.query(RetentionScore).filter_by(customer_id=c.id).order_by(RetentionScore.created_at.desc()).first(); goals=db.query(FinancialGoal).filter_by(customer_id=c.id).all()
    insights=[f"{c.segment} customer since {c.relationship_since}",f"Maintains an average balance of ₹{c.average_balance:,.0f}"]
    if req: insights.append(f"{sum(x.status!='Resolved' for x in req)} unresolved service request(s)")
    if leads: insights.append(f"Active {leads[0].product} interest with {leads[0].temperature.lower()} lead temperature")
    if risk: insights.append(f"{risk.level} attrition risk; prioritize service recovery" if risk.level in ["High","Critical"] else f"{risk.level} attrition risk")
    engagement=customer_engagement(db,c.id)
    recommended=[engagement["action"]]
    if engagement.get("warning"):recommended+= ["Prioritize service recovery before promotional outreach","Keep all outbound communication subject to employee approval"]
    else:recommended+= ["Review next-best-product relevance with the customer","Keep all outbound communication subject to employee approval"]
    return {"customer":serialize(c),"conversations":[serialize(x) for x in conv],"service_requests":[serialize(x) for x in req],"leads":[serialize(x) for x in leads],"opportunities":[serialize(x) for x in opp],"retention":serialize(risk) if risk else None,"goals":[serialize(x) for x in goals],"ai_insights":insights,"engagement":engagement,"recommended_actions":recommended}
@router.get("/leads",tags=["Bank Intelligence"])
def leads(user:User=Depends(bank_user),db:Session=Depends(get_db)): return [serialize(x) for x in db.query(Lead).order_by(Lead.created_at.desc()).all()]
@router.post("/leads/{lead_id}/abandon",tags=["Lead Qualification"])
def abandon_lead(lead_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    lead=db.get(Lead,lead_id)
    if not lead:raise HTTPException(404,"Lead not found")
    if user.user_type=="customer" and lead.customer_id!=user.customer_id:raise HTTPException(403,"This lead belongs to another customer")
    if lead.status=="Qualified" or not lead.qualification_data:return {**serialize(lead),"drop_off_created":False}
    lead.status="Abandoned";lead.drop_off_detected=True;lead.next_action=f"Send reviewed nudge to resume at {lead.journey_stage} stage"
    opportunity=db.query(Opportunity).filter_by(customer_id=lead.customer_id,product="Home Loan Follow-up",trigger=f"Drop-off at {lead.journey_stage}").first()
    if not opportunity:
        opportunity=Opportunity(customer_id=lead.customer_id,product="Home Loan Follow-up",score=lead.score,reason=f"Customer began home-loan qualification and exited after providing {len(lead.qualification_data)} field(s)",trigger=f"Drop-off at {lead.journey_stage}",suggested_action=lead.next_action,status="Pending Review");db.add(opportunity)
    refresh_customer_retention(db,lead.customer_id);db.add(Notification(title=f"Home-loan journey abandoned at {lead.journey_stage}",severity="warning",customer_id=lead.customer_id));db.commit();db.refresh(lead)
    return {**serialize(lead),"drop_off_created":True}
@router.get("/opportunities",tags=["Bank Intelligence"])
def opportunities(user:User=Depends(bank_user),db:Session=Depends(get_db)):
    customers={item.id:item for item in db.query(Customer).all()}
    rows=db.query(Opportunity).order_by(Opportunity.created_at.desc()).all()
    for item in rows:
        customer=customers.get(item.customer_id)
        formatted=format_customer_message(item.communication_draft,customer.name if customer else None)
        if item.communication_draft!=formatted:item.communication_draft=formatted
    db.commit()
    return [{**serialize(item),"customer_code":customers[item.customer_id].customer_code if item.customer_id in customers else str(item.customer_id),"customer_name":customers[item.customer_id].name if item.customer_id in customers else "Unknown customer","customer_email":customers[item.customer_id].email_address if item.customer_id in customers else "","customer_phone":customers[item.customer_id].phone_number if item.customer_id in customers else "","engagement":customer_engagement(db,item.customer_id)} for item in rows]
@router.post("/opportunities/refresh",tags=["Bank Intelligence"])
def refresh_opportunities(user:User=Depends(bank_user),db:Session=Depends(get_db)):
    created=identify_opportunities(db);db.add(AuditLog(user_id=user.id,action="OPPORTUNITIES_REFRESHED",entity="opportunity",entity_id="batch",metadata_json={"created":len(created)}));db.commit();return {"created":len(created)}
@router.get("/opportunities/{item_id}/engagement",tags=["Bank Intelligence"])
def opportunity_engagement(item_id:int,user:User=Depends(bank_user),db:Session=Depends(get_db)):
    item=db.get(Opportunity,item_id)
    if not item: raise HTTPException(404,"Opportunity not found")
    return {"opportunity_id":item.id,"customer_id":item.customer_id,"engagement":customer_engagement(db,item.customer_id),"checked_at":datetime.utcnow()}
@router.patch("/opportunities/{item_id}",tags=["Bank Intelligence"])
def update_opportunity(item_id:int,payload:OpportunityReview,user:User=Depends(bank_user),db:Session=Depends(get_db)):
    item=db.get(Opportunity,item_id)
    if not item: raise HTTPException(404)
    engagement=customer_engagement(db,item.customer_id)
    if payload.status=="Approved" and not engagement["eligible"]:raise HTTPException(409,f"Engagement blocked: {engagement['action']}")
    item.status=payload.status;item.communication_draft=payload.communication_draft.strip();item.reviewed_by=user.id;item.reviewed_at=datetime.utcnow()
    db.add(AuditLog(user_id=user.id,action="OPPORTUNITY_REVIEWED",entity="opportunity",entity_id=str(item.id),metadata_json={"status":payload.status,"engagement_state":engagement["state"]})); db.commit(); return {**serialize(item),"engagement":engagement}
@router.post("/opportunities/{item_id}/send-email",tags=["Bank Intelligence"])
def email_opportunity(item_id:int,payload:OpportunityEmailSend,user:User=Depends(bank_user),db:Session=Depends(get_db)):
    item=db.get(Opportunity,item_id)
    if not item:raise HTTPException(404,"Opportunity not found")
    if item.status!="Approved":raise HTTPException(409,"Approve the communication before sending email")
    engagement=customer_engagement(db,item.customer_id)
    if not engagement["eligible"]:raise HTTPException(409,f"Email blocked: {engagement['action']}")
    customer=db.get(Customer,item.customer_id)
    if not customer or not customer.email_address:raise HTTPException(409,"Customer email address is unavailable")
    message=format_customer_message(payload.message,customer.name)
    try:message_id=send_transactional_email(payload.recipient,customer.name,payload.subject,message)
    except RuntimeError as exc:raise HTTPException(502,str(exc))
    item.status="Email Sent"
    db.add(AuditLog(user_id=user.id,action="OPPORTUNITY_EMAIL_SENT",entity="opportunity",entity_id=str(item.id),metadata_json={"customer_id":customer.id,"recipient":payload.recipient,"provider":"transactional_email","message_id":message_id}));db.commit()
    return {"status":item.status,"recipient":payload.recipient,"subject":payload.subject,"message_id":message_id}

@router.get("/retention",tags=["Bank Intelligence"])
def retention_list(user:User=Depends(bank_user),db:Session=Depends(get_db)):
    items=refresh_all_retention(db);customers={item.id:item for item in db.query(Customer).all()}
    for item in items:
        customer=customers.get(item.customer_id)
        item.communication_draft=format_customer_message(item.communication_draft,customer.name if customer else None)
    db.commit()
    result=[]
    for item in items:
        customer=customers.get(item.customer_id)
        conversation=db.query(Conversation).filter_by(customer_id=item.customer_id).order_by(Conversation.updated_at.desc(),Conversation.id.desc()).first()
        activity_at=conversation.updated_at if conversation else item.created_at
        result.append({**serialize(item),"customer_name":customer.name if customer else "Unknown customer","customer_code":customer.customer_code if customer else str(item.customer_id),"email_address":customer.email_address if customer else "","phone_number":customer.phone_number if customer else "","rm_name":customer.rm_name if customer else "","activity_at":activity_at,"conversation_title":conversation.title if conversation else None,"conversation_summary":conversation.summary if conversation else None,"conversation_sentiment":conversation.sentiment if conversation else None,"conversation_resolution":conversation.resolution_status if conversation else None,"risk_summary":"; ".join(item.reasons) if item.reasons else "No material attrition signal detected"})
    return sorted(result,key=lambda row:row["activity_at"],reverse=True)
@router.post("/retention/refresh",tags=["Bank Intelligence"])
def refresh_retention_cases(user:User=Depends(bank_user),db:Session=Depends(get_db)):
    items=refresh_all_retention(db);db.add(AuditLog(user_id=user.id,action="RETENTION_REFRESHED",entity="retention",entity_id="batch",metadata_json={"customers":len(items)}));db.commit();return {"customers":len(items)}
@router.post("/retention/{item_id}/regenerate",tags=["Bank Intelligence"])
def regenerate_retention_case(item_id:int,user:User=Depends(bank_user),db:Session=Depends(get_db)):
    item=db.get(RetentionScore,item_id)
    if not item:raise HTTPException(404,"Retention case not found")
    item.communication_draft="";item=refresh_customer_retention(db,item.customer_id,generate_message=True)
    db.add(AuditLog(user_id=user.id,action="RETENTION_MESSAGE_REGENERATED",entity="retention",entity_id=str(item.id)));db.commit();db.refresh(item);return serialize(item)
@router.patch("/retention/{item_id}",tags=["Bank Intelligence"])
def review_retention_case(item_id:int,payload:RetentionReview,user:User=Depends(bank_user),db:Session=Depends(get_db)):
    item=db.get(RetentionScore,item_id)
    if not item:raise HTTPException(404,"Retention case not found")
    item.status=payload.status;item.communication_draft=payload.communication_draft.strip();item.reviewed_by=user.id;item.reviewed_at=datetime.utcnow();db.add(AuditLog(user_id=user.id,action="RETENTION_CASE_REVIEWED",entity="retention",entity_id=str(item.id),metadata_json={"status":payload.status}));db.commit();return serialize(item)
@router.post("/retention/{item_id}/send-email",tags=["Bank Intelligence"])
def email_retention_case(item_id:int,payload:OpportunityEmailSend,user:User=Depends(bank_user),db:Session=Depends(get_db)):
    item=db.get(RetentionScore,item_id)
    if not item:raise HTTPException(404,"Retention case not found")
    if item.status!="Content Approved":raise HTTPException(409,"Approve the retention communication before sending email")
    customer=db.get(Customer,item.customer_id)
    if not customer:raise HTTPException(404,"Customer not found")
    message=format_customer_message(payload.message,customer.name)
    try:message_id=send_transactional_email(payload.recipient,customer.name,payload.subject,message)
    except RuntimeError as exc:raise HTTPException(502,str(exc))
    db.add(AuditLog(user_id=user.id,action="RETENTION_EMAIL_SENT",entity="retention",entity_id=str(item.id),metadata_json={"customer_id":customer.id,"recipient":payload.recipient,"provider":"transactional_email","message_id":message_id}));db.commit()
    return {"status":item.status,"recipient":payload.recipient,"message_id":message_id}
@router.get("/routing",tags=["Bank Intelligence"])
def routing_list(user:User=Depends(bank_user),db:Session=Depends(get_db)):
    rows=db.query(RoutingDecision,Conversation,Customer).join(Conversation,RoutingDecision.conversation_id==Conversation.id).join(Customer,Conversation.customer_id==Customer.id).order_by(RoutingDecision.created_at.desc()).all()
    return [{**serialize(decision),"customer_id":customer.id,"customer_name":customer.name,"message":db.query(Message).join(InteractionAnalysis,InteractionAnalysis.message_id==Message.id).filter(InteractionAnalysis.id==decision.interaction_analysis_id).with_entities(Message.content).scalar()} for decision,conversation,customer in rows]
@router.patch("/routing/{decision_id}",tags=["Bank Intelligence"])
def action_routing(decision_id:int,payload:RoutingAction,user:User=Depends(bank_user),db:Session=Depends(get_db)):
    decision=db.get(RoutingDecision,decision_id)
    if not decision:raise HTTPException(404,"Routing decision not found")
    decision.status=payload.status;decision.actioned_by=user.id;decision.actioned_at=datetime.utcnow()
    if payload.status=="Applied":decision.current_queue=decision.recommended_queue
    if payload.status=="Applied" and decision.service_request_id:
        request=db.get(ServiceRequest,decision.service_request_id)
        if request:
            request.priority="High" if decision.recommended_queue!="Standard Queue" else request.priority
            request.assigned_queue=decision.recommended_queue;request.escalation_level=decision.escalation;request.routing_reason=decision.reason
    db.add(AuditLog(user_id=user.id,action="ROUTING_DECISION_ACTIONED",entity="routing",entity_id=str(decision.id),metadata_json={"status":payload.status,"queue":decision.recommended_queue,"service_request_id":decision.service_request_id}));db.commit();return serialize(decision)
@router.get("/notifications",tags=["Bank Intelligence"])
def notifications(user:User=Depends(bank_user),db:Session=Depends(get_db)): return [serialize(x) for x in db.query(Notification).order_by(Notification.created_at.desc()).all()]
@router.get("/analytics",tags=["Bank Intelligence"])
def analytics(user:User=Depends(bank_user),db:Session=Depends(get_db)): return dashboard(user,db)

@router.get("/knowledge",tags=["Administration"])
def knowledge(user:User=Depends(admin_user),db:Session=Depends(get_db)): return [serialize(x) for x in db.query(KnowledgeArticle).all()]
@router.post("/knowledge",tags=["Administration"])
def add_knowledge(payload:KnowledgeCreate,user:User=Depends(admin_user),db:Session=Depends(get_db)):
    item=KnowledgeArticle(**payload.model_dump()); db.add(item); db.flush(); db.add(AuditLog(user_id=user.id,action="KNOWLEDGE_CREATED",entity="knowledge",entity_id=str(item.id))); db.commit(); return serialize(item)
@router.get("/admin/knowledge/documents",tags=["Administration"])
def knowledge_documents(user:User=Depends(admin_user),db:Session=Depends(get_db)):
    return [{"id":item.id,"filename":item.filename,"title":item.title,"classification":item.classification,"audience":item.audience,"status":item.status,"page_count":item.page_count,"chunk_count":item.chunk_count,"error_message":item.error_message,"created_at":item.created_at} for item in db.query(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc()).all()]
@router.post("/admin/knowledge/documents",tags=["Administration"])
async def upload_knowledge_document(title:str=Form(""),customer_visible:bool=Form(False),file:UploadFile=File(...),user:User=Depends(admin_user),db:Session=Depends(get_db)):
    if file.content_type not in ["application/pdf","application/x-pdf"] or not file.filename.lower().endswith(".pdf"): raise HTTPException(400,"Only PDF documents are supported")
    data=await file.read(MAX_PDF_BYTES+1)
    try: document=ingest_pdf(db,data,file.filename,title,"customer" if customer_visible else "employee",user.id)
    except ValueError as exc: raise HTTPException(400,str(exc))
    db.add(AuditLog(user_id=user.id,action="PDF_KNOWLEDGE_INGESTED",entity="knowledge_document",entity_id=str(document.id),metadata_json={"filename":document.filename,"pages":document.page_count,"chunks":document.chunk_count,"audience":document.audience}));db.commit()
    return {"id":document.id,"title":document.title,"status":document.status,"audience":document.audience,"page_count":document.page_count,"chunk_count":document.chunk_count}
@router.patch("/admin/knowledge/documents/{document_id}",tags=["Administration"])
def update_knowledge_document(document_id:int,payload:ActionUpdate,user:User=Depends(admin_user),db:Session=Depends(get_db)):
    document=db.get(KnowledgeDocument,document_id)
    if not document:raise HTTPException(404,"Knowledge document not found")
    if payload.status not in ["Approved","Internal","Inactive"]:raise HTTPException(400,"Status must be Approved, Internal, or Inactive")
    document.status=payload.status
    if payload.status=="Approved":document.audience="customer"
    db.add(AuditLog(user_id=user.id,action="PDF_KNOWLEDGE_STATUS_CHANGED",entity="knowledge_document",entity_id=str(document.id),metadata_json={"status":payload.status,"audience":document.audience}));db.commit()
    return {"id":document.id,"status":document.status,"audience":document.audience}
@router.delete("/admin/knowledge/documents/{document_id}",tags=["Administration"])
def delete_knowledge_document(document_id:int,user:User=Depends(admin_user),db:Session=Depends(get_db)):
    document=db.get(KnowledgeDocument,document_id)
    if not document:raise HTTPException(404,"Knowledge document not found")
    metadata={"filename":document.filename,"title":document.title,"pages":document.page_count,"chunks":document.chunk_count}
    db.delete(document);db.flush()
    db.add(AuditLog(user_id=user.id,action="PDF_KNOWLEDGE_DELETED",entity="knowledge_document",entity_id=str(document_id),metadata_json=metadata));db.commit()
    return {"id":document_id,"deleted":True}
@router.get("/admin/users",tags=["Administration"])
def users(user:User=Depends(admin_user),db:Session=Depends(get_db)): return [{k:v for k,v in serialize(x).items() if k!="password_hash"} for x in db.query(User).all()]
@router.get("/admin/audit-logs",tags=["Administration"])
def audits(user:User=Depends(admin_user),db:Session=Depends(get_db)): return [serialize(x) for x in db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(200)]
@router.get("/admin/routing-rules",tags=["Administration"])
def routing_rules(user:User=Depends(admin_user)): return [{"condition":"Highly Negative + Repeat Contact","route":"Priority Service Queue"},{"condition":"Highly Negative + Financial Dispute","route":"Supervisor Review"},{"condition":"High Urgency","route":"Priority Service Queue"},{"condition":"Neutral Routine Query","route":"Standard Queue"}]
@router.get("/admin/ai-settings",tags=["Administration"])
def ai_settings(user:User=Depends(admin_user)):
    model=settings.sarvam_chat_model if settings.ai_provider=="sarvam" else settings.ollama_model if settings.ai_provider=="ollama" else "Deterministic Rules v1"
    endpoint=settings.sarvam_base_url if settings.ai_provider=="sarvam" else settings.ollama_base_url if settings.ai_provider=="ollama" else None
    return {"provider":settings.ai_provider,"model":model,"status":"Configured","temperature":0.2 if settings.ai_provider in ["ollama","sarvam"] else 0,"endpoint":endpoint,"secrets":"Server-side only"}
