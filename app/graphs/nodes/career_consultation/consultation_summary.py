# app/graphs/nodes/career_consultation/consultation_summary.py
"""
상담 요약 및 동기부여 마무리 노드
AI 기반 개인화된 동기부여 메시지 생성
"""

import os
from typing import Dict, Any
from app.graphs.state import ChatState
from app.utils.html_logger import save_career_response_to_html


class ConsultationSummaryNode:
    """
    상담 요약 및 마무리 노드
    """
    
    def __init__(self, graph_builder):
        self.graph_builder = graph_builder
    
    async def _generate_consultation_summary(self, merged_user_data: dict, selected_path: dict, consultation_context: dict, processing_log: list, state: ChatState) -> str:
        """AI 기반 상담 요약 및 격려 메시지 생성 (맞춤형 전략, 학습 로드맵 포함)"""
        try:
            from openai import AsyncOpenAI
            
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return f"""## 상담 요약

{merged_user_data.get('name', '고객')}님의 커리어 상담이 완료되었습니다.

**선택된 경로**: {selected_path.get('name', '목표 경로')}
**목표**: {consultation_context.get('user_goals', '설정된 목표')[:200]}

체계적인 계획을 바탕으로 꾸준히 실행해나가시면 반드시 목표를 달성하실 수 있습니다. 응원합니다!"""
            
            client = AsyncOpenAI(api_key=api_key)
            
            skills_str = ", ".join(merged_user_data.get('skills', ['정보 없음']))
            path_name = selected_path.get('name', '선택된 경로')
            user_goals = consultation_context.get('user_goals', '커리어 성장 목표')
            
            # 상담 단계별 정보 수집
            path_selection_info = state.get("path_selection_info", {})
            learning_resources = state.get("learning_resources", {})
            action_plan_info = state.get("action_plan", {})
            
            # 학습 로드맵 정보 추출
            learning_roadmap_provided = "learning_roadmap" in " ".join(processing_log).lower()
            learning_courses_info = ""
            if learning_resources:
                mysuni_courses = learning_resources.get("mysuni_courses", [])
                college_courses = learning_resources.get("college_courses", [])
                if mysuni_courses or college_courses:
                    learning_courses_info = f"mySUNI {len(mysuni_courses)}개 과정, College {len(college_courses)}개 과정 추천"
            
            # 맞춤형 전략 정보 추출
            strategy_provided = "path_deepening" in " ".join(processing_log).lower() or "action_plan" in str(action_plan_info).lower()
            mentor_recommendations = "멘토" in str(action_plan_info).lower() or "선배" in str(action_plan_info).lower()
            
            # 디버깅: AI 메서드에 전달된 데이터 확인
            print(f"🔍 DEBUG - consultation_summary AI 메서드에 전달된 데이터")
            print(f"   - name: {merged_user_data.get('name')}")
            print(f"   - path_name: {path_name}")
            print(f"   - user_goals: {user_goals[:100]}...")
            print(f"   - learning_roadmap_provided: {learning_roadmap_provided}")
            print(f"   - strategy_provided: {strategy_provided}")
            print(f"   - processing_log: {processing_log}")
            
            prompt = f"""
당신은 G.Navi의 전문 커리어 상담사입니다. {merged_user_data.get('name', '고객')}님과의 종합적인 커리어 상담이 완료되었습니다. 

**상담 대상자 정보:**
- 이름: {merged_user_data.get('name', '고객')}
- 경력: {merged_user_data.get('experience', '정보 없음')}
- 보유 기술: {skills_str}
- 도메인: {merged_user_data.get('domain', '정보 없음')}
- 선택한 경로: {path_name}
- 설정한 목표: {user_goals}

**제공된 상담 서비스:**
- 커리어 포지셔닝 분석: ✅ 완료
- 경로 선택 및 심화 논의: ✅ 완료
- 맞춤형 전략 수립: {'✅ 완료 (사내 멘토 추천 포함)' if strategy_provided else '기본 가이드 제공'}
- 학습 로드맵 설계: {'✅ 완료 (' + learning_courses_info + ')' if learning_roadmap_provided else '요청 시 제공 가능'}

**상담 진행 과정:**
{', '.join(processing_log)}

**요청사항:**
종합적인 상담 내용을 요약하고 개인 맞춤형 격려 메시지를 작성해주세요.

**응답 형식 (반드시 마크다운 문법을 사용하여 작성해주세요):**

## 상담 요약 완료

### 📋 상담 핵심 내용

**선택된 성장 경로**: {path_name}

**핵심 결정사항**:
- [커리어 포지셔닝 분석 결과 주요 내용]
- [경로 선택의 주요 근거와 이유]
- [향후 성장을 위한 핵심 전략 방향]

**맞춤형 성장 전략**:
{'- [사내 데이터 기반 구체적인 성장 전략 요약]' if strategy_provided else '- [기본 성장 가이드라인 제시]'}
{'- [추천된 사내 멘토 및 네트워킹 방향]' if mentor_recommendations else '- [멘토링 기회 탐색 권장]'}
- [단계별 실행 계획 및 우선순위]

**학습 로드맵**:
{f'- [제공된 학습 과정: {learning_courses_info}]' if learning_roadmap_provided else '- [향후 필요시 맞춤형 학습 로드맵 제공 가능]'}
{f'- [우선순위 기반 학습 순서 및 일정]' if learning_roadmap_provided else '- [기본 학습 방향성 가이드 제공]'}
- [실무 적용 및 성과 창출 방안]

### 💪 {merged_user_data.get('name', '고객')}님을 위한 격려 메시지

[{merged_user_data.get('name', '고객')}님의 현재 상황과 목표를 고려한 개인 맞춤형 격려와 응원 메시지. 구체적인 강점과 성장 가능성을 언급하며 동기부여하는 내용]

**다음 단계**: [구체적인 첫 번째 실행 단계 제시]

---

**🌟 G.Navi와 함께한 커리어 상담이 {merged_user_data.get('name', '고객')}님의 성공적인 성장 여정의 시작점이 되기를 바랍니다!**

**작성 지침:**
- 반드시 마크다운 문법 사용 (## 제목, ### 소제목, **굵은글씨** 등)
- 인사말 없이 바로 "## 상담 요약 완료"로 시작
- 전체 250-300단어 내외로 구체적이고 포괄적으로 작성
- 제공된 모든 상담 서비스 (포지셔닝, 전략, 학습 로드맵)를 균형있게 요약
- 상담의 핵심 가치와 실행 가능성을 강조
- 따뜻하고 전문적인 격려 메시지로 마무리
- 구체적이고 실행 가능한 다음 단계 제시
"""
            
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.4
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"AI 상담 요약 생성 중 오류: {e}")
            return f"""## 상담 요약

**{merged_user_data.get('name', '고객')}님**의 종합적인 커리어 상담이 성공적으로 완료되었습니다.

### 📋 상담 핵심 내용

**선택된 성장 경로**: {selected_path.get('name', '목표 경로')}
**핵심 결정사항**: 개인 강점 분석 및 성장 방향 설정
**맞춤형 전략**: 사내 데이터 기반 실행 계획 수립
**학습 로드맵**: 단계별 학습 과정 및 우선순위 제시

### 💪 격려 메시지

**{merged_user_data.get('name', '고객')}님**의 명확한 목표 설정과 체계적인 계획을 바탕으로, 꾸준히 실행해나가시면 반드시 원하는 성과를 달성하실 수 있습니다. 

**다음 단계**: {consultation_context.get('user_goals', '설정된 계획')[:100]}을 우선적으로 실행해보세요.

---

**G.Navi와 함께한 커리어 상담이 성공적인 성장 여정의 시작점이 되기를 바랍니다!**"""
    
    async def create_consultation_summary_node(self, state: ChatState) -> Dict[str, Any]:
        """
        상담 내용을 요약하고 격려 메시지로 마무리한다.
        """
        print("📝 상담 요약 및 마무리...")
        
        selected_path = state.get("selected_career_path", {})
        consultation_context = state.get("consultation_context", {})
        user_data = self.graph_builder.get_user_info_from_session(state)
        collected_info = state.get("collected_user_info", {})
        merged_user_data = {**user_data, **collected_info}
        processing_log = state.get("processing_log", [])
        
        # 디버깅: 데이터 확인
        print(f"🔍 DEBUG - consultation_summary user_data from session: {user_data}")
        print(f"🔍 DEBUG - consultation_summary collected_info: {collected_info}")
        print(f"🔍 DEBUG - consultation_summary merged_user_data: {merged_user_data}")
        
        # AI 기반 상담 요약 생성 (state 정보 포함)
        summary_message = await self._generate_consultation_summary(
            merged_user_data, selected_path, consultation_context, processing_log, state
        )
        
        # 간결한 요약 응답 구성
        summary_response = {
            "message": summary_message,
            "summary": {
                "consultation_type": "career_consultation",
                "selected_path": selected_path.get('name', '선택된 경로'),
                "user_goals": consultation_context.get('user_goals', '설정된 목표'),
                "completed_stages": processing_log
            }
        }
    
        # HTML 로그 저장
        save_career_response_to_html("consultation_summary", summary_response, state.get("session_id", "unknown"))
    
        return {
            **state,
            "consultation_stage": "completed",
            "formatted_response": summary_response,
            "final_response": summary_response,
            "awaiting_user_input": False,
            "processing_log": processing_log + ["커리어 상담 완료"]
        }
