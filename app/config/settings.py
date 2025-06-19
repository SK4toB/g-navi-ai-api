# app/config/settings.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # OpenAI 설정
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-3.5-turbo"
    openai_max_tokens: int = 1000
    openai_temperature: float = 0.7
    
    # ChromaDB 설정
    chroma_host: str = "chromadb-1.chromadb"  # k8s 내부 접근
    chroma_port: int = 8000
    chroma_auth_provider: str = "basic"
    chroma_auth_credentials: Optional[str] = None  # 환경변수에서 읽어옴
    chroma_collection_name: str = "gnavi4_dev_collection"  # 기본값은 개발용
    
    # 외부 접근용 (개발/테스트 시)
    chroma_external_url: Optional[str] = "https://chromadb-1.skala25a.project.skala-ai.com"
    chroma_use_external: bool = True  # 개발환경 기본값은 외부 URL 사용

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