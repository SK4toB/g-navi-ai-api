# app/graphs/nodes/career_consultation/path_deepening.py
"""
선택한 경로에 대한 심화 논의 노드
사용자의 목표와 이유를 분석하여 사내 데이터 기반 액션 플랜 수립
AI 기반 개인 맞춤형 전략 분석 포함
"""

import os
from typing import Dict, Any
from app.graphs.state import ChatState
from app.utils.html_logger import save_career_response_to_html


class PathDeepeningNode:
    """
    경로 심화 논의 노드
    """
    
    def __init__(self, graph_builder):
        self.graph_builder = graph_builder
        # 기존 데이터 검색 노드 재활용
        self.data_retrieval_node = graph_builder.data_retrieval_node
    
    async def _generate_ai_action_plan(self, merged_user_data: dict, selected_path: dict, user_goals: str, retrieved_data: dict) -> str:
        """AI 기반 사내 데이터를 활용한 액션 플랜 및 멘토 추천 생성"""
        try:
            from openai import AsyncOpenAI
            
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return "AI 분석 기능이 현재 이용 불가합니다."
            
            client = AsyncOpenAI(api_key=api_key)
            
            skills_str = ", ".join(merged_user_data.get('skills', ['정보 없음']))
            path_name = selected_path.get('name', '선택된 경로')
            
            # 디버깅: AI 메서드에 전달된 데이터 확인
            print(f"🔍 DEBUG - path_deepening AI 메서드에 전달된 merged_user_data: {merged_user_data}")
            print(f"🔍 DEBUG - path_deepening user_goals: {user_goals}")
            
            # retrieved_data에서 사내 경력 데이터 추출
            career_data = retrieved_data.get('career_data', [])
            career_context = ""
            if career_data:
                # 사내 구성원 데이터를 더 상세히 활용
                career_profiles = []
                for i, profile in enumerate(career_data[:10]):  # 최대 10개만 상세 분석
                    name = profile.get('name', f'구성원{i+1}')
                    experience = profile.get('experience', '정보없음')
                    skills = profile.get('skills', [])
                    domain = profile.get('domain', '정보없음')
                    career_path = profile.get('career_path', '정보없음')
                    
                    profile_info = f"- {name}: {experience}, 기술: {', '.join(skills[:3])}, 도메인: {domain}, 경로: {career_path}"
                    career_profiles.append(profile_info)
                
                career_context = f"""
**사내 구성원 성공 사례 ({len(career_data)}명 분석):**
{chr(10).join(career_profiles)}

**데이터 분석 결과:**
- 총 {len(career_data)}명의 사내 구성원 데이터 분석
- 유사 경로 성공 사례 및 성장 패턴 파악 가능
"""
            else:
                career_context = "사내 구성원 데이터: 현재 분석 가능한 데이터 없음"
            
            prompt = f"""
당신은 G.Navi의 전문 커리어 상담사입니다. 현재 상담이 진행 중이며, 사내 구성원 데이터를 기반으로 실무적인 액션 플랜을 수립해주세요.

**고객 정보:**
- 이름: {merged_user_data.get('name', '고객')}
- 경력: {merged_user_data.get('experience', '정보 없음')}
- 보유 기술: {skills_str}
- 도메인: {merged_user_data.get('domain', '정보 없음')}
- 선택한 경로: {path_name}
- 목표 및 동기: {user_goals[:200]}

**사내 데이터:**
{career_context}

**요청사항:**
1. 사내 경력 데이터를 기반으로 한 장기 액션 플랜 수립
2. **사내 구성원 벤치마킹**: 위의 사내 데이터에서 {path_name} 경로와 유사한 구성원들의 실제 성장 사례를 구체적으로 분석하고 벤치마킹 (이름, 경험, 성장 경로 등을 구체적으로 언급)
3. 데이터 기반 멘토/롤모델 추천 (실제 사내 인물명 또는 유사 프로필 활용)
4. 네트워킹 기회 제안 (사내 커뮤니티, 스터디 그룹 등)
5. 학습 로드맵 설계 필요성에 대한 유도 멘트

**응답 형식 (반드시 마크다운 문법을 사용하여 작성해주세요):**

## 맞춤형 액션 플랜

{merged_user_data.get('name', '고객')}님이 설정하신 목표를 달성하기 위한 구체적인 실행 계획을 제안드립니다.

### 사내 성공 사례 벤치마킹

**유사 성장 경로 분석:**
- [사내 구성원들의 실제 성장 사례를 구체적으로 분석 - 이름, 경험, 성장 과정 포함]
- [선택한 경로와 유사한 패턴을 보인 구성원들의 성공 요인 분석]

### 추천 액션 플랜

**1. 멘토/롤모델**
- [사내 데이터에서 추출한 실제 구성원명을 활용한 멘토 추천]

**2. 네트워킹 기회**
- [사내 커뮤니티 및 스터디 그룹 제안]

**3. 단계별 실행 계획**
- [구체적이고 실행 가능한 단계별 계획]

다음 단계로 **사내 교육과정을 추천**해드릴까요?

**작성 지침:**
- 반드시 마크다운 문법을 사용하여 응답 (## 제목, ### 소제목, **굵은글씨**, - 리스트 등)
- 인사말 없이 바로 "## 맞춤형 액션 플랜" 제목으로 시작
- 상담사처럼 친근하고 전문적인 톤으로 작성
- 250-300단어 내외로 간결하게 작성
- 구체적이고 실행 가능한 조언 위주
- 사내 데이터를 적극 활용한 맞춤형 추천
- **사내 성공 사례 벤치마킹을 필수로 포함**
- 마지막에 학습 로드맵 설계 제안을 자연스럽게 포함
"""
            
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.6
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"AI 액션 플랜 생성 중 오류: {e}")
            return "액션 플랜을 생성하는 중 문제가 발생했습니다. 다시 시도해주세요."
    
    async def process_deepening_node(self, state: ChatState) -> Dict[str, Any]:
        """
        사용자의 목표와 이유를 분석하여 실행 전략을 제시한다.
        """
        print("🎯 경로 심화 논의 시작...")
        
        user_response = state.get("user_question", "")
        selected_path = state.get("selected_career_path", {})
        user_data = self.graph_builder.get_user_info_from_session(state)
        collected_info = state.get("collected_user_info", {})
        merged_user_data = {**user_data, **collected_info}
        
        # 디버깅: 데이터 확인
        print(f"🔍 DEBUG - path_deepening user_data from session: {user_data}")
        print(f"🔍 DEBUG - path_deepening collected_info: {collected_info}")
        print(f"🔍 DEBUG - path_deepening merged_user_data: {merged_user_data}")
        
        # 기존 데이터 검색 노드로 사내 경력 데이터 수집
        # career_positioning에서 이미 검색한 데이터가 있으면 재사용, 없으면 새로 검색
        existing_career_data = state.get("retrieved_career_data", [])
        if existing_career_data:
            print(f"🔍 DEBUG - career_positioning에서 저장된 사내 구성원 데이터 재사용: {len(existing_career_data)}개")
            retrieved_data = {"career_data": existing_career_data}
        else:
            print("🔍 DEBUG - 새로운 사내 구성원 데이터 검색 실행")
            state = self.data_retrieval_node.retrieve_additional_data_node(state)
            retrieved_data = state.get("retrieved_data", {})
        
        # AI 기반 사내 데이터 활용 액션 플랜 생성
        ai_response = await self._generate_ai_action_plan(
            merged_user_data, selected_path, user_response, retrieved_data
        )
        
        # 사용자 응답 컨텍스트 저장
        consultation_context = {
            "user_goals": user_response,
            "selected_path": selected_path,
            "analysis_timestamp": "2025-07-02"
        }
        
        # 응답 구성
        strategy_response = {
            "message": ai_response,
            "action_plan": {
                "context": consultation_context,
                "data_sources": ["career_data", "networking_opportunities"]
            }
        }
        
        # HTML 로그 저장
        save_career_response_to_html("path_deepening", strategy_response, state.get("session_id", "unknown"))
        
        return {
            **state,
            "consultation_stage": "learning_decision",
            "consultation_context": consultation_context,
            "formatted_response": strategy_response,
            "final_response": strategy_response,
            "awaiting_user_input": True,
            "next_expected_input": "learning_roadmap_decision",
            "processing_log": state.get("processing_log", []) + ["실행 전략 수립 완료"]
        }
