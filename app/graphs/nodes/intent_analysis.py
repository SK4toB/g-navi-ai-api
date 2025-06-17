# app/graphs/nodes/intent_analysis.py
# 의도 분석 노드

import logging
from datetime import datetime
from app.graphs.state import ChatState
from app.graphs.agents.analyzer import IntentAnalysisAgent


class IntentAnalysisNode:
    """의도 분석 및 상황 이해 노드"""

    def __init__(self, graph_builder_instance):
        self.graph_builder = graph_builder_instance
        self.intent_analysis_agent = IntentAnalysisAgent()
        self.logger = logging.getLogger(__name__)

    def analyze_intent_node(self, state: ChatState) -> ChatState:
        """2단계: 의도 분석 및 상황 이해"""
        start_time = datetime.now()
        
        try:
            self.logger.info("=== 2단계: 의도 분석 및 상황 이해 ===")
            
            # 세션 정보에서 사용자 데이터 가져오기
            user_data = self.graph_builder.get_user_info_from_session(state)
            
            intent_analysis = self.intent_analysis_agent.analyze_intent_and_context(
                user_question=state.get("user_question", ""),
                user_data=user_data,
                chat_history=state.get("chat_history_results", [])
            )
            
            state["intent_analysis"] = intent_analysis
            state["processing_log"].append("의도 분석 및 상황 이해 완료")
            
            self.logger.info("의도 분석 및 상황 이해 완료")
            
        except Exception as e:
            error_msg = f"의도 분석 실패: {e}"
            self.logger.error(error_msg)
            state["error_messages"].append(error_msg)
            state["intent_analysis"] = {
                "error": str(e),
                "question_type": "professional",
                "requires_full_analysis": True,
                "simple_response": False
            }
        
        processing_time = (datetime.now() - start_time).total_seconds()
        state["processing_log"].append(f"2단계 처리 시간: {processing_time:.2f}초")
        
        return state
