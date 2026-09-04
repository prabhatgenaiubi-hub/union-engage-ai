from typing import Literal
from pydantic import BaseModel, Field
class LoginRequest(BaseModel): login_id:str=Field(min_length=3); password:str=Field(min_length=4)
class TokenResponse(BaseModel): access_token:str; token_type:str="bearer"; role:str; user_type:str; display_name:str; customer_id:int|None=None
class ChatRequest(BaseModel): message:str=Field(min_length=1,max_length=2000); conversation_id:int|None=None; language_code:Literal["auto","en-IN","hi-IN","bn-IN","gu-IN","kn-IN","ml-IN","mr-IN","od-IN","pa-IN","ta-IN","te-IN"]="auto"
class ServiceCreate(BaseModel): conversation_id:int|None=None; category:str; issue:str; priority:str="Medium"
class ServiceRequestUpdate(BaseModel): status:Literal["Open","In Progress","Awaiting Customer","Resolved","Closed"]
class ServiceRequestCommentCreate(BaseModel): comment:str=Field(min_length=1,max_length=2000)
class ServiceRequestMessageCreate(BaseModel): message:str=Field(min_length=1,max_length=2000)
class FeedbackCreate(BaseModel): conversation_id:int; csat:int|None=Field(None,ge=1,le=5); nps:int|None=Field(None,ge=0,le=10)
class KnowledgeCreate(BaseModel): title:str; category:str; keywords:str; content:str; active:bool=True
class ActionUpdate(BaseModel): status:str
