# app/graphs/nodes/data_retrieval.py
# 추가 데이터 검색 노드

import logging
from datetime import datetime
from app.graphs.state import ChatState
from app.graphs.agents.retriever import CareerEnsembleRetrieverAgent


class DataRetrievalNode:
    """추가 데이터 검색 노드 (커리어 사례 + 외부 트렌드)"""

    def __init__(self):
        self.career_retriever_agent = CareerEnsembleRetrieverAgent()
        self.logger = logging.getLogger(__name__)

    def retrieve_additional_data_node(self, state: ChatState) -> ChatState:
        """3단계: 추가 데이터 검색 (커리어 사례 + 외부 트렌드)"""
        start_time = datetime.now()
        try:
            self.logger.info("=== 3단계: 추가 데이터 검색 ===")
            
            intent_analysis = state.get("intent_analysis", {})
            user_question = state.get("user_question", "")
            
            # 커리어 히스토리 검색
            career_keywords = intent_analysis.get("career_history", [])
            if not career_keywords:
                career_keywords = [user_question]
            career_query = " ".join(career_keywords[:2])
            career_cases = self.career_retriever_agent.retrieve(career_query, k=3)
            
            # 외부 트렌드 검색
            trend_keywords = intent_analysis.get("external_trends", [])
            if not trend_keywords:
                trend_keywords = [user_question]
            external_trends = self.career_retriever_agent.search_external_trends_with_tavily(trend_keywords[:2])
            
            if len(external_trends) > 3:
                external_trends = external_trends[:3]
            
            state["career_cases"] = career_cases
            state["external_trends"] = external_trends
            state["processing_log"].append(
                f"추가 데이터 검색 완료: 커리어 사례 {len(career_cases)}개, 트렌드 정보 {len(external_trends)}개"
            )
            self.logger.info(f"커리어 사례 {len(career_cases)}개, 트렌드 정보 {len(external_trends)}개 검색 완료")
            
        except Exception as e:
            error_msg = f"추가 데이터 검색 실패: {e}"
            self.logger.error(error_msg)
            state["error_messages"].append(error_msg)
            state["career_cases"] = []
            state["external_trends"] = []
        
        processing_time = (datetime.now() - start_time).total_seconds()
        state["processing_log"].append(f"3단계 처리 시간: {processing_time:.2f}초")
        return state
