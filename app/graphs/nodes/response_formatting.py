# app/graphs/nodes/response_formatting.py
"""
* @className : ResponseFormattingNode
* @description : 응답 포맷팅 노드 모듈
*                검색 결과를 포맷팅하는 워크플로우 노드입니다.
*                사용자 친화적인 응답 형태로 변환합니다.
*
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from typing import Annotated

from app.graphs.state import ChatState
from app.graphs.agents.formatter import ResponseFormattingAgent


class ResponseFormattingNode:
    """
    적응적 응답 포맷팅 노드
    
    AgentRAG 워크플로우의 4단계로, 검색된 데이터를 바탕으로
    사용자에게 최적화된 개인화 응답을 생성합니다.
    
    Attributes:
        graph_builder: 그래프 빌더 인스턴스
        response_formatting_agent: 응답 포맷팅 에이전트
        logger: 로깅 인스턴스
    """

    def __init__(self, graph_builder_instance: Any) -> None:
        """
        응답 포맷팅 노드 초기화
        
        Args:
            graph_builder_instance: 그래프 빌더 인스턴스
        """
        self.graph_builder = graph_builder_instance
        self.response_formatting_agent = ResponseFormattingAgent()
        self.logger: logging.Logger = logging.getLogger(__name__)

    def format_response_node(self, 
                           state: Annotated[ChatState, "현재 워크플로우 상태 (검색 결과 포함)"]
                           ) -> Annotated[ChatState, "포맷팅된 응답이 포함된 상태"]:
        """
        4단계: 적응적 응답 포맷팅
        
        검색된 커리어 사례와 교육과정 데이터를 활용하여
        사용자 질문에 대한 개인화된 응답을 생성합니다.
        
        Args:
            state: 현재 워크플로우 상태 (검색 결과 포함)
            
        Returns:
            ChatState: 포맷팅된 응답이 포함된 상태
            
        Raises:
            Exception: 응답 포맷팅 중 오류 발생 시
        """
        import time
        start_time: float = time.perf_counter()
        
        try:  # 응답 포맷팅 처리 시작
            # 메시지 검증 실패 시 처리 건너뛰기
            workflow_status: Optional[str] = state.get("workflow_status")
            if workflow_status == "validation_failed":  # 검증 실패 상태 확인
                print(f"[4단계] 메시지 검증 실패로 처리 건너뛰기")
                return state
                
            print(f"\n[4단계] 적응적 응답 포맷팅 시작...")
            self.logger.info("=== 4단계: 적응적 응답 포맷팅 ===")
            
            # 성장 방향 상담인지 확인 (다이어그램은 5단계에서 별도 처리)
            user_question: str = state.get("user_question", "")  # 사용자 질문 조회
            
            # 모든 요청에 대해 기본 적응적 응답 생성
            final_response: Dict[str, Any] = self.response_formatting_agent.format_adaptive_response(  # 적응적 응답 포맷팅 에이전트 호출
                user_question=user_question,
                state=state
            )
            
            final_response["format_type"] = final_response.get("format_type", "adaptive")
            
            # bot_message 설정 (기본 출력 형식)
            state["formatted_response"] = final_response  # 다이어그램 생성에서 사용
            state["final_response"] = final_response
            
            processing_log: List[str] = state.get("processing_log", [])
            processing_log.append(f"적응적 응답 포맷팅 완료 (유형: {final_response['format_type']})")
            state["processing_log"] = processing_log
            
            # AI 응답을 current_session_messages에 추가하여 MemorySaver가 저장하도록 함
            current_session_messages: List[Dict[str, Any]] = state.get("current_session_messages", [])
            if not current_session_messages:  # 세션 메시지가 없는 경우
                current_session_messages = []  # 빈 리스트로 초기화
                state["current_session_messages"] = current_session_messages
            
            assistant_message: Dict[str, Any] = {
                "role": "assistant",
                "content": final_response.get("formatted_content", ""),
                "timestamp": datetime.now().isoformat(),
                "format_type": final_response.get("format_type", "adaptive")
            }
            current_session_messages.append(assistant_message)
            self.logger.info(f"AI 응답을 current_session_messages에 추가 (총 {len(current_session_messages)}개 메시지)")
            
            #  ConversationHistoryManager에도 AI 응답 추가 (세션 종료 시 VectorDB 구축을 위해)
            try:
                if hasattr(self.graph_builder, 'conversation_history_manager'):
                    self.graph_builder.conversation_history_manager.add_ai_response(
                        session_id=state.get("session_id", ""),
                        content=final_response.get("formatted_content", ""),
                        format_type=final_response.get("format_type", "adaptive")
                    )
            except Exception as e:
                self.logger.warning(f"ConversationHistoryManager 응답 추가 실패: {e}")
            
            # 4단계 완료 상세 로그 출력
            content_length: int = len(final_response.get("formatted_content", ""))  # 응답 길이 계산
            format_type: str = final_response.get("format_type", "adaptive")  # 포맷 타입 확인
            
            # 처리 시간 계산 및 로그
            end_time: float = time.perf_counter()
            step_time: float = end_time - start_time
            time_display: str = f"{step_time*1000:.0f}ms" if step_time < 1 else f"{step_time:.2f}s"
            
            processing_log = state.get("processing_log", [])
            processing_log.append(f"4단계 처리 시간: {time_display}")
            state["processing_log"] = processing_log
            
            print(f"[4단계] 적응적 응답 포맷팅 완료")
            print(f"응답 유형: {format_type}, 길이: {content_length}자")
            print(f"[4단계] 처리 시간: {time_display}")
            
            self.logger.info("적응적 응답 포맷팅 완료")
            
        except Exception as e:  # 예외 처리
            # 오류 발생 시에도 처리 시간 기록
            end_time = time.perf_counter()
            step_time = end_time - start_time
            time_display = f"{step_time*1000:.0f}ms" if step_time < 1 else f"{step_time:.2f}s"
                
            processing_log = state.get("processing_log", [])
            processing_log.append(f"4단계 처리 시간 (오류): {time_display}")
            state["processing_log"] = processing_log
            
            error_msg: str = f"응답 포맷팅 실패: {e}"
            self.logger.error(error_msg)
            
            error_messages: List[str] = state.get("error_messages", [])
            error_messages.append(error_msg)
            state["error_messages"] = error_messages
            state["final_response"] = {"error": str(e)}
            
            print(f"[4단계] 적응적 응답 포맷팅 오류: {time_display} (오류: {e})")
        
        # 총 처리 시간 계산
        try:
            workflow_start_time = state.get("workflow_start_time")
            if workflow_start_time:
                total_time = time.perf_counter() - workflow_start_time
                total_time_display = f"{total_time*1000:.0f}ms" if total_time < 1 else f"{total_time:.2f}s"
                
                processing_log = state.get("processing_log", [])
                processing_log.append(f"전체 워크플로우 처리 시간: {total_time_display}")
                state["processing_log"] = processing_log
                
                print(f"⏱전체 워크플로우 처리 시간: {total_time_display}")
                self.logger.info(f"전체 워크플로우 처리 시간: {total_time_display}")
        except Exception as e:
            self.logger.warning(f"전체 처리 시간 계산 실패: {e}")
        
        return state
