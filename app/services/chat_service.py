# app/services/chat_service.py (조건부 분기 방식)

from typing import Dict, Any
from app.graphs.graph_builder import ChatGraphBuilder
from app.services.bot_message import BotMessageService
from datetime import datetime, timedelta
import asyncio


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
    

    async def load_chat_session(self, conversation_id: str, user_info: Dict[str, Any], previous_messages: list = None) -> Dict[str, Any]:
        """
        기존 채팅방 로드
        세션이 살아있으면 재사용, 없으면 새로 생성
        """
        print(f"채팅방 로드 요청: {conversation_id}")
        
        # 1. 기존 세션 확인
        if conversation_id in self.active_sessions:
            session = self.active_sessions[conversation_id]
            last_active = session.get("last_active", session.get("created_at"))
            now = datetime.utcnow()
            inactive_duration = now - last_active
            
            # 세션이 아직 유효한 경우
            if inactive_duration <= self.session_timeout:
                # 활동 시간 업데이트
                self.active_sessions[conversation_id]["last_active"] = now
                
                print(f"✅ 기존 세션 재사용: {conversation_id}")
                print(f"   - 비활성 시간: {int(inactive_duration.total_seconds() / 60)}분")
                
                return {
                    "status": "session_reused",
                    "message": "기존 세션을 재사용합니다",
                    "conversation_id": conversation_id,
                    "session_age_minutes": int((now - session.get("created_at")).total_seconds() / 60),
                    "inactive_minutes": int(inactive_duration.total_seconds() / 60),
                    "requires_initial_message": False  # 초기 메시지 불필요
                }
            else:
                # 세션이 만료된 경우 - 제거 후 새로 생성
                print(f"⚠️ 만료된 세션 발견, 새 세션으로 교체: {conversation_id}")
                await self._close_session_internal(conversation_id)
        
        # 2. 새 세션 생성 (기존 create_chat_session과 동일한 로직)
        print(f"🔄 새 세션 생성: {conversation_id}")
        
        # LangGraph 빌드
        compiled_graph = await self.graph_builder.build_persistent_chat_graph(conversation_id, user_info)
        
        # 세션 정보 저장
        thread_id = f"thread_{conversation_id}"
        config = {"configurable": {"thread_id": thread_id}}
        
        self.active_sessions[conversation_id] = {
            "graph": compiled_graph,
            "thread_id": thread_id,
            "config": config,
            "user_info": user_info,
            "created_at": datetime.utcnow(),
            "last_active": datetime.utcnow(),
            "status": "active",
            "load_type": "restored"  # 복원된 세션임을 표시
        }
        
        # 3. TODO: 향후 대화 히스토리 복원 로직 추가 위치
        if previous_messages and len(previous_messages) > 0:
            print(f"📝 대화 히스토리 복원 예정: {len(previous_messages)}개 메시지")
            # TODO: Vector DB나 LangGraph 메모리에 이전 대화 저장
            # await self._restore_conversation_history(conversation_id, previous_messages)
        
        print(f"✅ 채팅방 로드 완료: {conversation_id}")
        
        return {
            "status": "session_created",
            "message": f"새 세션을 생성했습니다 ({len(previous_messages) if previous_messages else 0}개 이전 메시지)",
            "conversation_id": conversation_id,
            "previous_messages_count": len(previous_messages) if previous_messages else 0,
            "requires_initial_message": False  # 로드 시에는 초기 메시지 불필요
        }

    async def _close_session_internal(self, conversation_id: str):
        """내부 세션 종료 (정리 작업용)"""
        if conversation_id in self.active_sessions:
            del self.active_sessions[conversation_id]
            print(f"세션 메모리에서 제거: {conversation_id}")

    # 향후 구현 예정 메서드
    async def _restore_conversation_history(self, conversation_id: str, previous_messages: list = None):
        """
        대화 히스토리 복원 (향후 구현)
        Vector DB나 LangGraph 메모리에 이전 대화 저장
        """
        print(f"대화 히스토리 복원 시작: {conversation_id}")
        
        # TODO: 구현 예정
        # 1. previous_messages를 파싱
        # 2. Vector DB에 임베딩 저장
        # 3. LangGraph 메모리에 대화 컨텍스트 저장
        
        pass

    async def send_message(self, conversation_id: str, member_id: str, message_text: str) -> str:
        """
        조건부 분기 방식 메시지 처리
        """
        print(f"chat_service 메시지 처리: {conversation_id}")
        
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
    
    async def close_chat_session(self, conversation_id: str) -> Dict[str, Any]:
        """채팅 세션 수동 종료"""
        if conversation_id not in self.active_sessions:
            return {
                "status": "not_found",
                "message": f"세션 {conversation_id}을 찾을 수 없습니다",
                "conversation_id": conversation_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        session = self.active_sessions[conversation_id]
        user_name = session.get("user_info", {}).get("name", "Unknown")
        created_at = session.get("created_at")
        now = datetime.utcnow()
        session_age_minutes = int((now - created_at).total_seconds() / 60)
        
        # 세션 제거
        del self.active_sessions[conversation_id]
        
        print(f"🚪 수동 세션 종료: {conversation_id} (사용자: {user_name}, 지속시간: {session_age_minutes}분)")
        
        return {
            "status": "closed",
            "message": f"세션 {conversation_id}이 성공적으로 종료되었습니다",
            "conversation_id": conversation_id,
            "user_name": user_name,
            "session_age_minutes": session_age_minutes,
            "closed_at": now.isoformat()
        }

    def close_all_sessions(self) -> Dict[str, Any]:
        """모든 활성 세션 수동 종료"""
        if not self.active_sessions:
            return {
                "status": "no_sessions",
                "message": "종료할 활성 세션이 없습니다",
                "closed_sessions": [],
                "timestamp": datetime.utcnow().isoformat()
            }
        
        closed_sessions = []
        now = datetime.utcnow()
        
        for conv_id, session in list(self.active_sessions.items()):
            user_name = session.get("user_info", {}).get("name", "Unknown")
            created_at = session.get("created_at")
            session_age_minutes = int((now - created_at).total_seconds() / 60)
            
            closed_sessions.append({
                "conversation_id": conv_id,
                "user_name": user_name,
                "session_age_minutes": session_age_minutes
            })
            
            print(f"🚪 전체 종료: {conv_id} (사용자: {user_name})")
        
        # 모든 세션 제거
        total_closed = len(self.active_sessions)
        self.active_sessions.clear()
        
        print(f"✅ 전체 {total_closed}개 세션 종료 완료")
        
        return {
            "status": "all_closed",
            "message": f"총 {total_closed}개의 세션이 종료되었습니다",
            "closed_sessions": closed_sessions,
            "total_closed": total_closed,
            "timestamp": now.isoformat()
        }

    def close_sessions_by_user(self, user_name: str) -> Dict[str, Any]:
        """특정 사용자의 모든 세션 종료"""
        if not self.active_sessions:
            return {
                "status": "no_sessions",
                "message": "활성 세션이 없습니다",
                "user_name": user_name,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        user_sessions = []
        now = datetime.utcnow()
        
        # 해당 사용자의 세션 찾기
        for conv_id, session in list(self.active_sessions.items()):
            session_user_name = session.get("user_info", {}).get("name", "")
            
            if session_user_name == user_name:
                created_at = session.get("created_at")
                session_age_minutes = int((now - created_at).total_seconds() / 60)
                
                user_sessions.append({
                    "conversation_id": conv_id,
                    "session_age_minutes": session_age_minutes
                })
                
                # 세션 제거
                del self.active_sessions[conv_id]
                print(f"🚪 사용자별 종료: {conv_id} (사용자: {user_name})")
        
        if not user_sessions:
            return {
                "status": "user_not_found",
                "message": f"사용자 '{user_name}'의 활성 세션을 찾을 수 없습니다",
                "user_name": user_name,
                "timestamp": now.isoformat()
            }
        
        print(f"✅ 사용자 {user_name}의 {len(user_sessions)}개 세션 종료 완료")
        
        return {
            "status": "user_sessions_closed",
            "message": f"사용자 '{user_name}'의 {len(user_sessions)}개 세션이 종료되었습니다",
            "user_name": user_name,
            "closed_sessions": user_sessions,
            "total_closed": len(user_sessions),
            "timestamp": now.isoformat()
        }
    
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

    def get_all_active_sessions(self) -> Dict[str, Any]:
        """현재 열려있는 전체 세션 간단 조회"""
        now = datetime.utcnow()
        
        if not self.active_sessions:
            return {
                "total_sessions": 0,
                "sessions": [],
                "message": "현재 활성화된 세션이 없습니다",
                "timestamp": now.isoformat()
            }
        
        sessions_list = []
        
        for conv_id, session in self.active_sessions.items():
            created_at = session.get("created_at")
            last_active = session.get("last_active", created_at)
            
            # 시간 계산
            alive_minutes = int((now - created_at).total_seconds() / 60)
            inactive_minutes = int((now - last_active).total_seconds() / 60)
            
            sessions_list.append({
                "conversation_id": conv_id,
                "user_name": session.get("user_info", {}).get("name", "Unknown"),
                "alive_minutes": alive_minutes,
                "inactive_minutes": inactive_minutes,
                "last_active": last_active.isoformat(),
                "thread_id": session.get("thread_id")
            })
        
        # inactive_minutes 기준으로 정렬 (오래 비활성인 것부터)
        sessions_list.sort(key=lambda x: x["inactive_minutes"], reverse=True)
        
        return {
            "total_sessions": len(self.active_sessions),
            "sessions": sessions_list,
            "session_timeout_minutes": int(self.session_timeout.total_seconds() / 60),
            "message": f"현재 {len(self.active_sessions)}개의 세션이 활성화되어 있습니다",
            "timestamp": now.isoformat()
        }