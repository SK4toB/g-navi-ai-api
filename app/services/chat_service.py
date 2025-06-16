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
            
            # 3. 개인화된 환영 메시지 생성
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
            # GraphBuilder의 세션 정보도 함께 정리
            self.graph_builder.close_session(conversation_id)
            del self.active_sessions[conversation_id]
            print(f"G.Navi 채팅 세션 종료: {conversation_id}")
        else:
            print(f"세션을 찾을 수 없음: {conversation_id}")
    
    def get_session_status(self, conversation_id: str) -> Dict[str, Any]:
        """세션 상태 조회"""
        if conversation_id in self.active_sessions:
            session = self.active_sessions[conversation_id]
            return {
                "conversation_id": conversation_id,
                "status": "active",
                "thread_id": session["thread_id"],
                "user_info": session.get("user_info", {})
            }
        return {
            "conversation_id": conversation_id, 
            "status": "inactive"
        }
    
    async def _generate_welcome_message(self, user_info: Dict[str, Any]) -> str:
        """개인화된 환영 메시지 생성"""
        name = user_info.get("name", "사용자")
        projects = user_info.get("projects", [])
        
        # 기본 환영 메시지
        welcome_message = f"안녕하세요 {name}님! 👋 G.Navi AI 커리어 컨설턴트입니다."
        
        # 프로젝트 경험이 있는 경우 개인화된 제안
        if projects:
            latest_project = projects[0]
            role = latest_project.get("role", "")
            domain = latest_project.get("domain", "")
            
            if role and domain:
                welcome_message += f"\n{domain} 분야에서 {role}로 활동하고 계시는군요! 요즘 커리어 발전 방향이나 새로운 기회에 대해 고민이 있으시다면 언제든 말씀해 주세요."
            elif role:
                welcome_message += f"\n{role}로 활동하고 계시는군요! 커리어 발전이나 새로운 도전에 대해 궁금한 점이 있으시면 언제든 이야기해 주세요."
            elif domain:
                welcome_message += f"\n{domain} 분야에서 활동하고 계시는군요! 업계 동향이나 커리어 방향에 대해 궁금한 점이 있으시면 언제든 말씀해 주세요."
            else:
                welcome_message += "\n프로젝트 경험을 바탕으로 더 나은 커리어 방향을 함께 찾아보실까요?"
        else:
            welcome_message += "\n커리어 시작이나 새로운 방향 설정에 대해 궁금한 점이 있으시면 언제든 말씀해 주세요."

        return welcome_message