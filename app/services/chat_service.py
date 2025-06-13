# app/services/chat_service.py (조건부 분기 방식)

from typing import Dict, Any
from app.graphs.graph_builder import ChatGraphBuilder
from app.services.bot_message import BotMessageService
from datetime import datetime, timedelta

class ChatService:
    """
    조건부 분기 방식 채팅 서비스
    interrupt 없이 메시지별로 그래프 실행
    """
    
    def __init__(self):
        self.graph_builder = ChatGraphBuilder()
        self.active_sessions = {}  # conversation_id -> {graph, thread_id, config}
        self.bot_message_service = BotMessageService()
        self.session_timeout = timedelta(hours=1)
        print("chat_service __init__")
    
    
    async def create_chat_session(self, conversation_id: str, user_info: Dict[str, Any]) -> str:
        """
        채팅 세션 생성
        """
        print(f"conversation_id: {conversation_id} 시작")
        
        # 1. LangGraph 빌드
        compiled_graph = await self.graph_builder.build_persistent_chat_graph(conversation_id, user_info)
        
        # 2. 세션 정보 저장 (실행하지 않음)
        thread_id = f"thread_{conversation_id}"
        config = {"configurable": {"thread_id": thread_id}}
        
        self.active_sessions[conversation_id] = {
            "graph": compiled_graph,
            "thread_id": thread_id,
            "config": config,
            "user_info": user_info,
            "created_at": datetime.utcnow(),      # 생성 시간
            "last_active": datetime.utcnow(),     # 마지막 활동 시간
            "status": "active"                    # 세션 상태 
        }
        
        print(f"conversation_id: {conversation_id} 세션 생성 완료")
        
        # 3. BotMessageService를 사용한 환영 메시지 생성
        initial_message = await self.bot_message_service._generate_welcome_message(user_info)
        
        return initial_message
    
    async def load_chat_session(self, conversation_id: str, user_info: Dict[str, Any]) -> str:
        """
        채팅 세션 생성
        """
        print(f"conversation_id: {conversation_id} 시작")
        
        # 1. LangGraph 빌드
        compiled_graph = await self.graph_builder.build_persistent_chat_graph(conversation_id, user_info)
        
        # 2. 세션 정보 저장 (실행하지 않음)
        thread_id = f"thread_{conversation_id}"
        config = {"configurable": {"thread_id": thread_id}}
        
        self.active_sessions[conversation_id] = {
            "graph": compiled_graph,
            "thread_id": thread_id,
            "config": config,
            "user_info": user_info
        }
        
        print(f"conversation_id: {conversation_id} 세션 생성 완료")
        
        # 3. BotMessageService를 사용한 환영 메시지 생성
        initial_message = await self.bot_message_service._generate_welcome_message(user_info)
        
        return initial_message
    

    async def send_message(self, conversation_id: str, member_id: str, message_text: str) -> str:
        """
        조건부 분기 방식 메시지 처리
        """
        print(f"chat_service 조건부 분기 메시지 처리: {conversation_id}")
        
        if conversation_id not in self.active_sessions:
            raise ValueError(f"chat_service 활성화된 세션이 없습니다: {conversation_id}")
        
        # 마지막 활동 시간 업데이트 (메시지 처리 전에)
        self.active_sessions[conversation_id]["last_active"] = datetime.utcnow()

        session = self.active_sessions[conversation_id]
        graph = session["graph"]
        config = session["config"]
        user_info = session.get("user_info", {})
        
        try:
            print(f"chat_service 입력 메시지: {message_text}")
            
            # 전체 상태 구성 (메시지 포함)
            input_state = {
                "message_text": message_text,  # 실제 메시지
                "member_id": member_id,
                "conversation_id": conversation_id,
                "user_info": user_info,
                # 나머지 필드들 초기화
                "intent": None,
                "embedding_vector": None,
                "memory_results": None,
                "similarity_score": None,
                "profiling_data": None,
                "connection_suggestions": None,
                "bot_message": None
            }
            
            print(f"chat_service langgraph 실행합니다")
            
            # 전체 그래프 실행 (조건부 분기로 메시지 처리)
            result = await graph.ainvoke(input_state, config)
            
            print(f"chat_service langgraph 실행했습니다")
            
            # 최종 응답 추출
            bot_message = result.get("bot_message")
            
            if bot_message is None:
                print("bot_message is None")
                print(f"result 전체 내용: {result}")
                bot_message  = "Langgraph 응답을 생성할 수 없습니다."
            
            print(f"최종 응답: {str(bot_message )[:100]}...")
            return bot_message 
            
        except Exception as e:
            print(f"조건부 분기 처리 실패: {e}")
            import traceback
            print(f"상세 에러: {traceback.format_exc()}")
            return f"죄송합니다. 메시지 처리 중 오류가 발생했습니다: {str(e)}"
    
    async def close_chat_session(self, conversation_id: str):
        """채팅 세션 종료"""
        if conversation_id in self.active_sessions:
            del self.active_sessions[conversation_id]
            print(f"조건부 분기 채팅 세션 종료: {conversation_id}")
    
    def get_session_status(self, conversation_id: str) -> Dict[str, Any]:
        """세션 상태 조회"""
        if conversation_id in self.active_sessions:
            return {
                "conversation_id": conversation_id,
                "status": "active",
                "thread_id": self.active_sessions[conversation_id]["thread_id"]
            }
        return {"conversation_id": conversation_id, "status": "inactive"}


    def get_session_health(self, conversation_id: str) -> Dict[str, Any]:
        """특정 conversation_id의 세션 헬스체크"""
        now = datetime.utcnow()
        
        if conversation_id not in self.active_sessions:
            return {
                "conversation_id": conversation_id,
                "status": "not_found",
                "message": "세션이 존재하지 않습니다",
                "timestamp": now.isoformat()
            }
        
        session = self.active_sessions[conversation_id]
        created_at = session.get("created_at")
        last_active = session.get("last_active")
        
        # 시간 계산
        alive_duration = now - created_at
        inactive_duration = now - last_active
        
        # 만료 여부 체크
        is_expired = inactive_duration > self.session_timeout
        
        return {
            "conversation_id": conversation_id,
            "status": "expired" if is_expired else "active",
            "created_at": created_at.isoformat(),
            "last_active": last_active.isoformat(),
            "alive_minutes": int(alive_duration.total_seconds() / 60),
            "inactive_minutes": int(inactive_duration.total_seconds() / 60),
            "timeout_minutes": int(self.session_timeout.total_seconds() / 60),
            "expires_in_minutes": max(0, int((self.session_timeout - inactive_duration).total_seconds() / 60)),
            "thread_id": session.get("thread_id"),
            "message": "정상 활성화된 세션입니다" if not is_expired else f"{int(inactive_duration.total_seconds() / 60)}분 비활성으로 만료되었습니다",
            "timestamp": now.isoformat()
        }