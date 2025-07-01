# app/services/chat_session_service.py
"""
* @className : ChatSessionService
* @description : 채팅 세션 서비스 모듈
*                채팅 세션의 생성과 관리를 담당하는 서비스입니다.
*                LangGraph 빌드, 세션 초기화, 메시지 관리를 처리합니다.
*
* @modification : 2025.07.01(이재원) 최초생성
*
* @author 이재원
* @Date 2025.07.01
* @version 1.0
* @see ChatGraphBuilder, SessionManager
*  == 개정이력(Modification Information) ==
*  
*   수정일        수정자        수정내용
*   ----------   --------     ---------------------------
*   2025.07.01   이재원       최초 생성
*  
* Copyright (C) by G-Navi AI System All right reserved.
"""

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
        initial_message = await self.bot_message_service.generate_welcome_message(user_info)
        
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

        # 2. LangGraph 빌드 (previous_messages도 전달)
        compiled_graph = await self.graph_builder.build_persistent_chat_graph(conversation_id, user_info, previous_messages)
        
        # 3. 세션 설정 구성
        thread_id = f"thread_{conversation_id}"
        config = {"configurable": {"thread_id": thread_id}}
        
        # 4. 환영 메시지 생성 (세션 로드 시에도)
        welcome_message = await self.bot_message_service.generate_welcome_message(user_info)
        
        # 5. 로드 결과 구성
        load_result = {
            "status": "session_loaded",
            "message": welcome_message,
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
            from app.core.dependencies import get_service_container
            
            container = get_service_container()
            history_manager = container.history_manager
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
    
    def get_current_session_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """
        현재 세션의 메시지 목록 반환 (VectorDB 구축용)
        
        Args:
            conversation_id: 대화 ID
            
        Returns:
            List[Dict[str, Any]]: 현재 세션의 메시지 목록
        """
        try:
            print(f"🔍 세션 메시지 조회 시작: {conversation_id}")
            
            # ConversationHistoryManager에서 현재 세션의 메시지 히스토리 가져오기
            from app.core.dependencies import get_service_container
            
            container = get_service_container()
            history_manager = container.history_manager
            
            # 전체 히스토리 정보 조회 (디버깅용)
            all_sessions = history_manager.session_histories
            print(f"📊 전체 활성 세션 수: {len(all_sessions)}")
            print(f"📋 활성 세션 목록: {list(all_sessions.keys())}")
            
            # 현재 세션의 히스토리 조회
            history = history_manager.get_history(conversation_id)
            full_history = history_manager.get_history_with_metadata(conversation_id)
            
            print(f"📝 세션 {conversation_id} 상세 정보:")
            print(f"   OpenAI 형식 메시지: {len(history)}개")
            print(f"   메타데이터 포함: {len(full_history)}개")
            
            if full_history:
                print(f"   📋 메시지 상세 (ConversationHistoryManager):")
                for i, msg in enumerate(full_history):
                    role = msg.get('role', 'unknown')
                    content = msg.get('content', '')[:50]
                    timestamp = msg.get('timestamp', 'no-time')
                    source = msg.get('metadata', {}).get('source', 'unknown')
                    print(f"     #{i+1} [{timestamp}] {role}: {content}{'...' if len(msg.get('content', '')) > 50 else ''} (출처: {source})")
            
            # 🔍 추가: 최근 추가된 메시지가 있는지 확인
            recent_count = len([msg for msg in full_history if msg.get('metadata', {}).get('source') in ['chat_history_node', 'response_formatting_node']]) if full_history else 0
            print(f"   🆕 워크플로우에서 추가된 메시지: {recent_count}개")
            
            if history and len(history) > 0:
                print(f"✅ 현재 세션 메시지 조회 성공: {conversation_id} - {len(history)}개 메시지")
                print(f"   - 마지막 메시지: {history[-1].get('role', 'unknown')} - {history[-1].get('content', '')[:50]}...")
                return history
            else:
                print(f"⚠️ 현재 세션 메시지 없음: {conversation_id} - 히스토리 없음")
                return []
            
        except Exception as e:
            print(f"❌ 세션 메시지 조회 실패: {conversation_id} - {e}")
            import traceback
            traceback.print_exc()
            # 실패 시 빈 리스트 반환 (VectorDB 구축 건너뛰기)
            return []