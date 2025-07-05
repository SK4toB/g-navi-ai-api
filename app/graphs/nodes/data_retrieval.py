# app/graphs/nodes/data_retrieval.py
"""
* @className : DataRetrievalNode
* @description : 데이터 검색 노드 모듈
*                관련 데이터를 검색하는 워크플로우 노드입니다.
*                커리어 사례, 교육과정, 뉴스 데이터, 과거 대화를 검색합니다.
*
* @modification : 2025.07.01(이재원) 최초생성
*
* @author 이재원
* @Date 2025.07.01
* @version 1.1
* @see CareerEnsembleRetrieverAgent, NewsRetrieverAgent, ChatState
*  == 개정이력(Modification Information) ==
*  
*   수정일        수정자        수정내용
*   ----------   --------     ---------------------------
*   2025.07.01   이재원       최초 생성
*   2025.07.01   이재원       뉴스 데이터 검색 기능 추가, Agent 직접 호출 패턴 적용
*  
* Copyright (C) by G-Navi AI System All right reserved.
"""

import logging
from datetime import datetime
from app.graphs.state import ChatState
from app.graphs.agents.retriever import CareerEnsembleRetrieverAgent


class DataRetrievalNode:
    """
    🔍 추가 데이터 검색 노드 (커리어 사례 + 교육과정 + 뉴스 데이터 + 과거 대화)
    
    AgentRAG 워크플로우의 3단계로, 의도 분석 결과를 바탕으로
    관련 커리어 사례, 교육과정, 뉴스 데이터, 과거 대화 내역을 검색하여 
    상담 근거를 확보합니다.
    
    🔗 검색 데이터 종류:
    - 커리어 사례: 유사한 경력 전환 성공 사례
    - 교육과정: 개인화된 학습 경로 및 과정 추천
    - 뉴스 데이터: 최신 산업 동향 및 관련 뉴스
    - 과거 대화: 사용자별 개인화된 상담 이력
    """

    def __init__(self):
        self.career_retriever_agent = CareerEnsembleRetrieverAgent()
        self.logger = logging.getLogger(__name__)
        
        # 뉴스 검색 에이전트 초기화 (지연 로딩)
        self.news_retriever_agent = None

    def retrieve_additional_data_node(self, state: ChatState) -> ChatState:
        """
        🔎 3단계: 추가 데이터 검색 (커리어 사례 + 교육과정 + 뉴스 데이터 + 과거 대화)
        
        의도 분석에서 추출된 키워드를 사용하여 다음 데이터를 Vector Store에서 검색합니다:
        - 관련 커리어 사례 (성공 사례 및 전환 경험)
        - 개인화된 교육과정 (학습 경로 포함)
        - 최신 뉴스 데이터 (산업 동향 및 관련 정보)
        - 과거 대화 내역 (개인화된 상담 이력)
        
        Args:
            state: 현재 워크플로우 상태 (의도 분석 결과 포함)
            
        Returns:
            ChatState: 검색된 모든 데이터가 포함된 상태
        """
        import time
        start_time = time.perf_counter()
        
        try:  # 데이터 검색 처리 시작
            # 메시지 검증 실패 시 처리 건너뛰기
            if state.get("workflow_status") == "validation_failed":  # 검증 실패 상태 확인
                print(f"⚠️  [3단계] 메시지 검증 실패로 처리 건너뛰기")
                return state
                
            print(f"\n🔍 [3단계] 추가 데이터 검색 시작...")
            self.logger.info("=== 3단계: 추가 데이터 검색 (커리어 + 교육과정 + 뉴스 + 과거대화) ===")
            
            intent_analysis = state.get("intent_analysis", {})  # 의도 분석 결과 조회
            user_question = state.get("user_question", "")  # 사용자 질문 조회
            
            # 1. 과거 대화 내역 검색 (개인화)
            past_conversations = self._search_past_conversations(state)  # 과거 대화 검색 호출
            
            # 2. 커리어 사례 검색 (성공 사례)
            user_data = state.get("user_data", {})
            user_experience = user_data.get("experience")
            # '비슷한 연차' 관련 질의 감지
            similar_exp_keywords = ["비슷한 연차", "동일 연차", "내 연차", "비슷한 경력", "비슷한 CL", "비슷한 경험자"]
            is_similar_exp_query = any(kw in user_question for kw in similar_exp_keywords)
            # 2. 커리어 사례 검색 (성공 사례)
            career_keywords = intent_analysis.get("career_history", [])  # 커리어 키워드 추출
            if not career_keywords:  # 키워드가 없는 경우
                career_keywords = [user_question]  # 사용자 질문을 키워드로 사용
            career_query = " ".join(career_keywords[:2])  # 상위 2개 키워드를 쿼리로 조합
            career_search_count = state.get("career_search_count", 2)
            print(f"🔍 DEBUG - 커리어 검색 요청: k={career_search_count}, query='{career_query}'")
            career_cases = self.career_retriever_agent.retrieve(career_query, k=career_search_count*2 if is_similar_exp_query else career_search_count)
            # 연차 필터링: 비슷한 연차 질의일 때만
            if is_similar_exp_query and user_experience:
                filtered_cases = []
                for case in career_cases:
                    metadata = getattr(case, 'metadata', {})
                    case_exp = metadata.get('experience')
                    if case_exp and case_exp == user_experience:
                        filtered_cases.append(case)
                # 필터링된 결과가 있으면 우선 사용, 없으면 기존 방식 fallback
                if filtered_cases:
                    career_cases = filtered_cases[:career_search_count]
                else:
                    career_cases = career_cases[:career_search_count]
            else:
                career_cases = career_cases[:career_search_count]
            
            # 각 검색 결과의 메타데이터 확인
            for i, case in enumerate(career_cases):  # 검색 결과 순회
                metadata = getattr(case, 'metadata', {})  # 메타데이터 조회
                employee_id = metadata.get('employee_id', 'Unknown')  # 직원 ID 조회
                print(f"🔍 DEBUG - 결과 {i+1}: Employee {employee_id}")
            # end for (검색 결과 순회)
            
            if len(career_cases) < career_search_count:  # 검색 결과가 요청보다 적은 경우
                print(f"⚠️ WARNING - 요청한 {career_search_count}개보다 적은 {len(career_cases)}개만 검색됨")
                print(f"⚠️ WARNING - Vector Store에 저장된 데이터가 부족하거나 검색 쿼리와 유사도가 낮은 것으로 추정")
            
            # 3. 교육과정 검색 (학습 경로)
            education_results = self._search_education_courses(state, intent_analysis)  # 교육과정 검색 호출
            
            # 4. 뉴스 데이터 검색 (최신 동향)
            news_results = self._get_news_results(state, intent_analysis)  # 뉴스 데이터 검색 호출
            
            # 상태 업데이트
            state["past_conversations"] = past_conversations
            state["career_cases"] = career_cases
            state["education_courses"] = education_results
            state["news_data"] = news_results
            
            state["processing_log"].append(
                f"데이터 검색 완료 (검색 개수: {career_search_count}): 커리어 사례 {len(career_cases)}개, "
                f"교육과정 {len(education_results.get('recommended_courses', []))}개, "
                f"뉴스 데이터 {len(news_results)}개, "
                f"과거 대화 {len(past_conversations)}개"
            )
            
            # 처리 시간 계산 및 로그
            end_time = time.perf_counter()
            step_time = end_time - start_time
            
            if step_time < 0.001:  # 마이크로초 단위인 경우
                time_display = f"{step_time * 1000000:.0f}μs"
            elif step_time < 0.01:  # 밀리초 단위인 경우
                time_display = f"{step_time * 1000:.1f}ms"
            else:  # 초 단위인 경우
                time_display = f"{step_time:.3f}초"
            
            processing_log = state.get("processing_log", [])
            processing_log.append(f"3단계 처리 시간: {time_display}")
            state["processing_log"] = processing_log
            
            print(f"✅ [3단계] 추가 데이터 검색 완료")
            print(f"📊 커리어 사례: {len(career_cases)}개 (요청 개수: {career_search_count}), 교육과정: {len(education_results.get('recommended_courses', []))}개, 뉴스: {len(news_results)}개, 과거 대화: {len(past_conversations)}개")
            print(f"🔍 검색 쿼리: {career_query[:50]}...")
            print(f"⏱️  [3단계] 처리 시간: {time_display}")
            
            self.logger.info(
                f"커리어 사례 {len(career_cases)}개 (요청 개수: {career_search_count}), "
                f"교육과정 {len(education_results.get('recommended_courses', []))}개, "
                f"뉴스 데이터 {len(news_results)}개, "
                f"과거 대화 {len(past_conversations)}개 검색 완료"
            )
            
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
            processing_log.append(f"3단계 처리 시간 (오류): {time_display}")
            state["processing_log"] = processing_log
            
            error_msg = f"데이터 검색 실패: {e}"
            self.logger.error(error_msg)
            state["error_messages"].append(error_msg)
            state["career_cases"] = []
            state["education_courses"] = {"recommended_courses": [], "course_analysis": {}, "learning_path": []}
            state["past_conversations"] = []
            state["news_data"] = []
            
            print(f"❌ [3단계] 데이터 검색 오류: {time_display} (오류: {e})")
        
        return state
    
    def _search_education_courses(self, state: ChatState, intent_analysis: dict) -> dict:
        """
        📚 교육과정 검색 및 추천 로직
        
        사용자의 질문과 프로필을 분석하여 적합한 교육과정을 검색하고,
        개인화된 학습 경로를 제안합니다.
        
        Args:
            state: 현재 워크플로우 상태
            intent_analysis: 의도 분석 결과
            
        Returns:
            dict: 추천 교육과정과 학습 경로 정보
        """
        
        # 사용자 프로필 정보 추출
        user_data = state.get("user_data", {})
        user_question = state.get("user_question", "")
        
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
            # 교육과정 검색 개수 설정 (기본값 15, state에서 지정 가능)
            education_search_count = state.get("education_search_count", 15)
            
            # CareerEnsembleRetrieverAgent의 교육과정 검색 활용
            education_results = self.career_retriever_agent.search_education_courses(
                query=user_question,
                user_profile=user_data,
                intent_analysis=intent_analysis,
                max_results=education_search_count
            )
            
            self.logger.info(f"교육과정 검색 완료: {len(education_results.get('recommended_courses', []))}개 (요청 개수: {education_search_count})")
            print(f"🔍 DEBUG - 교육과정 검색 완료: {len(education_results.get('recommended_courses', []))}개 (요청 개수: {education_search_count})")
            return education_results
            
        except Exception as e:
            self.logger.error(f"교육과정 검색 중 오류: {e}")
            return {"recommended_courses": [], "course_analysis": {}, "learning_path": []}
    
    def _search_past_conversations(self, state: ChatState) -> list:
        """
        💬 사용자별 과거 대화 세션 VectorDB 검색 (핵심 개인화 기능)
        
        이 메서드는 현재 사용자(member_id)의 과거 채팅 세션 대화 내역에서
        현재 질문과 관련된 내용을 의미 기반으로 검색합니다.
        
        Args:
            state: 현재 워크플로우 상태 (user_data와 user_question 포함)
            
        Returns:
            list: 관련 과거 대화 내용 목록
                [
                    {
                        "conversation_id": "채팅세션 ID",
                        "summary": "대화 요약 (AI 생성)",
                        "content_snippet": "대화 내용 일부",
                        "created_at": "세션 생성 시간",
                        "relevance_score": "관련도 점수 (0~1)",
                        "message_count": "해당 세션의 총 메시지 수"
                    }
                ]
                
        🔄 동작 원리:
        1. 현재 사용자의 member_id 추출
        2. SessionVectorDBBuilder를 통한 사용자별 VectorDB 접근
        3. 현재 질문(user_question)을 쿼리로 하여 의미 기반 검색
        4. 관련도 임계값(0.1) 이상의 결과만 필터링
        5. 상위 3개 결과 반환 (너무 많은 결과 방지)
        
        🛡️ 개인정보 보호:
        - 사용자별로 완전히 분리된 VectorDB에서만 검색
        - 다른 사용자의 대화 내역은 절대 접근 불가
        
        📊 활용 목적:
        - 사용자가 이전에 문의했던 유사 질문 파악
        - 과거 상담 내용을 바탕으로 연속성 있는 상담 제공
        - 개인화된 컨텍스트 기반 응답 품질 향상
        """
        try:
            # 📋 1단계: 사용자 정보 추출 (VectorDB 접근을 위한 식별자)
            user_data = state.get("user_data", {})
            member_id = user_data.get("id") or user_data.get("member_id")
            user_question = state.get("user_question", "")
            
            # 🔍 2단계: 필수 정보 검증
            if not member_id or not user_question:
                self.logger.info("member_id 또는 user_question이 없어서 과거 대화 검색을 건너뜁니다")
                return []
            
            # 🗃️ 3단계: 사용자별 VectorDB에서 의미 기반 검색 실행
            from app.utils.session_vectordb_builder import session_vectordb_builder
            
            search_results = session_vectordb_builder.search_user_sessions(
                member_id=str(member_id),    # 사용자별 VectorDB 식별자
                query=user_question,         # 현재 질문을 검색 쿼리로 사용
                k=3                         # 상위 3개 결과만 (과도한 컨텍스트 방지)
            )
            
            # 📊 4단계: 검색 결과 가공 및 품질 필터링
            past_conversations = []
            for result in search_results:
                metadata = result.get("metadata", {})
                content = result.get("content", "")
                relevance_score = result.get("relevance_score", 0)
                
                # ✅ 5단계: 관련도 임계값 필터링 (품질 보장)
                # 관련도가 0.1 이상인 것만 포함 (너무 낮으면 노이즈, 너무 높으면 결과 부족)
                if relevance_score > 0.1:
                    past_conversations.append({
                        "conversation_id": metadata.get("conversation_id"),
                        "summary": metadata.get("summary", ""),
                        "content_snippet": content[:200] + "..." if len(content) > 200 else content,
                        "created_at": metadata.get("created_at"),
                        "relevance_score": relevance_score,
                        "message_count": metadata.get("message_count", 0)
                    })
            
            self.logger.info(f"과거 대화 검색 완료: {len(past_conversations)}개 (member_id: {member_id})")
            return past_conversations
            
        except Exception as e:
            self.logger.error(f"과거 대화 검색 중 오류: {e}")
            return []
    
    def _get_news_results(self, state: ChatState, intent_analysis: dict) -> list:
        """
        📰 뉴스 데이터 검색 (NewsRetrieverAgent 직접 호출)
        
        사용자 질문과 의도 분석 결과를 바탕으로 NewsRetrieverAgent를 통해
        관련 뉴스를 검색합니다. 최신 산업 동향 및 관련 정보를 제공합니다.
        
        🔍 검색 프로세스:
        1. NewsRetrieverAgent 지연 로딩 (필요시에만 초기화)
        2. 사용자 질문 추출
        3. Agent를 통한 의미 기반 뉴스 검색
        4. 상위 3개 결과 반환
        
        Args:
            state (ChatState): 현재 워크플로우 상태 (user_question 포함)
            intent_analysis (dict): 의도 분석 결과 (검색 최적화용)
            
        Returns:
            list: 검색된 뉴스 데이터 리스트
                [
                    {
                        "id": "뉴스 ID",
                        "title": "뉴스 제목",
                        "content": "뉴스 내용",
                        "source": "뉴스 출처",
                        "published_date": "발행일",
                        "category": "카테고리",
                        "domain": "도메인",
                        "relevance_score": "관련도 점수"
                    }
                ]
        """
        try:
            # 📰 1단계: 뉴스 검색 에이전트 지연 로딩 (메모리 효율성)
            if self.news_retriever_agent is None:
                try:
                    from app.graphs.agents.retriever import NewsRetrieverAgent
                    self.news_retriever_agent = NewsRetrieverAgent()
                except ImportError as e:
                    self.logger.warning(f"뉴스 검색 에이전트를 로드할 수 없습니다: {e}")
                    return []
            
            # 🔍 2단계: 검색 쿼리 준비
            user_question = state.get("user_question", "")
            
            # 🎯 3단계: NewsRetrieverAgent를 통한 뉴스 검색
            news_results = self.news_retriever_agent.search_relevant_news(
                query=user_question,
                intent_analysis=intent_analysis,
                n_results=2  # 상위 2개 뉴스만 선택 (컨텍스트 크기 최적화)
            )
            
            self.logger.info(f"뉴스 검색 완료: {len(news_results)}개")
            return news_results
            
        except Exception as e:
            self.logger.error(f"뉴스 검색 중 오류: {e}")
            return []

