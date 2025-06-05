# app/services/chat_service.py (조건부 분기 방식)

from typing import Dict, Any
import os
from app.graphs.graph_builder import ChatGraphBuilder

class ChatService:
    """
    조건부 분기 방식 채팅 서비스
    interrupt 없이 메시지별로 그래프 실행
    """
    
    def __init__(self):
        self.graph_builder = ChatGraphBuilder()
        self.active_sessions = {}  # room_id -> {graph, thread_id, config}
        self.openai_client = None
        self._init_openai()
        print("ChatService 초기화 (조건부 분기 방식)")
    
    def _init_openai(self):
        """OpenAI 클라이언트 초기화 (초기 메시지용)"""
        try:
            from openai import AsyncOpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.openai_client = AsyncOpenAI(api_key=api_key)
                self.model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
                self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "1000"))
                self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
                print("ChatService OpenAI 연결")
        except Exception as e:
            print(f"OpenAI 초기화 실패: {e}")
    
    async def create_chat_session(self, room_id: str, user_info: Dict[str, Any]) -> str:
        """
        조건부 분기 방식 채팅 세션 생성
        """
        print(f"🚀 조건부 분기 채팅 세션 생성: {room_id}")
        
        # 1. LangGraph 빌드
        compiled_graph = await self.graph_builder.build_persistent_chat_graph(room_id, user_info)
        
        # 2. 세션 정보 저장 (실행하지 않음)
        thread_id = f"thread_{room_id}"
        config = {"configurable": {"thread_id": thread_id}}
        
        self.active_sessions[room_id] = {
            "graph": compiled_graph,
            "thread_id": thread_id,
            "config": config,
            "user_info": user_info
        }
        
        print(f"✅ 조건부 분기 세션 생성 완료: {room_id}")
        
        # 3. 환영 메시지 생성
        initial_message = await self._generate_welcome_message(user_info)
        
        return initial_message
    
    async def send_message(self, room_id: str, user_id: str, message: str) -> str:
        """
        조건부 분기 방식 메시지 처리
        """
        print(f"🔄 조건부 분기 메시지 처리: {room_id}")
        
        if room_id not in self.active_sessions:
            raise ValueError(f"활성화된 세션이 없습니다: {room_id}")
        
        session = self.active_sessions[room_id]
        graph = session["graph"]
        config = session["config"]
        user_info = session.get("user_info", {})
        
        try:
            print(f"📨 입력 메시지: {message}")
            
            # 전체 상태 구성 (메시지 포함)
            input_state = {
                "user_message": message,  # 실제 메시지
                "user_id": user_id,
                "room_id": room_id,
                "user_info": user_info,
                # 나머지 필드들 초기화
                "intent": None,
                "embedding_vector": None,
                "memory_results": None,
                "similarity_score": None,
                "profiling_data": None,
                "connection_suggestions": None,
                "final_response": None
            }
            
            print(f"🎯 조건부 분기 그래프 실행...")
            
            # 전체 그래프 실행 (조건부 분기로 메시지 처리)
            result = await graph.ainvoke(input_state, config)
            
            print(f"🎯 조건부 분기 실행 완료")
            print(f"📤 실행 결과 키들: {list(result.keys())}")
            
            # 최종 응답 추출
            final_response = result.get("final_response")
            
            if final_response is None:
                print("❌ final_response가 None입니다!")
                print(f"📋 result 전체 내용: {result}")
                final_response = "조건부 분기: 응답을 생성할 수 없습니다."
            
            print(f"✅ 조건부 분기 최종 응답: {str(final_response)[:100]}...")
            return final_response
            
        except Exception as e:
            print(f"❌ 조건부 분기 처리 실패: {e}")
            import traceback
            print(f"📋 상세 에러: {traceback.format_exc()}")
            return f"죄송합니다. 메시지 처리 중 오류가 발생했습니다: {str(e)}"
    
    async def close_chat_session(self, room_id: str):
        """채팅 세션 종료"""
        if room_id in self.active_sessions:
            del self.active_sessions[room_id]
            print(f"🚪 조건부 분기 채팅 세션 종료: {room_id}")
    
    def get_session_status(self, room_id: str) -> Dict[str, Any]:
        """세션 상태 조회"""
        if room_id in self.active_sessions:
            return {
                "room_id": room_id,
                "status": "active",
                "thread_id": self.active_sessions[room_id]["thread_id"]
            }
        return {"room_id": room_id, "status": "inactive"}
    
    async def _generate_welcome_message(self, user_info: Dict[str, Any]) -> str:
        """간단한 환영 메시지 생성 (테스트용)"""
        name = user_info.get('name', '사용자')
        return f"안녕하세요 {name}님! G.Navi입니다. 무엇을 도와드릴까요?"