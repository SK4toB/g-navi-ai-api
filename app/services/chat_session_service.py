# app/services/chat_session_service.py

from typing import Dict, Any
from datetime import datetime
from app.graphs.graph_builder import ChatGraphBuilder
from app.services.bot_message import BotMessageService


class ChatSessionService:
    """
    채팅 세션 생성/로드 전담 클래스
    - 새 세션 생성
    - 기존 세션 로드
    - 대화 히스토리 복원
    """
    
    def __init__(self):
        self.graph_builder = ChatGraphBuilder()
        self.bot_message_service = BotMessageService()
        print("ChatSessionService 초기화")
    
    async def create_new_session(self, conversation_id: str, user_info: Dict[str, Any]) -> tuple[Any, str, Dict, str]:
        """
        새 채팅 세션 생성
        Returns: (compiled_graph, thread_id, config, initial_message)
        """
        print(f"ChatSessionService 새 세션 생성 시작: {conversation_id}")
        
        # 1. LangGraph 빌드
        compiled_graph = await self.graph_builder.build_persistent_chat_graph(conversation_id, user_info)
        
        # 2. 세션 설정 구성
        thread_id = f"thread_{conversation_id}"
        config = {"configurable": {"thread_id": thread_id}}
        
        # 3. 환영 메시지 생성
        initial_message = await self.bot_message_service._generate_welcome_message(user_info)
        
        print(f"ChatSessionService 새 세션 생성 완료: {conversation_id}")
        
        return compiled_graph, thread_id, config, initial_message
    
    async def load_existing_session(
        self, 
        conversation_id: str, 
        user_info: Dict[str, Any], 
        previous_messages: list = None
    ) -> tuple[Any, str, Dict, Dict[str, Any]]:
        """
        기존 세션 복원 (세션이 만료된 경우)
        Returns: (compiled_graph, thread_id, config, load_result)
        """
        print(f"ChatSessionService 세션 복원 시작: {conversation_id}")
        
        # 1. LangGraph 빌드 (새 세션과 동일)
        compiled_graph = await self.graph_builder.build_persistent_chat_graph(conversation_id, user_info)
        
        # 2. 세션 설정 구성
        thread_id = f"thread_{conversation_id}"
        config = {"configurable": {"thread_id": thread_id}}
        
        # 3. 대화 히스토리 복원 (TODO: 향후 구현)
        if previous_messages and len(previous_messages) > 0:
            print(f"ChatSessionService 대화 히스토리 복원 예정: {len(previous_messages)}개 메시지")
            await self._restore_conversation_history(conversation_id, previous_messages)
        
        # 4. 로드 결과 구성
        load_result = {
            "status": "session_created",
            "message": f"새 세션을 생성했습니다 ({len(previous_messages) if previous_messages else 0}개 이전 메시지)",
            "conversation_id": conversation_id,
            "previous_messages_count": len(previous_messages) if previous_messages else 0,
            "requires_initial_message": False  # 로드 시에는 초기 메시지 불필요
        }
        
        print(f"ChatSessionService 세션 복원 완료: {conversation_id}")
        
        return compiled_graph, thread_id, config, load_result
    
    async def _restore_conversation_history(self, conversation_id: str, previous_messages: list):
        """
        대화 히스토리 복원 (향후 구현)
        Vector DB나 LangGraph 메모리에 이전 대화 저장
        """
        print(f"ChatSessionService 대화 히스토리 복원 시작: {conversation_id}")
        
        # TODO: 구현 예정
        # 1. previous_messages를 파싱
        # 2. Vector DB에 임베딩 저장
        # 3. LangGraph 메모리에 대화 컨텍스트 저장
        
        pass