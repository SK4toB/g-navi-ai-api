# app/services/chat_session_service.py

from typing import Dict, Any, List
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
        
        # 1. 대화 히스토리 복원 (LangGraph 빌드 전에 먼저 수행)
        if previous_messages and len(previous_messages) > 0:
            print(f"ChatSessionService 대화 히스토리 복원: {len(previous_messages)}개 메시지")
            await self._restore_conversation_history(conversation_id, previous_messages, user_info)

        # 2. LangGraph 빌드 (새 세션과 동일)
        compiled_graph = await self.graph_builder.build_persistent_chat_graph(conversation_id, user_info)
        
        # 3. 세션 설정 구성
        thread_id = f"thread_{conversation_id}"
        config = {"configurable": {"thread_id": thread_id}}
        
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
    
    async def _restore_conversation_history(self, conversation_id: str, previous_messages: List, user_info: Dict[str, Any]):
        """
        SpringBoot에서 받은 메시지들을 대화 히스토리에 복원 (방법 2)
        """
        if not previous_messages:
            print("복원할 메시지가 없습니다.")
            return
        
        try:
            from app.graphs.nodes.openai_response_node import get_history_manager
            
            history_manager = get_history_manager()
            user_name = user_info.get("name", "사용자")
            
            print(f"대화 히스토리 복원 시작: {conversation_id}, {len(previous_messages)}개 메시지")
            
            restored_count = 0
            for message in previous_messages:
                try:
                    sender_type = message.sender_type  # "USER" 또는 "BOT"
                    message_text = message.message_text
                    timestamp = getattr(message, 'timestamp', None)
                    
                    # MongoDB 형식을 OpenAI 형식으로 변환
                    if sender_type == "USER":
                        role = "user"
                        metadata = {
                            "user_name": user_name,
                            "restored": True,
                            "original_timestamp": str(timestamp) if timestamp else None,
                            "source": "mongodb"
                        }
                    elif sender_type == "BOT":
                        role = "assistant"
                        metadata = {
                            "restored": True,
                            "original_timestamp": str(timestamp) if timestamp else None,
                            "source": "mongodb"
                        }
                    else:
                        print(f"알 수 없는 sender_type: {sender_type}, 건너뜀")
                        continue
                    
                    # 대화 히스토리에 추가 (타임스탬프는 metadata에만 저장)
                    history_manager.add_message(
                        conversation_id=conversation_id,
                        role=role,
                        content=message_text,
                        metadata=metadata
                    )
                    
                    restored_count += 1
                    print(f"복원됨 ({restored_count}): {role} - {message_text[:50]}...")
                    
                except Exception as msg_error:
                    print(f"개별 메시지 복원 실패: {str(msg_error)}")
                    continue
            
            # 복원 완료 후 요약 정보 출력
            summary = history_manager.get_history_summary(conversation_id)
            print(f"대화 히스토리 복원 완료: {restored_count}개 복원됨")
            print(f"   - 총 메시지: {summary['message_count']}개")
            print(f"   - 사용자 메시지: {summary['user_messages']}개")
            print(f"   - 봇 메시지: {summary['assistant_messages']}개")
            
        except Exception as e:
            print(f"대화 히스토리 복원 실패: {str(e)}")
            import traceback
            print(f"상세 에러: {traceback.format_exc()}")
            # 복원 실패해도 세션 생성은 계속 진행