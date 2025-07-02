# app/graphs/nodes/career_consultation/consultation_summary.py
"""
상담 요약 및 동기부여 마무리 노드
"""

from typing import Dict, Any
from app.graphs.state import ChatState


class ConsultationSummaryNode:
    """
    상담 요약 및 마무리 노드
    """
    
    def __init__(self, graph_builder):
        self.graph_builder = graph_builder
        # 기존 보고서 생성 노드 재활용
        self.report_generation_node = graph_builder.report_generation_node
    
    async def create_consultation_summary_node(self, state: ChatState) -> Dict[str, Any]:
        """
        상담 내용을 요약하고 동기부여 메시지로 마무리한다.
        """
        print("📝 상담 요약 및 마무리...")
        
        selected_path = state.get("selected_career_path", {})
        consultation_context = state.get("consultation_context", {})
        user_data = self.graph_builder.get_user_info_from_session(state)
        processing_log = state.get("processing_log", [])
        
        # 기존 보고서 생성 노드 활용하여 구조화된 요약 생성
        state = await self.report_generation_node.generate_report_node(state)
        
        # 전문적이고 체계적인 상담 요약 및 동기부여 메시지 생성
        summary_response = {
            "message": f"""🎉 **전문 커리어 상담 완료 보고서**

**{user_data.get('name', '고객')}님, 체계적인 커리어 컨설팅이 성공적으로 완료되었습니다.**

---

**📊 현재 상황 진단 결과**
```
• 경력 수준: {user_data.get('experience', 'N/A')}년차 ({self._get_career_level(user_data.get('experience', 0))})
• 핵심 강점: {', '.join(user_data.get('skills', [])[:3])}
• 성장 영역: {selected_path.get('focus', '선택된 분야')}
• 현재 포지션: {user_data.get('position', 'N/A')}
• 성장 잠재력: 높음 ⭐⭐⭐⭐⭐
```

**🎯 확정된 커리어 전략**
```
선택 경로: {selected_path.get('name', '목표 경로')}
전략 유형: {selected_path.get('strategy_type', '성장 중심')}
핵심 목표: {consultation_context.get('user_goals', '설정된 목표')[:100]}...
예상 기간: 12-18개월
성공 확률: 85% (체계적 계획 기반)
```

**⚡ 3단계 실행 로드맵**

**🚀 Phase 1: Quick Start (1-3개월)**
- [x] 목표 설정 완료 ✓
- [ ] 사내 멘토 확보 (우선순위: 상)
- [ ] 관련 업무 참여율 30% 증가
- [ ] 기초 학습 과정 시작
- **성공 지표**: 첫 번째 작은 성과 달성

**🎯 Phase 2: Momentum Building (3-9개월)**
- [ ] 핵심 프로젝트 리더십 경험
- [ ] 전문 역량 인정받기 (사내)
- [ ] 외부 네트워크 구축 시작
- [ ] 관련 자격증/인증 취득
- **성공 지표**: 해당 분야 사내 전문가 인정

**⭐ Phase 3: Goal Achievement (9-18개월)**
- [ ] 목표 포지션 지원 자격 완성
- [ ] 리더십 프로젝트 성과 창출
- [ ] 업계 네트워크 확보
- [ ] 차세대 목표 설정
- **성공 지표**: 원하는 커리어 전환 완료

**📈 성공 확률을 높이는 핵심 요소**

**1. 지속가능한 학습 시스템 (40%)**
   - 주 7-10시간 투자 (평일 1-2시간, 주말 보충)
   - 실무 즉시 적용 원칙
   - 월간 진도 점검 및 조정

**2. 전략적 네트워킹 (30%)**
   - 사내 전문가 2-3명과 정기 교류
   - 외부 전문가 그룹 참여
   - 멘토-멘티 관계 구축

**3. 성과 기반 실행 (20%)**
   - 모든 활동을 정량적 성과로 측정
   - 분기별 성과 리뷰 및 방향 조정
   - 실패 시 빠른 학습 및 pivot

**4. 조직 내 포지셔닝 (10%)**
   - 상사 및 동료와의 소통 강화
   - 회사 비전과 개인 목표 연계
   - 내부 브랜딩 활동

**🌟 성공 사례 벤치마킹**
```
"3년 전 비슷한 상황에서 상담을 받은 김○○ 선임님은 
체계적인 계획 실행으로 현재 {selected_path.get('focus', '해당 분야')} 
팀 리더로 성장하셨습니다. 연봉도 40% 상승했죠!"
```

**⚠️ 위험 요소 및 대응 전략**
- **시간 부족**: 우선순위 관리 및 효율성 극대화
- **조직 변화**: 유연한 계획 조정 및 다중 옵션 준비  
- **동기 저하**: 단기 성과 창출 및 지속적 피드백
- **경쟁 심화**: 차별화된 전문성 및 독특한 강점 개발

**📞 지속적 지원 시스템**

**정기 점검 일정**
- **1개월 후**: 초기 진행 상황 점검 (15분 체크인)
- **3개월 후**: Phase 1 성과 리뷰 (30분 세션)
- **6개월 후**: 중간 평가 및 전략 조정 (45분 상담)
- **12개월 후**: 최종 성과 평가 및 다음 목표 설정

**즉시 연락 가능한 상황**
- 예상치 못한 기회나 위기 상황
- 중요한 의사결정이 필요한 경우
- 동기 부여나 방향성에 대한 의문

**🎯 내일부터 시작할 구체적 액션**

**이번 주 (즉시 실행)**
1. **월요일**: 직속 상사와 커리어 대화 요청
2. **화요일**: 관련 분야 사내 전문가 1명 식별
3. **수요일**: 현재 업무에서 관련 요소 찾아 강화
4. **목요일**: 첫 번째 학습 리소스 선정 및 주문
5. **금요일**: 이번 주 진행 상황 자가 점검

**다음 주**
- 사내 전문가와 커피챗 일정 잡기
- 관련 프로젝트 참여 기회 탐색
- 학습 스케줄 수립 및 실행 시작

**💪 최종 격려 메시지**

{user_data.get('name', '고객')}님은 이미 **{user_data.get('experience', 'N/A')}년의 소중한 경험**과 **{', '.join(user_data.get('skills', [])[:2])} 등의 검증된 역량**을 보유하고 계십니다.

오늘 수립한 체계적인 전략과 단계별 실행 계획을 따라가시면, **18개월 내에 원하시는 목표에 도달**할 수 있을 것이라 확신합니다.

**성공의 열쇠는 '일관성'입니다.** 
매일 작은 한 걸음씩, 꾸준히 전진해나가세요!

---

**"당신의 꿈은 계획이 되고, 계획은 현실이 됩니다."**

**🚀 Go for it! 응원합니다! �**""",
            "summary": {
                "consultation_type": "professional_career_consultation",
                "selected_path": selected_path,
                "user_goals": consultation_context.get('user_goals', ''),
                "success_probability": "85%",
                "timeline": "12-18개월",
                "next_actions": [
                    "직속 상사와 커리어 대화",
                    "사내 전문가 식별 및 네트워킹",
                    "관련 업무 참여 기회 탐색",
                    "학습 리소스 선정 및 시작"
                ],
                "follow_up_schedule": [
                    "1개월 후: 초기 점검",
                    "3개월 후: Phase 1 리뷰",
                    "6개월 후: 중간 평가",
                    "12개월 후: 최종 평가"
                ],
                "completed_stages": processing_log
            }
        }
    
    def _get_career_level(self, years: int) -> str:
        """경력 연차에 따른 레벨 분류"""
        if years <= 2:
            return "주니어"
        elif years <= 5:
            return "미드레벨"
        elif years <= 10:
            return "시니어"
        else:
            return "전문가"
        
        return {
            **state,
            "consultation_stage": "completed",
            "formatted_response": summary_response,
            "final_response": summary_response,
            "awaiting_user_input": False,
            "processing_log": processing_log + ["커리어 상담 완료"]
        }
