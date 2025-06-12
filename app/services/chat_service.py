# app/services/chat_service.py
# G.Navi AgentRAG 채팅 서비스

from typing import Dict, Any
import os
import logging
from datetime import datetime
from app.graphs.graph_builder import ChatGraphBuilder

class ChatService:
    """
    G.Navi AgentRAG 채팅 서비스
    5단계 워크플로우를 통한 커리어 컨설팅
    """
    
    def __init__(self):
        self.graph_builder = ChatGraphBuilder()
        self.active_sessions = {}  # session_id -> {graph, config, user_data}
        self.logger = logging.getLogger(__name__)
        print("ChatService 초기화 (G.Navi AgentRAG)")
    
    async def create_chat_session(self, conversation_id: str, user_info: Dict[str, Any]) -> str:
        """
        G.Navi 채팅 세션 생성
        """
        print(f"G.Navi 채팅 세션 생성: {conversation_id}")
        
        try:
            # 1. LangGraph 빌드
            compiled_graph = await self.graph_builder.build_persistent_chat_graph(conversation_id, user_info)
            
            # 2. 세션 정보 저장
            thread_id = f"thread_{conversation_id}"
            config = {"configurable": {"thread_id": thread_id}}
            
            self.active_sessions[conversation_id] = {
                "graph": compiled_graph,
                "thread_id": thread_id,
                "config": config,
                "user_info": user_info
            }
            
            print(f"G.Navi 세션 생성 완료: {conversation_id}")
            
            # 3. 환영 메시지 생성
            initial_message = await self._generate_welcome_message(user_info)
            
            return initial_message
            
        except Exception as e:
            error_msg = f"세션 생성 실패: {e}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
    
    async def send_message(self, conversation_id: str, member_id: str, message_text: str) -> str:
        """
        G.Navi 메시지 처리 (5단계 AgentRAG 워크플로우)
        기존 시그니처 유지하되 내부는 G.Navi 방식으로 처리
        """
        print(f"G.Navi 메시지 처리: {conversation_id}")
        
        if conversation_id not in self.active_sessions:
            raise ValueError(f"활성화된 세션이 없습니다: {conversation_id}")
        
        session = self.active_sessions[conversation_id]
        graph = session["graph"]
        config = session["config"]
        user_info = session.get("user_info", {})
        
        try:
            print(f"📨 입력 메시지: {message_text}")
            
            # G.Navi 상태 구성 (기존 파라미터들을 G.Navi 형식으로 변환)
            input_state = {
                "user_question": message_text,  # message_text를 user_question으로 사용
                "user_data": user_info,         # user_info를 user_data로 사용
                "session_id": conversation_id,  # conversation_id를 session_id로 사용
                # 초기화될 필드들
                "chat_history_results": [],
                "intent_analysis": {},
                "career_cases": [],
                "external_trends": [],
                "recommendation": {},
                "final_response": {},
                "processing_log": [],
                "error_messages": [],
                "total_processing_time": 0.0
            }
            
            print(f"G.Navi AgentRAG 실행 시작...")
            start_time = datetime.now()
            
            # 전체 그래프 실행 (5단계 워크플로우)
            result = await graph.ainvoke(input_state, config)
            
            end_time = datetime.now()
            total_time = (end_time - start_time).total_seconds()
            
            print(f"G.Navi AgentRAG 실행 완료 (총 {total_time:.2f}초)")
            print(f"실행 결과 키들: {list(result.keys())}")
            
            # 최종 응답 추출 (기존 방식과 호환되도록 문자열 반환)
            final_response = result.get("final_response", {})
            
            if not final_response or "error" in final_response:
                error_msg = final_response.get("error", "알 수 없는 오류")
                print(f"처리 실패: {error_msg}")
                return f"죄송합니다. 시스템 오류로 인해 상담을 제공할 수 없습니다: {error_msg}"
            
            # formatted_content를 문자열로 반환 (기존 호환성)
            formatted_content = final_response.get("formatted_content", "")
            
            if formatted_content:
                print(f"G.Navi 최종 응답 준비 완료 (형식: {final_response.get('format_type', 'unknown')})")
                
                # 처리 로그 출력 (디버깅용)
                processing_log = result.get("processing_log", [])
                for log in processing_log:
                    print(f"  📊 {log}")
                
                return formatted_content
            else:
                return "응답을 생성할 수 없습니다."
            
        except Exception as e:
            error_msg = f"메시지 처리 실패: {e}"
            self.logger.error(error_msg)
            import traceback
            self.logger.error(f"상세 에러: {traceback.format_exc()}")
            
            return f"죄송합니다. 메시지 처리 중 오류가 발생했습니다: {str(e)}"
    
    async def close_chat_session(self, conversation_id: str):
        """채팅 세션 종료"""
        if conversation_id in self.active_sessions:
            del self.active_sessions[conversation_id]
            print(f"G.Navi 채팅 세션 종료: {conversation_id}")
    
    def get_session_status(self, conversation_id: str) -> Dict[str, Any]:
        """세션 상태 조회"""
        if conversation_id in self.active_sessions:
            session = self.active_sessions[conversation_id]
            return {
                "conversation_id": conversation_id,
                "status": "active",
                "thread_id": session["thread_id"]
            }
        return {
            "conversation_id": conversation_id, 
            "status": "inactive"
        }
    
    async def _generate_welcome_message(self, user_info: Dict[str, Any]) -> str:
        """환영 메시지 생성"""
        name = user_info.get("name", "이재원")
        
        welcome_message = f"""안녕하세요 {name}님! 👋

G.Navi AI 커리어 컨설팅에 오신 것을 환영합니다.

저는 여러분의 커리어 여정을 함께할 AI 컨설턴트입니다. 다음과 같은 도움을 드릴 수 있습니다:

🎯 **커리어 방향성 설정**
📈 **기술 스택 및 학습 로드맵 제안**  
🔍 **업계 트렌드 및 전망 분석**
💼 **이직 및 취업 전략 수립**
🚀 **개인 프로젝트 기획 및 포트폴리오 개선**

궁금한 것이 있으시면 언제든 말씀해 주세요!"""

        return welcome_message