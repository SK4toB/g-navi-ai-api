# app/graphs/nodes/career_consultation/path_deepening.py
"""
선택한 경로에 대한 심화 논의 노드
사용자의 목표와 이유를 분석하여**🔍 현재 상황 분석 (Gap Analysis)**
- **보유 역량**: {', '.join(user_data.get('skills', [])[:3])} 등
- **경력 수준**: {user_data.get('experience', 'N/A')}년차
- **부족 역량**: [응답 기반 분석 필요]
- **성장 가능성**: 높음 (기존 경험 활용 가능)

{("**🤖 AI 맞춤형 전략 분석**" + chr(10) + ai_strategy + chr(10)) if ai_strategy else ""}

**🗺️ 체계적 실행 로드맵** 수립
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
    
    async def _generate_personalized_strategy(self, user_data: dict, selected_path: dict, user_goals: str) -> str:
        """AI 기반 개인 맞춤형 실행 전략 생성"""
        try:
            from openai import AsyncOpenAI
            
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return ""
            
            client = AsyncOpenAI(api_key=api_key)
            
            skills_str = ", ".join(user_data.get('skills', ['현재 스킬']))
            path_name = selected_path.get('name', '선택된 경로')
            
            prompt = f"""
다음 직장인을 위한 맞춤형 커리어 전략을 수립해주세요:

- 경력: {user_data.get('experience', '정보 없음')}
- 현재 스킬: {skills_str}
- 목표 경로: {path_name}
- 목표 및 동기: {user_goals[:300]}
- 도메인: {user_data.get('domain', '전문 분야')}

다음을 포함하여 200-250단어로 작성해주세요:
1. 현재 상황에서 이 경로로 가기 위한 구체적 갭 분석
2. 3-6개월 내 달성 가능한 현실적 첫 단계
3. 가장 중요한 스킬 개발 우선순위 3가지
4. 예상되는 어려움과 해결 방안

실무적이고 구체적인 조언으로 작성해주세요.
"""
            
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=3000,
                temperature=0.6
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"개인화 전략 생성 중 오류: {e}")
            return ""
    
    async def process_deepening_node(self, state: ChatState) -> Dict[str, Any]:
        """
        사용자의 목표와 이유를 분석하여 실행 전략을 제시한다.
        """
        print("🎯 경로 심화 논의 시작...")
        
        user_response = state.get("user_question", "")
        selected_path = state.get("selected_career_path", {})
        user_data = self.graph_builder.get_user_info_from_session(state)
        
        # 기존 데이터 검색 노드로 관련 정보 수집
        state = self.data_retrieval_node.retrieve_additional_data_node(state)
        
        # AI 기반 개인 맞춤형 전략 생성
        ai_strategy = await self._generate_personalized_strategy(
            user_data, selected_path, user_response
        )
        
        # 사용자 응답 컨텍스트 저장
        consultation_context = {
            "user_goals": user_response,
            "selected_path": selected_path,
            "analysis_timestamp": "2025-07-02"
        }
        
        # 전문적인 실행 전략 및 분석 생성
        strategy_response = {
            "message": f"""🎯 **전문적 커리어 분석 및 실행 전략**

{user_data.get('name', '고객')}님의 목표와 현재 상황을 종합 분석한 결과를 바탕으로, **{selected_path.get('name', '선택하신 경로')}** 달성을 위한 체계적인 전략을 제시합니다.

**� 현재 상황 분석 (Gap Analysis)**
- **보유 역량**: {', '.join(user_data.get('skills', [])[:3])} 등
- **경력 수준**: {user_data.get('experience', 'N/A')}년차
- **부족 역량**: [응답 기반 분석 필요]
- **성장 가능성**: 높음 (기존 경험 활용 가능)

**🗺️ 체계적 실행 로드맵**

**Phase 1: 기반 구축 (1-3개월)**
- **역량 진단**: 현재 수준 객관적 평가
- **Quick Win 프로젝트**: 관련 업무에서 작은 성과 창출
- **네트워크 구축**: 해당 분야 사내 전문가 1-2명과 관계 형성
- **학습 환경 구축**: 필요 도구/리소스 확보

**Phase 2: 역량 강화 (3-9개월)**
- **핵심 스킬 개발**: {selected_path.get('focus', '관련 분야')} 전문성 강화
- **실무 적용**: 현재 업무에 새로운 방법론 적용
- **멘토링 시작**: 선배 전문가와 정기 멘토링 세션
- **외부 활동**: 관련 커뮤니티 참여 및 네트워킹

**Phase 3: 성과 창출 (9-18개월)**
- **프로젝트 리드**: 관련 분야 프로젝트 주도
- **지식 공유**: 사내 세미나/교육 진행
- **성과 측정**: 정량적 성과 지표 수집
- **경력 준비**: 목표 포지션 지원 준비

**🎯 핵심 성공 요인 (Critical Success Factors)**
1. **지속적 학습**: 주 5-10시간 투자
2. **실무 적용**: 배운 내용 즉시 업무 적용
3. **네트워킹**: 월 1-2회 전문가 네트워킹
4. **성과 기록**: 모든 성과 문서화 및 정량화

**⚠️ 주의사항 및 리스크 관리**
- **시간 관리**: 현재 업무 품질 유지하며 성장
- **번아웃 방지**: 단계적 목표 설정으로 지속가능성 확보
- **조직 내 정치**: 상사 및 동료와의 커뮤니케이션 강화

**📈 성공 지표 (KPI)**
- 3개월: 관련 업무 참여율 30% 증가
- 6개월: 해당 분야 사내 전문가 인정
- 12개월: 관련 프로젝트 성과 창출
- 18개월: 목표 포지션 지원 자격 획득

**다음 단계로 맞춤형 학습 계획을 수립해드릴까요?**
구체적인 교육과정, 도서, 프로젝트 등을 포함한 상세 학습 로드맵이 필요하시면 "네, 학습 계획도 받고 싶습니다"라고 답변해주세요.""",
            "action_plan": {
                "phase1": "기반 구축 (1-3개월)",
                "phase2": "역량 강화 (3-9개월)", 
                "phase3": "성과 창출 (9-18개월)",
                "success_factors": ["지속적 학습", "실무 적용", "네트워킹", "성과 기록"]
            }
        }
        
        # HTML 로그 저장
        save_career_response_to_html("path_deepening", strategy_response, state.get("session_id", "unknown"))
        
        return {
            **state,
            "consultation_stage": "learning_decision",
            "consultation_context": consultation_context,
            "formatted_response": strategy_response,
            "final_response": strategy_response,  # final_response 추가
            "awaiting_user_input": True,
            "next_expected_input": "learning_roadmap_decision",
            "processing_log": state.get("processing_log", []) + ["실행 전략 수립 완료"]
        }
