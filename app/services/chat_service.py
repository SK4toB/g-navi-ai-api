# app/services/chat_service.py (리팩토링된 버전)

from typing import Dict, Any
from datetime import datetime
from app.services.session_manager import SessionManager
from app.services.message_processor import MessageProcessor
from app.services.chat_session_service import ChatSessionService


class ChatService:
    """
    채팅 서비스 클래스
    - 채팅 세션 생성/로드
    - 메시지 처리
    - 세션 관리 위임
    - 각 책임별 서비스 분리
    """
    
    def __init__(self, session_timeout_hours: int = 1):
        # 각 책임별 서비스 초기화
        # SessionManager에서 이미 테스트용 1분 타임아웃으로 설정됨
        self.session_manager = SessionManager(session_timeout_hours)
        self.message_processor = MessageProcessor()
        self.chat_session_service = ChatSessionService()
        
        print("ChatService 초기화 완료 (서비스모드: 세션 타임아웃 30분, 자동정리 5분)")
    
    async def start_auto_cleanup(self):
        """자동 세션 정리 시작 (VectorDB 구축 포함)"""
        await self.session_manager.start_auto_cleanup(self.get_session_messages)
    
    async def stop_auto_cleanup(self):
        """자동 세션 정리 중지"""
        await self.session_manager.stop_auto_cleanup()
    
    # ============================================================================
    # 메인 채팅 기능
    # ============================================================================
    
    async def create_chat_session(self, conversation_id: str, user_info: Dict[str, Any]) -> str:
        """새 채팅 세션 생성"""
        print(f"ChatService 새 채팅 세션 생성: {conversation_id}")
        
        # 1. 새 세션 생성 (그래프 빌드 + 초기 메시지)
        compiled_graph, thread_id, config, initial_message = await self.chat_session_service.create_new_session(
            conversation_id, user_info
        )
        
        # 2. 세션 매니저에 등록
        self.session_manager.create_session(
            conversation_id=conversation_id,
            graph=compiled_graph,
            thread_id=thread_id,
            config=config,
            user_info=user_info
        )
        
        print(f"ChatService 새 채팅 세션 생성 완료: {conversation_id}")
        return initial_message
    
    async def load_chat_session(
        self, 
        conversation_id: str, 
        user_info: Dict[str, Any], 
        previous_messages: list = None
    ) -> Dict[str, Any]:
        """기존 채팅방 로드"""
        print(f"ChatService 채팅방 로드 요청: {conversation_id}")
        
        # 1. 기존 세션 확인
        existing_session = self.session_manager.get_session(conversation_id)
        
        if existing_session and not self.session_manager.is_session_expired(conversation_id):
            # 기존 세션 재사용
            self.session_manager.update_last_active(conversation_id)
            
            session_age = datetime.utcnow() - existing_session.get("created_at")
            last_active = existing_session.get("last_active")
            inactive_duration = datetime.utcnow() - last_active
            
            print(f"ChatService 기존 세션 재사용: {conversation_id}")
            
            return {
                "status": "session_reused",
                "message": "기존 세션을 재사용합니다",
                "conversation_id": conversation_id,
                "session_age_minutes": int(session_age.total_seconds() / 60),
                "inactive_minutes": int(inactive_duration.total_seconds() / 60),
                "requires_initial_message": False
            }
        
        # 2. 만료되었거나 없는 세션 - 새로 생성
        if existing_session:
            print(f"ChatService 만료된 세션 발견, 새 세션으로 교체: {conversation_id}")
            self.session_manager.close_session(conversation_id)
        
        print(f"ChatService 새 세션 생성: {conversation_id}")
        
        # 3. 새 세션 생성 및 히스토리 복원
        compiled_graph, thread_id, config, load_result = await self.chat_session_service.load_existing_session(
            conversation_id, user_info, previous_messages
        )
        
        # 4. 세션 매니저에 등록
        self.session_manager.create_session(
            conversation_id=conversation_id,
            graph=compiled_graph,
            thread_id=thread_id,
            config=config,
            user_info=user_info
        )
        
        # load_type 표시
        session = self.session_manager.get_session(conversation_id)
        session["load_type"] = "restored"
        
        print(f"ChatService 채팅방 로드 완료: {conversation_id}")
        return load_result
    
    async def send_message(self, conversation_id: str, member_id: str, message_text: str) -> str:
        """메시지 전송 및 처리"""
        print(f"ChatService 메시지 처리 요청: {conversation_id}")
        
        # 1. 세션 존재 여부 확인
        session = self.session_manager.get_session(conversation_id)
        if not session:
            raise ValueError(f"ChatService 활성화된 세션이 없습니다: {conversation_id}")
        
        # 2. 마지막 활동 시간 업데이트
        self.session_manager.update_last_active(conversation_id)
        
        # 3. 메시지 처리
        bot_message = await self.message_processor.process_message(
            graph=session["graph"],
            config=session["config"],
            conversation_id=conversation_id,
            member_id=member_id,
            user_question=message_text,  # user_question으로 수정
            user_info=session.get("user_info", {})
        )
        
        print(f"ChatService 메시지 처리 완료: {conversation_id}")
        return bot_message
    
    # ============================================================================
    # 세션 관리 위임 메서드들
    # ============================================================================
    
    async def close_chat_session(self, conversation_id: str) -> Dict[str, Any]:
        """채팅 세션 종료 (VectorDB 구축 포함)"""
        print(f"🔚 세션 종료 시작: {conversation_id}")
        
        # 세션 종료 전에 current_session_messages 가져오기
        current_messages = self.get_session_messages(conversation_id)
        
        print(f"📊 세션 종료 시 current_session_messages 개수: {len(current_messages) if current_messages else 0}개")
        if current_messages:
            print(f"📋 current_session_messages 상세:")
            for i, msg in enumerate(current_messages):
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')[:50]
                print(f"     #{i+1} {role}: {content}{'...' if len(msg.get('content', '')) > 50 else ''}")
        
        # 세션 종료 (VectorDB 구축 포함)
        return await self.session_manager.close_session(conversation_id, current_messages)
    
    def close_all_sessions(self) -> Dict[str, Any]:
        """모든 세션 종료"""
        return self.session_manager.close_all_sessions()
    
    def close_sessions_by_user(self, user_name: str) -> Dict[str, Any]:
        """특정 사용자의 모든 세션 종료"""
        return self.session_manager.close_sessions_by_user(user_name)
    
    def get_session_status(self, conversation_id: str) -> Dict[str, Any]:
        """세션 상태 조회"""
        return self.session_manager.get_session_status(conversation_id)
    
    def get_session_health(self, conversation_id: str) -> Dict[str, Any]:
        """세션 헬스체크"""
        return self.session_manager.get_session_health(conversation_id)
    
    def get_all_active_sessions(self) -> Dict[str, Any]:
        """전체 활성 세션 조회"""
        return self.session_manager.get_all_active_sessions()
    
    async def cleanup_expired_sessions(self) -> Dict[str, Any]:
        """만료된 세션 정리 (VectorDB 구축 포함)"""
        return await self.session_manager.cleanup_expired_sessions(self.get_session_messages)
    
    # ============================================================================
    # 호환성을 위한 속성 접근자들 (기존 코드와의 호환성 유지)
    # ============================================================================
    
    @property
    def active_sessions(self) -> Dict[str, Dict[str, Any]]:
        """기존 코드 호환성을 위한 active_sessions 접근자"""
        return self.session_manager.active_sessions
    
    @property
    def session_timeout(self):
        """기존 코드 호환성을 위한 session_timeout 접근자"""
        return self.session_manager.session_timeout

    async def process_message(self, conversation_id: str, member_id: str, user_question: str) -> str:
        """메시지 처리 (호환성 있는 시그니처)"""
        return await self.send_message(conversation_id, member_id, user_question)
    
    def get_session_messages(self, conversation_id: str):
        """세션의 current_session_messages 반환 (VectorDB 구축용)"""
        try:
            print(f"📥 get_session_messages 시작: {conversation_id}")
            
            session = self.session_manager.get_session(conversation_id)
            if not session:
                print(f"❌ 세션이 존재하지 않음: {conversation_id}")
                return []
            
            print(f"✅ 세션 정보 확인됨: {conversation_id}")
            
            # ChatSessionService에서 현재 메시지 가져오기
            messages = self.chat_session_service.get_current_session_messages(conversation_id)
            
            print(f"📊 get_session_messages 결과: {len(messages) if messages else 0}개 메시지")
            
            return messages
            
        except Exception as e:
            print(f"❌ 세션 메시지 조회 실패: {conversation_id} - {e}")
            import traceback
            traceback.print_exc()
            return []