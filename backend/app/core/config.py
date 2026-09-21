from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Union Engage AI"
    database_url: str = "sqlite:///./union_engage.db"
    jwt_secret: str = "local-demo-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    ai_provider: str = "mock"
    sarvam_api_key: str = ""
    sarvam_base_url: str = "https://api.sarvam.ai"
    sarvam_chat_model: str = "sarvam-105b-conversations"
    sarvam_speech_model: str = "saaras:v3"
    sarvam_timeout_seconds: int = 90
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3:latest"
    ollama_timeout_seconds: int = 90
    ollama_embedding_model: str = "nomic-embed-text:latest"
    ollama_embedding_timeout_seconds: int = 180
    brevo_api_key: str = ""
    smtp_from_email: str = ""
    smtp_from_name: str = "UNION-ENGAGE-AI"
    smtp_host: str = "smtp-relay.brevo.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    brevo_timeout_seconds: int = 20
    cors_origins: str = "http://localhost:3000"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
settings = Settings()
