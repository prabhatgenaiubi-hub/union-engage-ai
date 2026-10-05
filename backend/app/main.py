from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import router
from app.db.session import SessionLocal
from app.models import AppSetting
app=FastAPI(title=settings.app_name,description="Unified conversational intelligence for synthetic banking demonstrations",version="1.0.0")
app.add_middleware(CORSMiddleware,allow_origins=settings.cors_origins.split(","),allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
app.include_router(router)
@app.on_event("startup")
def restore_chat_reply_model():
    db=SessionLocal()
    try:
        saved=db.get(AppSetting,"chat_reply_provider")
        if saved and saved.value in {"huggingface","sarvam","ollama"}:settings.chat_reply_provider=saved.value
    finally: db.close()
@app.get("/health",tags=["System"])
def health(): return {"status":"healthy","ai_provider":settings.ai_provider}
