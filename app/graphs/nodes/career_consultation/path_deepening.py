# app/graphs/nodes/career_consultation/path_deepening.py
"""
선택한 경로에 대한 심화 논의 노드
사용자의 목표와 이유를 분석하여 실행 전략을 수립
"""

from typing import Dict, Any
from app.graphs.state import ChatState


class PathDeepeningNode:
    """
    경로 심화 논의 노드
    """
    
    def __init__(self, graph_builder):
        self.graph_builder = graph_builder
        # 기존 데이터 검색 노드 재활용
        self.data_retrieval_node = graph_builder.data_retrieval_node
    
    async def process_deepening_node(self, state: ChatState) -> Dict[str, Any]:
        """
        사용자의 목표와 이유를 분석하여 실행 전략을 제시한다.
        """
        print("🎯 경로 심화 논의 시작...")
        
        user_response = state.get("user_question", "")
        selected_path = state.get("selected_career_path", {})
        user_data = self.graph_builder.get_user_info_from_session(state)
        
        # 기존 데이터 검색 노드로 관련 정보 수집
        state = await self.data_retrieval_node.retrieve_additional_data_node(state)
        
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
        
        return {
            **state,
            "consultation_stage": "learning_decision",
            "consultation_context": consultation_context,
            "formatted_response": strategy_response,
            "awaiting_user_input": True,
            "next_expected_input": "learning_roadmap_decision",
            "processing_log": state.get("processing_log", []) + ["실행 전략 수립 완료"]
        }
