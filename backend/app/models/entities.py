from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.db.base import Base

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class User(Base, TimestampMixin):
    __tablename__="users"
    id: Mapped[int]=mapped_column(primary_key=True)
    login_id: Mapped[str]=mapped_column(String(40), unique=True, index=True)
    password_hash: Mapped[str]=mapped_column(String(255))
    user_type: Mapped[str]=mapped_column(String(20), index=True)
    role: Mapped[str]=mapped_column(String(30), default="customer")
    display_name: Mapped[str]=mapped_column(String(100))
    customer_id: Mapped[int|None]=mapped_column(ForeignKey("customers.id"), nullable=True)

class Customer(Base, TimestampMixin):
    __tablename__="customers"
    id: Mapped[int]=mapped_column(primary_key=True)
    customer_code: Mapped[str]=mapped_column(String(20), unique=True, index=True)
    name: Mapped[str]=mapped_column(String(100))
    segment: Mapped[str]=mapped_column(String(30), default="Classic")
    city: Mapped[str]=mapped_column(String(60))
    relationship_since: Mapped[str]=mapped_column(String(10))
    average_balance: Mapped[float]=mapped_column(Float, default=0)
    monthly_income: Mapped[float]=mapped_column(Float, default=0)
    monthly_surplus: Mapped[float]=mapped_column(Float, default=0)
    rm_name: Mapped[str]=mapped_column(String(100), default="Ananya Rao")

class Conversation(Base, TimestampMixin):
    __tablename__="conversations"
    id: Mapped[int]=mapped_column(primary_key=True)
    customer_id: Mapped[int]=mapped_column(ForeignKey("customers.id"), index=True)
    title: Mapped[str]=mapped_column(String(160), default="New conversation")
    primary_intent: Mapped[str]=mapped_column(String(60), default="General Banking")
    sentiment: Mapped[str]=mapped_column(String(30), default="Neutral")
    resolution_status: Mapped[str]=mapped_column(String(30), default="In Progress")
    summary: Mapped[str]=mapped_column(Text, default="")
    messages: Mapped[list["Message"]]=relationship(cascade="all, delete-orphan", order_by="Message.created_at")

class Message(Base):
    __tablename__="messages"
    id: Mapped[int]=mapped_column(primary_key=True)
    conversation_id: Mapped[int]=mapped_column(ForeignKey("conversations.id"), index=True)
    role: Mapped[str]=mapped_column(String(20))
    content: Mapped[str]=mapped_column(Text)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

class InteractionAnalysis(Base):
    __tablename__="interaction_analysis"
    id: Mapped[int]=mapped_column(primary_key=True)
    message_id: Mapped[int]=mapped_column(ForeignKey("messages.id"), index=True)
    intent: Mapped[str]=mapped_column(String(60)); sentiment: Mapped[str]=mapped_column(String(30))
    score: Mapped[float]=mapped_column(Float); emotion: Mapped[str]=mapped_column(String(30))
    urgency: Mapped[str]=mapped_column(String(20)); complaint: Mapped[bool]=mapped_column(Boolean, default=False)
    repeat_contact: Mapped[bool]=mapped_column(Boolean, default=False); entities: Mapped[dict]=mapped_column(JSON, default=dict)

class ServiceRequest(Base, TimestampMixin):
    __tablename__="service_requests"
    id: Mapped[int]=mapped_column(primary_key=True); request_code: Mapped[str]=mapped_column(String(30), unique=True)
    customer_id: Mapped[int]=mapped_column(ForeignKey("customers.id"), index=True)
    conversation_id: Mapped[int|None]=mapped_column(ForeignKey("conversations.id"), nullable=True)
    category: Mapped[str]=mapped_column(String(60)); issue: Mapped[str]=mapped_column(String(200)); priority: Mapped[str]=mapped_column(String(20)); status: Mapped[str]=mapped_column(String(30), default="Open")

class ServiceRequestComment(Base):
    __tablename__="service_request_comments"
    id: Mapped[int]=mapped_column(primary_key=True)
    service_request_id: Mapped[int]=mapped_column(ForeignKey("service_requests.id"),index=True)
    author_id: Mapped[int]=mapped_column(ForeignKey("users.id"),index=True)
    comment: Mapped[str]=mapped_column(Text)
    created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)

class ServiceRequestMessage(Base):
    __tablename__="service_request_messages"
    id: Mapped[int]=mapped_column(primary_key=True)
    service_request_id: Mapped[int]=mapped_column(ForeignKey("service_requests.id"),index=True)
    sender_id: Mapped[int]=mapped_column(ForeignKey("users.id"),index=True)
    sender_type: Mapped[str]=mapped_column(String(20))
    message: Mapped[str]=mapped_column(Text)
    created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)

class Lead(Base, TimestampMixin):
    __tablename__="leads"
    id: Mapped[int]=mapped_column(primary_key=True); customer_id: Mapped[int]=mapped_column(ForeignKey("customers.id"), index=True)
    conversation_id: Mapped[int|None]=mapped_column(ForeignKey("conversations.id"), nullable=True)
    product: Mapped[str]=mapped_column(String(60)); score: Mapped[int]=mapped_column(Integer); temperature: Mapped[str]=mapped_column(String(20))
    journey_stage: Mapped[str]=mapped_column(String(50), default="Interest"); status: Mapped[str]=mapped_column(String(30), default="New")
    next_action: Mapped[str]=mapped_column(String(120), default="Follow up"); reasons: Mapped[list]=mapped_column(JSON, default=list)

class FinancialGoal(Base, TimestampMixin):
    __tablename__="financial_goals"
    id: Mapped[int]=mapped_column(primary_key=True); customer_id: Mapped[int]=mapped_column(ForeignKey("customers.id"), index=True)
    name: Mapped[str]=mapped_column(String(80)); target_amount: Mapped[float]=mapped_column(Float); saved_amount: Mapped[float]=mapped_column(Float, default=0)
    timeline_months: Mapped[int]=mapped_column(Integer); monthly_required: Mapped[float]=mapped_column(Float)

class Opportunity(Base, TimestampMixin):
    __tablename__="product_opportunities"
    id: Mapped[int]=mapped_column(primary_key=True); customer_id: Mapped[int]=mapped_column(ForeignKey("customers.id"), index=True)
    product: Mapped[str]=mapped_column(String(60)); score: Mapped[int]=mapped_column(Integer); reason: Mapped[str]=mapped_column(Text)
    trigger: Mapped[str]=mapped_column(String(100)); suggested_action: Mapped[str]=mapped_column(String(160)); status: Mapped[str]=mapped_column(String(30), default="Pending Review")

class RetentionScore(Base, TimestampMixin):
    __tablename__="retention_scores"
    id: Mapped[int]=mapped_column(primary_key=True); customer_id: Mapped[int]=mapped_column(ForeignKey("customers.id"), index=True)
    score: Mapped[int]=mapped_column(Integer); level: Mapped[str]=mapped_column(String(20)); reasons: Mapped[list]=mapped_column(JSON, default=list); suggested_action: Mapped[str]=mapped_column(String(160))

class RoutingDecision(Base, TimestampMixin):
    __tablename__="routing_decisions"
    id: Mapped[int]=mapped_column(primary_key=True); conversation_id: Mapped[int]=mapped_column(ForeignKey("conversations.id"), index=True)
    current_queue: Mapped[str]=mapped_column(String(50), default="Standard Queue"); recommended_queue: Mapped[str]=mapped_column(String(50)); reason: Mapped[str]=mapped_column(Text); status: Mapped[str]=mapped_column(String(20), default="Recommended")

class KnowledgeArticle(Base, TimestampMixin):
    __tablename__="knowledge_articles"
    id: Mapped[int]=mapped_column(primary_key=True); title: Mapped[str]=mapped_column(String(140)); category: Mapped[str]=mapped_column(String(50)); keywords: Mapped[str]=mapped_column(String(300)); content: Mapped[str]=mapped_column(Text); active: Mapped[bool]=mapped_column(Boolean, default=True)

class KnowledgeDocument(Base, TimestampMixin):
    __tablename__="knowledge_documents"
    id: Mapped[int]=mapped_column(primary_key=True)
    filename: Mapped[str]=mapped_column(String(255))
    title: Mapped[str]=mapped_column(String(255))
    sha256: Mapped[str]=mapped_column(String(64),unique=True,index=True)
    classification: Mapped[str]=mapped_column(String(30),default="Internal")
    audience: Mapped[str]=mapped_column(String(30),default="employee")
    status: Mapped[str]=mapped_column(String(30),default="Processing",index=True)
    page_count: Mapped[int]=mapped_column(Integer,default=0)
    chunk_count: Mapped[int]=mapped_column(Integer,default=0)
    original_file: Mapped[bytes]=mapped_column(LargeBinary)
    error_message: Mapped[str|None]=mapped_column(Text,nullable=True)
    uploaded_by: Mapped[int|None]=mapped_column(ForeignKey("users.id"),nullable=True)
    chunks: Mapped[list["KnowledgeChunk"]]=relationship(cascade="all, delete-orphan")

class KnowledgeChunk(Base):
    __tablename__="knowledge_chunks"
    id: Mapped[int]=mapped_column(primary_key=True)
    document_id: Mapped[int]=mapped_column(ForeignKey("knowledge_documents.id"),index=True)
    page_number: Mapped[int]=mapped_column(Integer,index=True)
    chunk_index: Mapped[int]=mapped_column(Integer)
    content: Mapped[str]=mapped_column(Text)
    embedding: Mapped[list[float]]=mapped_column(Vector(768).with_variant(JSON,"sqlite"))

class AuditLog(Base):
    __tablename__="audit_logs"
    id: Mapped[int]=mapped_column(primary_key=True); user_id: Mapped[int|None]=mapped_column(ForeignKey("users.id"), nullable=True); action: Mapped[str]=mapped_column(String(80)); entity: Mapped[str]=mapped_column(String(60)); entity_id: Mapped[str]=mapped_column(String(40)); metadata_json: Mapped[dict]=mapped_column(JSON, default=dict); created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

class Notification(Base):
    __tablename__="notifications"
    id: Mapped[int]=mapped_column(primary_key=True); title: Mapped[str]=mapped_column(String(160)); severity: Mapped[str]=mapped_column(String(20)); customer_id: Mapped[int|None]=mapped_column(ForeignKey("customers.id"), nullable=True); read: Mapped[bool]=mapped_column(Boolean, default=False); created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

class CustomerFeedback(Base):
    __tablename__="customer_feedback"
    id: Mapped[int]=mapped_column(primary_key=True); conversation_id: Mapped[int]=mapped_column(ForeignKey("conversations.id")); csat: Mapped[int|None]=mapped_column(Integer); nps: Mapped[int|None]=mapped_column(Integer); created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)
