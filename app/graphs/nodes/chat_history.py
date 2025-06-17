# app/graphs/nodes/chat_history.py
# 과거 대화내역 검색 노드

import logging
from datetime import datetime
from app.graphs.state import ChatState
from app.graphs.agents.retriever import CareerEnsembleRetrieverAgent


class ChatHistoryNode:
    """과거 대화내역 검색 노드"""

    def __init__(self, graph_builder_instance):
        self.graph_builder = graph_builder_instance
        self.career_retriever_agent = CareerEnsembleRetrieverAgent()
        self.logger = logging.getLogger(__name__)

    def retrieve_chat_history_node(self, state: ChatState) -> ChatState:
        """1단계: 과거 대화내역 검색"""
        start_time = datetime.now()
        try:
            self.logger.info("=== 1단계: 과거 대화내역 검색 ===")
            
            # 세션 정보에서 사용자 데이터 가져오기
            user_data = self.graph_builder.get_user_info_from_session(state)
            user_id = user_data.get("memberId") if "memberId" in user_data else user_data.get("name")
            
            if user_id:
                self.logger.info(f"사용자 {user_id}의 과거 대화내역 검색 중...")
                chat_results = self.career_retriever_agent.load_chat_history(user_id=user_id)
            else:
                self.logger.warning("사용자 ID가 없어 전체 대화내역을 로드합니다")
                chat_results = self.career_retriever_agent.load_chat_history()
            
            state["chat_history_results"] = chat_results
            state["processing_log"].append(f"과거 대화내역 검색 완료: {len(chat_results)}개 (사용자: {user_id or 'ALL'})")
            self.logger.info(f"과거 대화내역 검색 완료: {len(chat_results)}개")
            
        except Exception as e:
            error_msg = f"과거 대화내역 검색 실패: {e}"
            self.logger.error(error_msg)
            state["error_messages"].append(error_msg)
            state["chat_history_results"] = []
        
        processing_time = (datetime.now() - start_time).total_seconds()
        state["processing_log"].append(f"1단계 처리 시간: {processing_time:.2f}초")
        return state
