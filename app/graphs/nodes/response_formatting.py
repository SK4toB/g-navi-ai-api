# app/graphs/nodes/response_formatting.py
"""
📝 4단계: 적응적 응답 포맷팅 노드

이 노드는 AgentRAG 워크플로우의 네 번째 단계로, 다음 작업을 수행합니다:
1. 검색된 데이터와 사용자 맥락을 종합한 개인화 응답 생성
2. 질문 유형에 따른 적응적 응답 포맷 선택
3. 사용자 친화적이고 자연스러운 대화체 생성
4. current_session_messages에 AI 응답 추가 (MemorySaver 연동)

🎨 응답 유형:
- adaptive: 일반적인 상담 및 조언
- career_guidance: 체계적인 커리어 가이던스  
- conversation: 가벼운 대화 및 인사
- summary: 이전 대화 요약
"""

import logging
from datetime import datetime
from app.graphs.state import ChatState
from app.graphs.agents.formatter import ResponseFormattingAgent


class ResponseFormattingNode:
    """
    📝 적응적 응답 포맷팅 노드
    
    AgentRAG 워크플로우의 4단계로, 검색된 데이터를 바탕으로
    사용자에게 최적화된 개인화 응답을 생성합니다.
    """

    def __init__(self, graph_builder_instance):
        self.graph_builder = graph_builder_instance
        self.response_formatting_agent = ResponseFormattingAgent()
        self.logger = logging.getLogger(__name__)

    def format_response_node(self, state: ChatState) -> ChatState:
        """
        ✨ 4단계: 적응적 응답 포맷팅
        
        검색된 커리어 사례와 교육과정 데이터를 활용하여
        사용자 질문에 대한 개인화된 응답을 생성합니다.
        
        Args:
            state: 현재 워크플로우 상태 (검색 결과 포함)
            
        Returns:
            ChatState: 포맷팅된 응답이 포함된 상태
        """
        import time
        start_time = time.perf_counter()
        
        try:
            # 메시지 검증 실패 시 처리 건너뛰기
            if state.get("workflow_status") == "validation_failed":
                print(f"⚠️  [4단계] 메시지 검증 실패로 처리 건너뛰기")
                return state
                
            print(f"\n📝 [4단계] 적응적 응답 포맷팅 시작...")
            self.logger.info("=== 4단계: 적응적 응답 포맷팅 ===")
            
            # 성장 방향 상담인지 확인 (다이어그램은 5단계에서 별도 처리)
            user_question = state.get("user_question", "")
            
            # 모든 요청에 대해 기본 적응적 응답 생성
            final_response = self.response_formatting_agent.format_adaptive_response(
                user_question=user_question,
                state=state
            )
            
            final_response["format_type"] = final_response.get("format_type", "adaptive")
            
            # bot_message 설정 (기본 출력 형식)
            state["formatted_response"] = final_response  # 다이어그램 생성에서 사용
            state["final_response"] = final_response
            state["processing_log"].append(f"적응적 응답 포맷팅 완료 (유형: {final_response['format_type']})")
            
            # AI 응답을 current_session_messages에 추가하여 MemorySaver가 저장하도록 함
            if "current_session_messages" not in state:
                state["current_session_messages"] = []
            
            assistant_message = {
                "role": "assistant",
                "content": final_response.get("formatted_content", ""),
                "timestamp": datetime.now().isoformat(),
                "format_type": final_response.get("format_type", "adaptive")
            }
            state["current_session_messages"].append(assistant_message)
            self.logger.info(f"AI 응답을 current_session_messages에 추가 (총 {len(state['current_session_messages'])}개 메시지)")
            
            # 4단계 완료 상세 로그 출력
            content_length = len(final_response.get("formatted_content", ""))
            format_type = final_response.get("format_type", "adaptive")
            
            # 처리 시간 계산 및 로그
            end_time = time.perf_counter()
            step_time = end_time - start_time
            
            # 시간 단위 결정
            if step_time < 0.001:  # 1ms 미만
                time_display = f"{step_time * 1000000:.0f}μs"
            elif step_time < 0.01:  # 10ms 미만
                time_display = f"{step_time * 1000:.1f}ms"
            else:
                time_display = f"{step_time:.3f}초"
            
            processing_log = state.get("processing_log", [])
            processing_log.append(f"4단계 처리 시간: {time_display}")
            state["processing_log"] = processing_log
            
            print(f"✅ [4단계] 적응적 응답 포맷팅 완료")
            print(f"📊 응답 유형: {format_type}, 길이: {content_length}자")
            print(f"⏱️  [4단계] 처리 시간: {time_display}")
            
            self.logger.info("적응적 응답 포맷팅 완료")
            
        except Exception as e:
            # 오류 발생 시에도 처리 시간 기록
            end_time = time.perf_counter()
            step_time = end_time - start_time
            
            if step_time < 0.001:
                time_display = f"{step_time * 1000000:.0f}μs"
            elif step_time < 0.01:
                time_display = f"{step_time * 1000:.1f}ms"
            else:
                time_display = f"{step_time:.3f}초"
                
            processing_log = state.get("processing_log", [])
            processing_log.append(f"4단계 처리 시간 (오류): {time_display}")
            state["processing_log"] = processing_log
            
            error_msg = f"응답 포맷팅 실패: {e}"
            self.logger.error(error_msg)
            state["error_messages"].append(error_msg)
            state["final_response"] = {"error": str(e)}
            
            print(f"❌ [4단계] 적응적 응답 포맷팅 오류: {time_display} (오류: {e})")
        
        # 총 처리 시간 계산
        try:
            total_time = sum(
                float(log.split(": ")[-1].replace("초", "").replace("ms", "").replace("μs", ""))
                for log in state.get("processing_log", [])
                if "처리 시간" in log and ("초" in log or "ms" in log or "μs" in log)
            )
            state["total_processing_time"] = total_time
        except:
            pass  # 총 시간 계산 오류는 무시
        
        return state
