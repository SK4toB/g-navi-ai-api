# app/core/dependencies.py
"""
* @className : Core Dependencies
* @description : 핵심 의존성 모듈
*                애플리케이션의 핵심 의존성을 관리하는 모듈입니다.
*                서비스 컨테이너와 주요 컴포넌트 인스턴스를 제공합니다.
*
"""
from functools import lru_cache
from typing import Annotated
from fastapi import Depends

from app.services.chat_service import ChatService
from app.services.conversation_history_manager import ConversationHistoryManager
from app.services.chroma_service import ChromaService

class ServiceContainer:
    """
    서비스 컨테이너 - 싱글톤 관리
    전역 변수 대신 의존성 주입 패턴 사용
    """
    
    def __init__(self):
        self._chat_service = None
        self._history_manager = None
        self._chroma_service = None
        self._career_vectordb_service = None
        print("ServiceContainer 초기화")
    
    @property
    def history_manager(self) -> ConversationHistoryManager:
        """ConversationHistoryManager 싱글톤"""
        if self._history_manager is None:
            print("ConversationHistoryManager 싱글톤 생성")
            self._history_manager = ConversationHistoryManager(max_messages=20)
        return self._history_manager
    
    @property  
    def chat_service(self) -> ChatService:
        """ChatService 싱글톤"""
        if self._chat_service is None:
            print("ChatService 싱글톤 생성")
            self._chat_service = ChatService(session_timeout_hours=1)
        return self._chat_service

    @property
    def chroma_service(self) -> ChromaService:
        """ChromaService 싱글톤"""
        if self._chroma_service is None:
            print("ChromaService 싱글톤 생성")
            self._chroma_service = ChromaService()
        return self._chroma_service

    
@lru_cache()
def get_service_container() -> ServiceContainer:
    """서비스 컨테이너 싱글톤 - 앱 전체에서 하나만 생성"""
    print("ServiceContainer 싱글톤 생성")
    return ServiceContainer()


def get_chat_service(
    container: Annotated[ServiceContainer, Depends(get_service_container)]
) -> ChatService:
    """ChatService 의존성 주입"""
    return container.chat_service


def get_history_manager(
    container: Annotated[ServiceContainer, Depends(get_service_container)]
) -> ConversationHistoryManager:
    """ConversationHistoryManager 의존성 주입"""
    return container.history_manager


def get_chroma_service(
    container: Annotated[ServiceContainer, Depends(get_service_container)]
) -> ChromaService:
    """ChromaService 의존성 주입"""
    return container.chroma_service