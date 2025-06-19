# app/graphs/nodes/retrieve_additional_data_node.py
# 추가 데이터 검색 노드 (K8s 환경 대응)

import logging
from datetime import datetime
from app.graphs.state import ChatState
from app.graphs.agents.retriever import CareerEnsembleRetrieverAgent


class DataRetrievalNode:
    """추가 데이터 검색 노드 (커리어 사례 + 외부 트렌드 + 교육과정)"""

    def __init__(self):
        self.career_retriever_agent = CareerEnsembleRetrieverAgent()
        self.logger = logging.getLogger(__name__)

    def retrieve_additional_data_node(self, state: ChatState) -> ChatState:
        """3단계: 추가 데이터 검색 (커리어 사례 + 외부 트렌드 + 교육과정)"""
        start_time = datetime.now()
        try:
            self.logger.info("=== 3단계: 추가 데이터 검색 (교육과정 포함) ===")
            
            intent_analysis = state.get("intent_analysis", {})
            user_question = state.get("message_text", "")  # message_text로 수정
            
            # 기존 커리어 히스토리 검색
            career_keywords = intent_analysis.get("career_history", [])
            if not career_keywords:
                career_keywords = [user_question]
            career_query = " ".join(career_keywords[:2])
            career_cases = self.career_retriever_agent.retrieve(career_query, k=3)
            
            # 새로운 교육과정 검색 추가
            education_results = self._search_education_courses(state, intent_analysis)
            
            # 상태 업데이트
            state["career_cases"] = career_cases
            state["external_trends"] = []  # 외부 트렌드 검색 비활성화
            state["education_courses"] = education_results  # 새로 추가
            
            # processing_log 초기화 (없으면)
            if "processing_log" not in state:
                state["processing_log"] = []
            
            state["processing_log"].append(
                f"추가 데이터 검색 완료: 커리어 사례 {len(career_cases)}개, "
                f"교육과정 {len(education_results.get('recommended_courses', []))}개"
            )
            self.logger.info(
                f"커리어 사례 {len(career_cases)}개, "
                f"교육과정 {len(education_results.get('recommended_courses', []))}개 검색 완료"
            )
            
        except Exception as e:
            error_msg = f"추가 데이터 검색 실패: {e}"
            self.logger.error(error_msg)
            
            # error_messages 초기화 (없으면)
            if "error_messages" not in state:
                state["error_messages"] = []
                
            state["error_messages"].append(error_msg)
            state["career_cases"] = []
            state["external_trends"] = []
            state["education_courses"] = {"recommended_courses": [], "course_analysis": {}, "learning_path": []}
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # processing_log 재확인
        if "processing_log" not in state:
            state["processing_log"] = []
            
        state["processing_log"].append(f"3단계 처리 시간: {processing_time:.2f}초")
        return state
    
    def _search_education_courses(self, state: ChatState, intent_analysis: dict) -> dict:
        """교육과정 검색 로직"""
        
        # 사용자 프로필 정보 추출
        user_data = state.get("user_info", {})  # user_data -> user_info로 수정
        user_question = state.get("message_text", "")  # user_question -> message_text로 수정
        
        # 교육과정 관련 키워드 감지 (더 넓은 범위)
        education_keywords = [
            "교육", "과정", "학습", "스킬", "배우", "공부", "강의", "수업", "커리큘럼", "교육과정",
            "추천", "개발", "향상", "성장", "능력", "역량", "전문성", "경력", "취업", "이직",
            "AI", "데이터", "프로그래밍", "개발자", "분석", "머신러닝", "프로젝트"
        ]
        
        # AI/기술 관련 쿼리도 교육과정 추천 대상에 포함
        ai_tech_keywords = ["AI", "인공지능", "데이터분석", "머신러닝", "딥러닝", "프로그래밍", "개발", "코딩"]
        
        is_education_query = (
            any(keyword in user_question for keyword in education_keywords) or
            any(keyword in user_question for keyword in ai_tech_keywords) or
            intent_analysis.get("intent") == "course_recommendation"
        )
        
        # 모든 쿼리에 대해 교육과정을 추천하도록 변경 (더 나은 사용자 경험 제공)
        # if not is_education_query:
        #     return {"recommended_courses": [], "course_analysis": {}, "learning_path": []}
        
        try:
            # CareerEnsembleRetrieverAgent의 교육과정 검색 활용
            education_results = self.career_retriever_agent.search_education_courses(
                query=user_question,
                user_profile=user_data,
                intent_analysis=intent_analysis
            )
            
            self.logger.info(f"교육과정 검색 완료: {len(education_results.get('recommended_courses', []))}개")
            return education_results
            
        except Exception as e:
            self.logger.error(f"교육과정 검색 중 오류: {e}")
            return {"recommended_courses": [], "course_analysis": {}, "learning_path": []}


# 전역 인스턴스 생성
_data_retrieval_node = DataRetrievalNode()

# 노드 함수 정의 (기존 패턴과 일치)
async def process(state: ChatState) -> ChatState:
    """추가 데이터 검색 노드 처리 함수"""
    print("=== G.Navi 3단계: 추가 데이터 검색 (업데이트됨) ===")
    return _data_retrieval_node.retrieve_additional_data_node(state)