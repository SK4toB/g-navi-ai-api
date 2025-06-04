# 의존성 주입

# app/api/deps.py
from typing import Generator
from app.services.chat_service import ChatService

# 싱글톤 인스턴스
_chat_service_instance = None

def get_chat_service() -> ChatService:
    """
    ChatService 싱글톤 인스턴스 반환
    모든 API 엔드포인트에서 동일한 인스턴스 사용
    """
    global _chat_service_instance
    
    if _chat_service_instance is None:
        print("ChatService 싱글톤 인스턴스 생성")
        _chat_service_instance = ChatService()
    
    return _chat_service_instance

def common_parameters():
    """공통 파라미터들"""
    pass