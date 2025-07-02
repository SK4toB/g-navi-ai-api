# app/graphs/nodes/career_consultation/learning_roadmap.py
"""
학습 로드맵 설계 노드
사내 교육과정 및 외부 리소스 추천
"""

from typing import Dict, Any
from app.graphs.state import ChatState


class LearningRoadmapNode:
    """
    학습 로드맵 설계 노드
    """
    
    def __init__(self, graph_builder):
        self.graph_builder = graph_builder
        # 기존 교육과정 검색 기능 재활용
        self.data_retrieval_node = graph_builder.data_retrieval_node
    
    async def create_learning_roadmap_node(self, state: ChatState) -> Dict[str, Any]:
        """
        사용자 맞춤형 학습 로드맵을 설계한다.
        """
        print("📚 학습 로드맵 설계 시작...")
        
        user_response = state.get("user_question", "").lower()
        selected_path = state.get("selected_career_path", {})
        user_data = self.graph_builder.get_user_info_from_session(state)
        
        # 학습 로드맵 요청 여부 확인
        wants_roadmap = "네" in user_response or "yes" in user_response or "학습" in user_response
        
        if wants_roadmap:
            # 기존 교육과정 데이터 검색 노드 활용
            state = await self.data_retrieval_node.retrieve_additional_data_node(state)
            
            roadmap_response = {
                "message": f"""📚 **전문가 수준 학습 로드맵 설계**

{user_data.get('name', '고객')}님의 **{selected_path.get('name', '목표 경로')}** 달성을 위한 체계적이고 실무 중심의 학습 계획을 제시합니다.

**🎯 학습 목표 및 원칙**
- **실무 적용성**: 모든 학습 내용을 현재 업무에 즉시 적용
- **단계적 발전**: 기초 → 심화 → 전문가 수준으로 체계적 진행
- **성과 측정**: 각 단계별 명확한 평가 지표 설정

**🏢 사내 교육 리소스 활용 전략**

**mySUNI 핵심 과정 (우선순위순)**
1. **{selected_path.get('focus', '관련 분야')} 기초 과정** (1개월차)
   - 기본 개념 정립 및 전체 그림 이해
   - 사내 성공 사례 학습
2. **프로젝트 관리 과정** (2개월차)
   - 실무 프로젝트 진행 시 필수 역량
   - PMP 기초 지식 습득
3. **리더십 및 커뮤니케이션** (3개월차)
   - 팀 협업 및 이해관계자 관리
   - 프레젠테이션 스킬 강화

**College 전문 과정**
- **심화 기술 과정**: {selected_path.get('name', '해당 분야')} 고급 기법
- **비즈니스 연계 과정**: 기술을 비즈니스 가치로 전환
- **트렌드 분석 과정**: 최신 기술 동향 및 미래 전망

**📖 체계적 자기주도학습 계획**

**Phase 1: 기초 역량 구축 (1-3개월)**
- **도서**: 해당 분야 바이블 3권 정독
  - 기본서 1권 → 실무서 1권 → 심화서 1권
- **온라인 강의**: Coursera/Udemy 기초 과정 수강
- **실습**: 개인 프로젝트 1개 완료

**Phase 2: 실무 적용 및 심화 (3-9개월)**
- **온라인 플랫폼**:
  - **Coursera**: 세계적 대학 전문 과정 (월 1개 완료)
  - **LinkedIn Learning**: 실무 중심 스킬 강화
  - **Udemy**: 특정 도구/기술 마스터리
- **커뮤니티 활동**: 관련 분야 전문가 그룹 가입
- **멘토링**: 사내 전문가와 월 2회 정기 세션

**Phase 3: 전문가 수준 도달 (9-18개월)**
- **고급 자격증**: 해당 분야 공인 자격증 취득
- **컨퍼런스 참여**: 연 2-3회 전문 컨퍼런스 참석
- **지식 공유**: 사내 세미나 발표 및 기술 블로그 운영

**🚀 사내 실무 프로젝트 연계 전략**

**참여 가능한 프로젝트 유형**
1. **Cross-functional 프로젝트**: 다양한 팀과 협업 경험
2. **혁신 프로젝트**: 새로운 기술/방법론 도입 기회
3. **멘토링 프로그램**: 후배 교육을 통한 전문성 검증

**프로젝트 참여 시 학습 포인트**
- 학습한 이론을 실제 업무에 적용
- 프로젝트 진행 과정을 체계적으로 문서화
- 성과를 정량적으로 측정하고 기록

**📅 월별 상세 실행 계획**

**1-3개월: 기반 다지기**
- 주 10시간 학습 (평일 2시간, 주말 추가)
- 사내 과정 1개 + 온라인 기초 과정 1개
- 동료/선배와 스터디 그룹 구성

**4-6개월: 실무 적용**
- 주 8시간 학습 + 실무 프로젝트 참여
- 학습 내용을 현재 업무에 시범 적용
- 첫 번째 성과물 완성

**7-12개월: 전문성 구축**
- 주 6시간 학습 + 전문 프로젝트 리드
- 외부 전문가와 네트워킹 시작
- 사내에서 해당 분야 인정받기

**📊 학습 성과 측정 지표**
- **지식 습득**: 월별 학습 완료율 90% 이상
- **실무 적용**: 분기별 적용 사례 3개 이상
- **네트워킹**: 반기별 전문가 연결 5명 이상
- **성과 창출**: 연간 관련 프로젝트 성과 1개 이상

**💡 학습 효율성 극대화 팁**
1. **시간 관리**: 매일 같은 시간에 학습하여 습관화
2. **기록 관리**: 학습 일지 작성 및 주간 회고
3. **실무 연계**: 배운 즉시 업무에 적용해보기
4. **동기 유지**: 월별 작은 목표 달성으로 성취감 확보

**이제 오늘 상담의 핵심 내용을 종합 정리해드리겠습니다.** 
"네, 최종 정리해주세요"라고 답변해주시면, 액션 플랜과 함께 전문적인 상담 요약을 제공해드리겠습니다.""",
                "learning_resources": {
                    "internal": {
                        "mySUNI": ["기초 과정", "프로젝트 관리", "리더십"],
                        "College": ["심화 기술", "비즈니스 연계", "트렌드 분석"]
                    },
                    "external": {
                        "coursera": "세계적 대학 전문 과정",
                        "linkedin_learning": "실무 중심 스킬",
                        "udemy": "특정 도구/기술 마스터리"
                    },
                    "projects": ["Cross-functional", "Innovation", "Mentoring"],
                    "timeline": {
                        "phase1": "기초 역량 구축 (1-3개월)",
                        "phase2": "실무 적용 및 심화 (3-9개월)",
                        "phase3": "전문가 수준 도달 (9-18개월)"
                    }
                }
            }
        else:
            roadmap_response = {
                "message": f"""✅ **학습 계획 생략, 실행 전략 중심으로 마무리**

{user_data.get('name', '고객')}님께서는 별도의 상세 학습 로드맵보다는 **실행 전략에 집중**하시겠다고 하셨습니다.

**🎯 현재까지 확정된 핵심 요소들:**
- ✅ **목표 경로**: {selected_path.get('name', '선택된 경로')}
- ✅ **실행 전략**: 단계별 체계적 접근법 수립 완료
- ✅ **성공 요인**: 핵심 포인트 및 주의사항 정리 완료

**💼 즉시 실행 가능한 액션 아이템:**
1. **이번 주**: 관련 업무 기회 탐색 및 상사와 커리어 대화
2. **다음 주**: 사내 해당 분야 전문가 1명과 커피챗 요청
3. **이번 달**: 관련 업무에 참여할 수 있는 프로젝트 1개 찾기

**이제 오늘 상담 내용을 체계적으로 정리하여 실행 가능한 형태로 요약해드리겠습니다.**
"네, 최종 정리해주세요"라고 답변해주시면 완벽한 상담 요약을 제공해드리겠습니다.""",
                "learning_resources": {
                    "focus": "execution_over_learning",
                    "immediate_actions": [
                        "관련 업무 기회 탐색",
                        "사내 전문가와 네트워킹",
                        "프로젝트 참여 기회 찾기"
                    ]
                }
            }
        
        return {
            **state,
            "consultation_stage": "summary_request",
            "formatted_response": roadmap_response,
            "awaiting_user_input": True,
            "next_expected_input": "summary_request",
            "processing_log": state.get("processing_log", []) + ["학습 로드맵 처리 완료"]
        }
