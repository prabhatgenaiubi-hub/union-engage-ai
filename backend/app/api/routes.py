from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import *
from app.schemas.api import *
from app.core.security import verify_password, create_token
from app.api.deps import current_user, bank_user, admin_user
from app.services.chat import process_message
from app.core.config import settings
from app.services.pdf_knowledge import ingest_pdf, MAX_PDF_BYTES
from app.services.sentiment import conversation_insights

router=APIRouter(prefix="/api")
def serialize(obj):
    return {c.name:getattr(obj,c.name) for c in obj.__table__.columns}
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

@router.post("/chat",tags=["Customer AI"])
def chat(payload:ChatRequest,user:User=Depends(current_user),db:Session=Depends(get_db)):
    if user.user_type!="customer" or not user.customer_id: raise HTTPException(403,"Customer access required")
    return process_message(db,user.customer_id,payload.message,payload.conversation_id,payload.language_code)
@router.get("/conversations",tags=["Conversations"])
def conversations(user:User=Depends(current_user),db:Session=Depends(get_db)):
    q=db.query(Conversation)
    if user.user_type=="customer": q=q.filter_by(customer_id=user.customer_id)
    items=q.order_by(Conversation.updated_at.desc()).all()
    if user.user_type=="customer": return [serialize(x) for x in items]
    customer_names=dict(db.query(Customer.id,Customer.name).all())
    return [{**serialize(item),"customer_name":customer_names.get(item.customer_id,"Unknown customer"),"message_count":db.query(Message).filter_by(conversation_id=item.id).count()} for item in items]
@router.get("/sentiment/recent",tags=["Bank Intelligence"])
def recent_sentiment(limit:int=10,user:User=Depends(bank_user),db:Session=Depends(get_db)):
    limit=max(1,min(limit,50))
    rows=db.query(InteractionAnalysis,Message,Conversation,Customer).join(Message,InteractionAnalysis.message_id==Message.id).join(Conversation,Message.conversation_id==Conversation.id).join(Customer,Conversation.customer_id==Customer.id).order_by(Message.created_at.desc()).limit(limit).all()
    return [{"analysis_id":analysis.id,"conversation_id":conversation.id,"customer_id":customer.id,"customer_name":customer.name,"message":message.content,"sentiment":analysis.sentiment,"emotion":analysis.emotion,"score":analysis.score,"intent":analysis.intent,"urgency":analysis.urgency,"created_at":message.created_at} for analysis,message,conversation,customer in reversed(rows)]
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
    count=db.query(ServiceRequest).count()+1; item=ServiceRequest(request_code=f"SR-{datetime.utcnow().year}-{count:06d}",customer_id=user.customer_id,conversation_id=payload.conversation_id,category=payload.category,issue=payload.issue,priority=payload.priority)
    db.add(item); db.add(Notification(title="New service request requires review",severity="warning",customer_id=user.customer_id)); db.commit(); db.refresh(item); return serialize(item)
@router.get("/service-requests",tags=["Service Requests"])
def requests(user:User=Depends(current_user),db:Session=Depends(get_db)):
    q=db.query(ServiceRequest)
    if user.user_type=="customer": q=q.filter_by(customer_id=user.customer_id)
    return [serialize(x) for x in q.order_by(ServiceRequest.created_at.desc()).all()]
@router.patch("/service-requests/{request_id}",tags=["Service Requests"])
def update_service_request(request_id:int,payload:ServiceRequestUpdate,user:User=Depends(bank_user),db:Session=Depends(get_db)):
    item=db.get(ServiceRequest,request_id)
    if not item: raise HTTPException(404,"Service request not found")
    previous=item.status; item.status=payload.status
    if item.conversation_id:
        conversation=db.get(Conversation,item.conversation_id)
        if conversation: conversation.resolution_status="Resolved" if payload.status in ["Resolved","Closed"] else "Unresolved"
    db.add(AuditLog(user_id=user.id,action="SERVICE_REQUEST_STATUS_CHANGED",entity="service_request",entity_id=str(item.id),metadata_json={"from":previous,"to":payload.status}))
    db.commit();db.refresh(item);return serialize(item)
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
    item=CustomerFeedback(**payload.model_dump()); db.add(item); db.commit(); return {"status":"recorded","csat":item.csat,"nps":item.nps}
@router.get("/financial-goals",tags=["Financial Goals"])
def goals(user:User=Depends(current_user),db:Session=Depends(get_db)):
    q=db.query(FinancialGoal)
    if user.user_type=="customer": q=q.filter_by(customer_id=user.customer_id)
    return [serialize(x) for x in q.all()]

@router.get("/dashboard",tags=["Bank Intelligence"])
def dashboard(user:User=Depends(bank_user),db:Session=Depends(get_db)):
    conv=db.query(Conversation).count(); open_sr=db.query(ServiceRequest).filter(ServiceRequest.status!="Resolved").count(); hot=db.query(Lead).filter_by(temperature="Hot").count(); high=db.query(RetentionScore).filter(RetentionScore.level.in_(["High","Critical"])).count()
    sentiments=dict(db.query(Conversation.sentiment,func.count(Conversation.id)).group_by(Conversation.sentiment).all())
    return {"kpis":{"conversations":conv,"active_customers":db.query(Customer).count(),"open_requests":open_sr,"hot_leads":hot,"high_risk":high,"priority_escalations":db.query(RoutingDecision).filter(RoutingDecision.recommended_queue!="Standard Queue").count(),"csat":4.1,"nps":42},"sentiments":sentiments,"conversation_trend":[{"day":d,"count":v} for d,v in zip(["Mon","Tue","Wed","Thu","Fri","Sat","Sun"],[18,25,21,32,28,16,24])],"lead_funnel":[{"stage":s,"value":v} for s,v in zip(["New","Qualified","Warm","Hot","Converted"],[42,31,22,14,8])]}
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
    return {"customer":serialize(c),"conversations":[serialize(x) for x in conv],"service_requests":[serialize(x) for x in req],"leads":[serialize(x) for x in leads],"opportunities":[serialize(x) for x in opp],"retention":serialize(risk) if risk else None,"goals":[serialize(x) for x in goals],"ai_insights":insights,"recommended_actions":["Resolve open complaints before promotional engagement","Follow up on active leads after service recovery","Review next-best-product opportunities with the customer"]}
@router.get("/leads",tags=["Bank Intelligence"])
def leads(user:User=Depends(bank_user),db:Session=Depends(get_db)): return [serialize(x) for x in db.query(Lead).order_by(Lead.score.desc()).all()]
@router.get("/opportunities",tags=["Bank Intelligence"])
def opportunities(user:User=Depends(bank_user),db:Session=Depends(get_db)): return [serialize(x) for x in db.query(Opportunity).order_by(Opportunity.score.desc()).all()]
@router.patch("/opportunities/{item_id}",tags=["Bank Intelligence"])
def update_opportunity(item_id:int,payload:ActionUpdate,user:User=Depends(bank_user),db:Session=Depends(get_db)):
    item=db.get(Opportunity,item_id)
    if not item: raise HTTPException(404)
    item.status=payload.status; db.add(AuditLog(user_id=user.id,action="OPPORTUNITY_UPDATED",entity="opportunity",entity_id=str(item.id),metadata_json={"status":payload.status})); db.commit(); return serialize(item)
@router.get("/retention",tags=["Bank Intelligence"])
def retention_list(user:User=Depends(bank_user),db:Session=Depends(get_db)): return [serialize(x) for x in db.query(RetentionScore).order_by(RetentionScore.score.desc()).all()]
@router.get("/routing",tags=["Bank Intelligence"])
def routing_list(user:User=Depends(bank_user),db:Session=Depends(get_db)): return [serialize(x) for x in db.query(RoutingDecision).order_by(RoutingDecision.created_at.desc()).all()]
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
