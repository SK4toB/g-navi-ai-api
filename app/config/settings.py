# app/config/settings.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # OpenAI 설정
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"
    openai_max_tokens: int = 4096
    openai_temperature: float = 0.3
    
    # API 설정
    api_title: str = "AI Chatbot API"
    api_version: str = "1.0.0"
    api_description: str = "FastAPI 기반 AI 채팅 서비스"
    
    # 서버 설정
    host: str = "0.0.0.0"
    port: int = 8001
    debug: bool = False
    
    # CORS 설정
    cors_origins: list = ["*"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()