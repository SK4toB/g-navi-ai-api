# app/graphs/nodes/career_consultation/learning_roadmap.py
"""
학습 로드맵 설계 노드
AI 기반 맞춤형 학습 계획 생성 (사내 교육과정 추천 포함)
"""

import os
from typing import Dict, Any
from app.graphs.state import ChatState
from app.utils.html_logger import save_career_response_to_html


class LearningRoadmapNode:
    """
    AI 기반 학습 로드맵 설계 노드
    """
    
    def __init__(self, graph_builder):
        self.graph_builder = graph_builder
        # 교육과정 검색 기능 활용
        self.data_retrieval_node = graph_builder.data_retrieval_node
    
    async def _generate_ai_learning_roadmap(self, merged_user_data: dict, selected_path: dict, user_goals: str, education_data: dict) -> Dict[str, Any]:
        """AI 기반 개인 맞춤형 학습 로드맵 생성"""
        try:
            from openai import AsyncOpenAI
            
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return {
                    "message": "학습 로드맵 생성 기능이 현재 이용 불가합니다.",
                    "learning_resources": {}
                }
            
            client = AsyncOpenAI(api_key=api_key)
            
            skills_str = ", ".join(merged_user_data.get('skills', ['정보 없음']))
            path_name = selected_path.get('name', '선택된 경로')
            
            # 교육과정 데이터 추출
            mysuni_courses = education_data.get('mysuni_courses', [])
            college_courses = education_data.get('college_courses', [])
            
            education_context = ""
            if mysuni_courses or college_courses:
                education_context = f"""
사내 교육과정 정보 (최대 15개씩 검색됨):
- mySUNI 과정 ({len(mysuni_courses)}개): {str(mysuni_courses)[:1500] if mysuni_courses else '검색 결과 없음'}
- College 과정 ({len(college_courses)}개): {str(college_courses)[:1500] if college_courses else '검색 결과 없음'}
"""
            
            print(f"🔍 DEBUG - learning_roadmap AI 메서드에 전달된 merged_user_data: {merged_user_data}")
            print(f"🔍 DEBUG - education_context 길이: {len(education_context)}")
            
            prompt = f"""
당신은 G.Navi의 전문 학습 설계사입니다. {merged_user_data.get('name', '고객')}님의 **{path_name}** 경로 달성을 위한 맞춤형 학습 로드맵을 설계해주세요.

**사용자 프로필:**
- 이름: {merged_user_data.get('name', '고객')}
- 경력: {merged_user_data.get('experience', '정보 없음')}
- 보유 기술: {skills_str}
- 도메인: {merged_user_data.get('domain', '정보 없음')}
- 목표 경로: {path_name}
- 사용자 목표: {user_goals[:200]}

{education_context}

**응답 형식 (반드시 마크다운 문법을 사용하여 작성):**

## 학습 로드맵 설계

### 학습 우선순위 및 순서

**핵심 학습 영역 (우선순위 순):**
1. **[첫 번째 영역]** - [간단한 이유와 예상 기간]
2. **[두 번째 영역]** - [간단한 이유와 예상 기간] 
3. **[세 번째 영역]** - [간단한 이유와 예상 기간]

### 사내 교육과정 추천

**mySUNI 추천 과정:**
- [사용자에게 가장 적합한 mySUNI 과정 1-2개 추천 및 이유]

**College 추천 과정:**
- [사용자에게 가장 적합한 College 과정 1-2개 추천 및 이유]

### 학습 실행 계획

**1-3개월 (기초 구축)**
- [구체적인 학습 활동과 목표]

**4-6개월 (실무 적용)**
- [구체적인 학습 활동과 목표]

**작성 지침:**
- 반드시 마크다운 문법 사용 (## 제목, ### 소제목, **굵은글씨**, - 리스트)
- 인사말 없이 바로 "## 학습 로드맵 설계"로 시작
- 전체 200-250단어 내외로 간결하고 실용적으로 작성
- 사내 교육과정을 구체적으로 활용한 추천 제공
- 실무에 바로 적용 가능한 구체적인 내용으로 구성
- 우선순위가 명확한 학습 순서 제시
"""
            
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.6
            )
            
            ai_content = response.choices[0].message.content.strip()
            
            return {
                "message": ai_content,
                "learning_resources": {
                    "mysuni_courses": mysuni_courses[:10] if mysuni_courses else [],
                    "college_courses": college_courses[:10] if college_courses else [],
                    "focus_areas": ["기초 구축", "실무 적용", "전문성 강화"]
                }
            }
            
        except Exception as e:
            print(f"AI 학습 로드맵 생성 중 오류: {e}")
            return {
                "message": "학습 로드맵을 생성하는 중 문제가 발생했습니다. 다시 시도해주세요.",
                "learning_resources": {}
            }
    
    async def create_learning_roadmap_node(self, state: ChatState) -> Dict[str, Any]:
        """
        사용자 맞춤형 학습 로드맵을 설계한다.
        """
        print("📚 학습 로드맵 설계 시작...")
        
        user_response = state.get("user_question", "").lower()
        selected_path = state.get("selected_career_path", {})
        user_data = self.graph_builder.get_user_info_from_session(state)
        collected_info = state.get("collected_user_info", {})
        merged_user_data = {**user_data, **collected_info}
        
        # 디버깅: 데이터 확인
        print(f"🔍 DEBUG - learning_roadmap user_data from session: {user_data}")
        print(f"🔍 DEBUG - learning_roadmap collected_info: {collected_info}")
        print(f"🔍 DEBUG - learning_roadmap merged_user_data: {merged_user_data}")
        
        # 학습 로드맵 요청 여부 확인
        wants_roadmap = "네" in user_response or "yes" in user_response or "학습" in user_response
        
        if wants_roadmap:
            # 사내 교육과정 데이터 검색 (mySUNI, College 각각 15개씩)
            # 교육과정 검색 개수를 15로 설정
            state["education_search_count"] = 15
            state = self.data_retrieval_node.retrieve_additional_data_node(state)
            
            # 교육과정 데이터 추출
            education_data = {
                "mysuni_courses": state.get("education_courses", {}).get("mysuni", []),
                "college_courses": state.get("education_courses", {}).get("college", [])
            }
            
            # 디버깅: 검색된 교육과정 개수 확인
            print(f"🔍 DEBUG - 검색된 mySUNI 과정 개수: {len(education_data['mysuni_courses'])}")
            print(f"🔍 DEBUG - 검색된 College 과정 개수: {len(education_data['college_courses'])}")
            
            # AI 기반 학습 로드맵 생성
            roadmap_result = await self._generate_ai_learning_roadmap(
                merged_user_data, selected_path, user_response, education_data
            )
            
            roadmap_response = {
                "message": roadmap_result["message"],
                "learning_resources": roadmap_result["learning_resources"]
            }
        else:
            # 학습 로드맵 생략 시 간단한 요약
            roadmap_response = {
                "message": f"""## 상담 마무리

**{merged_user_data.get('name', '고객')}님**께서는 학습 로드맵 대신 **실행에 집중**하기로 하셨습니다.

### 즉시 실행 가능한 액션

**이번 주 실행 목표:**
- 관련 업무 기회 탐색 및 상사와 커리어 대화
- 사내 해당 분야 전문가 1명과 커피챗 요청

**다음 단계:**
- **{selected_path.get('name', '선택된 경로')}** 목표를 향한 구체적인 실행 계획 수립

이제 오늘 상담 내용을 종합 정리해드리겠습니다.""",
                "learning_resources": {
                    "focus": "execution_over_learning",
                    "immediate_actions": [
                        "관련 업무 기회 탐색",
                        "사내 전문가와 네트워킹",
                        "프로젝트 참여 기회 찾기"
                    ]
                }
            }
        
        # HTML 로그 저장
        save_career_response_to_html("learning_roadmap", roadmap_response, state.get("session_id", "unknown"))
        
        return {
            **state,
            "consultation_stage": "summary_request",
            "formatted_response": roadmap_response,
            "final_response": roadmap_response,
            "awaiting_user_input": True,
            "next_expected_input": "summary_request",
            "processing_log": state.get("processing_log", []) + ["학습 로드맵 처리 완료"]
        }
