# app/graphs/nodes/intent_analysis.py
"""
🎯 2단계: 사용자 의도 분석 및 상황 이해 노드

이 노드는 AgentRAG 워크플로우의 두 번째 단계로, 다음 작업을 수행합니다:
1. 사용자 질문의 의도와 목적 분석
2. 과거 대화 내역을 통한 맥락 이해
3. 커리어 검색에 필요한 핵심 키워드 추출
4. 후속 단계(데이터 검색)에 필요한 분석 정보 제공

📊 분석 결과:
- intent: 질문의 주요 의도 분류
- career_history: 커리어 사례 검색용 키워드 (최대 3개)
- 사용자 프로필과 대화 맥락을 종합한 상황 이해
"""

import logging
from datetime import datetime
from app.graphs.state import ChatState
from app.graphs.agents.analyzer import IntentAnalysisAgent


class IntentAnalysisNode:
    """
    🎯 사용자 의도 분석 및 상황 이해 노드
    
    AgentRAG 워크플로우의 2단계로, 사용자 질문을 분석하여
    다음 단계에 필요한 검색 키워드와 의도 정보를 추출합니다.
    """

    def __init__(self, graph_builder_instance):
        self.graph_builder = graph_builder_instance
        self.intent_analysis_agent = IntentAnalysisAgent()
        self.logger = logging.getLogger(__name__)

    def analyze_intent_node(self, state: ChatState) -> ChatState:
        """
        🔍 2단계: 사용자 의도 분석 및 상황 이해
        
        사용자 질문과 대화 맥락을 분석하여 의도를 파악하고,
        다음 단계의 데이터 검색에 필요한 키워드를 추출합니다.
        
        Args:
            state: 현재 워크플로우 상태
            
        Returns:
            ChatState: 의도 분석 결과가 포함된 상태
        """
        import time
        start_time = time.perf_counter()
        
        try:
            # 메시지 검증 실패 시 처리 건너뛰기
            if state.get("workflow_status") == "validation_failed":
                print(f"⚠️  [2단계] 메시지 검증 실패로 처리 건너뛰기")
                return state
                
            print(f"\n🎯 [2단계] 의도 분석 및 상황 이해 시작...")
            self.logger.info("=== 2단계: 의도 분석 및 상황 이해 ===")
            
            # 세션 정보에서 사용자 데이터 가져오기
            user_data = self.graph_builder.get_user_info_from_session(state)
            
            intent_analysis = self.intent_analysis_agent.analyze_intent_and_context(
                user_question=state.get("user_question", ""),
                user_data=user_data,
                chat_history=state.get("current_session_messages", [])
            )
            
            state["intent_analysis"] = intent_analysis
            state["processing_log"].append("의도 분석 및 상황 이해 완료")
            
            # 처리 시간 계산 및 로그
            end_time = time.perf_counter()
            step_time = end_time - start_time
            
            if step_time < 0.001:
                time_display = f"{step_time * 1000000:.0f}μs"
            elif step_time < 0.01:
                time_display = f"{step_time * 1000:.1f}ms"
            else:
                time_display = f"{step_time:.3f}초"
            
            processing_log = state.get("processing_log", [])
            processing_log.append(f"2단계 처리 시간: {time_display}")
            state["processing_log"] = processing_log
            
            # 분석 결과 요약
            intent_type = intent_analysis.get("intent", "일반 상담")
            career_keywords = intent_analysis.get("career_history", [])
            
            print(f"✅ [2단계] 의도 분석 및 상황 이해 완료")
            print(f"📊 분석된 의도: {intent_type}")
            print(f"🔍 키워드 추출: {len(career_keywords)}개")
            print(f"⏱️  [2단계] 처리 시간: {time_display}")
            
            self.logger.info("의도 분석 및 상황 이해 완료")
            
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
            processing_log.append(f"2단계 처리 시간 (오류): {time_display}")
            state["processing_log"] = processing_log
            
            error_msg = f"의도 분석 실패: {e}"
            self.logger.error(error_msg)
            state["error_messages"].append(error_msg)
            state["intent_analysis"] = {
                "error": str(e),
                "career_history": []
            }
            
            print(f"❌ [2단계] 의도 분석 오류: {time_display} (오류: {e})")
        
        return state