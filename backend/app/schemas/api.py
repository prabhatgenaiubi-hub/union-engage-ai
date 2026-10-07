from typing import Literal
from pydantic import BaseModel, Field
class LoginRequest(BaseModel): login_id:str=Field(min_length=3); password:str=Field(min_length=4)
class RegisterRequest(BaseModel):
    user_type:Literal["customer","employee"]
    display_name:str=Field(min_length=2,max_length=100)
    login_id:str=Field(min_length=3,max_length=40,pattern=r"^[A-Za-z0-9._-]+$")
    password:str=Field(min_length=8,max_length=72)
class TokenResponse(BaseModel): access_token:str; token_type:str="bearer"; role:str; user_type:str; display_name:str; customer_id:int|None=None
class CustomerContactUpdate(BaseModel):
    phone_number:str=Field(min_length=8,max_length=20)
    email_address:str=Field(min_length=5,max_length=120)
class ChatRequest(BaseModel): mode:Literal["banking","coach"]="banking"; message:str=Field(min_length=1,max_length=2000); conversation_id:int|None=None; language_code:Literal["auto","en-IN","hi-IN","bn-IN","gu-IN","kn-IN","ml-IN","mr-IN","od-IN","pa-IN","ta-IN","te-IN"]="auto"; follow_up_action:str|None=Field(default=None,max_length=200)
class PublicChatTurn(BaseModel): role:Literal["user","assistant"]; content:str=Field(min_length=1,max_length=1000)
class PublicChatRequest(BaseModel): message:str=Field(min_length=1,max_length=1000); session_id:str|None=Field(default=None,max_length=64); language_code:str=Field(default="auto",max_length=10); history:list[PublicChatTurn]=Field(default_factory=list,max_length=8); follow_up_action:str|None=Field(default=None,max_length=200)
class ServiceCreate(BaseModel): conversation_id:int|None=None; category:str; issue:str; customer_description:str=Field(default="",max_length=500); priority:str="Medium"
class ServiceRequestUpdate(BaseModel): status:Literal["Open","In Progress","Awaiting Customer","Resolved","Closed"]
class ServiceRequestCommentCreate(BaseModel): comment:str=Field(min_length=1,max_length=2000)
class ServiceRequestMessageCreate(BaseModel): message:str=Field(min_length=1,max_length=2000)
class FeedbackCreate(BaseModel): conversation_id:int; csat:int|None=Field(None,ge=1,le=5); nps:int|None=Field(None,ge=0,le=10)
class KnowledgeCreate(BaseModel): title:str; category:str; keywords:str; content:str; active:bool=True
class ActionUpdate(BaseModel): status:str
class ChatReplyModelUpdate(BaseModel): provider:Literal["huggingface","sarvam","ollama"]
class ImageGenerationUpdate(BaseModel): enabled:bool
class CampaignImageGenerate(BaseModel):
    prompt:str=Field(min_length=10,max_length=1000)
    campaign_type:Literal["opportunity","retention"]
class OpportunityReview(BaseModel): status:Literal["Pending Review","Approved","Dismissed"]; communication_draft:str=Field(max_length=2000)
class OpportunityEmailSend(BaseModel):
    recipient:str=Field(min_length=5,max_length=120,pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    subject:str=Field(min_length=1,max_length=200)
    message:str=Field(min_length=1,max_length=5000)
    image_base64:str|None=Field(default=None,max_length=8_000_000)
    image_filename:str|None=Field(default=None,max_length=120)
    image_position:Literal["top","after_greeting","bottom","custom"]="top"
    image_width_percent:int=Field(default=100,ge=25,le=100)
    image_height_px:int=Field(default=300,ge=100,le=600)
    image_alignment:Literal["left","center","right"]="center"
class RetentionReview(BaseModel): status:Literal["Monitoring","Intervention Planned","Content Approved","Closed"]; communication_draft:str=Field(max_length=2000)
class RoutingAction(BaseModel):
    status:Literal["Applied","Dismissed"]="Applied"
    department:Literal["Customer Service","Cards","Accounts & Deposits","Loans","Digital Banking","Payments & Disputes","Fraud & Risk","Complaints & Escalations"]|None=None
    escalation_level:Literal["None","Team Lead","Manager","Senior Management","Fraud / Risk Review"]|None=None
    comment:str|None=Field(None,max_length=2000)
class FinancialGoalUpdate(BaseModel):
    name:str=Field(min_length=1,max_length=80)
    target_amount:float=Field(ge=0)
    saved_amount:float=Field(ge=0)
    timeline_months:int=Field(ge=0,le=1200)
    monthly_income:float=Field(ge=0)
    monthly_expenses:float=Field(ge=0)
