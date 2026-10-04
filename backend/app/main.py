from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import router
app=FastAPI(title=settings.app_name,description="Unified conversational intelligence for synthetic banking demonstrations",version="1.0.0")
app.add_middleware(CORSMiddleware,allow_origins=settings.cors_origins.split(","),allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
app.include_router(router)
@app.get("/health",tags=["System"])
def health(): return {"status":"healthy","ai_provider":settings.ai_provider}
