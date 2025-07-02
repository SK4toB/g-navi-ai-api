# app/graphs/nodes/career_consultation/career_positioning.py
"""
커리어 포지셔닝 및 시장 분석 노드
기존의 intent_analysis + data_retrieval + response_formatting 노드를 재활용
"""

from typing import Dict, Any
from app.graphs.state import ChatState


class CareerPositioningNode:
    """
    커리어 포지셔닝 노드 - 기존 노드들을 재활용하여 포지셔닝 분석 수행
    """
    
    def __init__(self, graph_builder):
        self.graph_builder = graph_builder
        # 기존 노드들 재활용
        self.intent_analysis_node = graph_builder.intent_analysis_node
        self.data_retrieval_node = graph_builder.data_retrieval_node
        self.response_formatting_node = graph_builder.response_formatting_node
    
    async def career_positioning_node(self, state: ChatState) -> Dict[str, Any]:
        """
        현재 데이터를 기반으로 포지셔닝 및 시장 분석을 수행하고
        사용자 맞춤형 경로 2~3가지를 제시한다.
        """
        print("🎯 커리어 포지셔닝 분석 시작...")
        
        # 1. 기존 의도 분석 노드 활용
        state = await self.intent_analysis_node.analyze_intent_node(state)
        
        # 2. 기존 데이터 검색 노드 활용
        state = await self.data_retrieval_node.retrieve_additional_data_node(state)
        
        # 3. 사용자 정보 병합 (기존 정보 + 수집된 정보)
        user_data = self.graph_builder.get_user_info_from_session(state)
        collected_info = state.get("collected_user_info", {})
        merged_user_data = {**user_data, **collected_info}
        
        # 4. 커리어 상담 전용 응답 포맷팅
        # 포지셔닝 분석 응답 생성
        positioning_response = {
            "message": f"""👋 **안녕하세요, {merged_user_data.get('name', '고객')}님!**

저는 G.Navi 커리어 전문 상담사입니다. 귀하의 프로필을 종합적으로 분석해드렸습니다.

---

## 📊 **현재 상황 진단**

**• 경력 수준**: {merged_user_data.get('experience', 'N/A')} ➜ **{self._get_experience_level(merged_user_data.get('experience', ''))}**
**• 핵심 역량**: {', '.join(merged_user_data.get('skills', [])[:3])} ➜ **{self._analyze_skill_strength(merged_user_data.get('skills', []))}**
**• 도메인 전문성**: {merged_user_data.get('domain', 'N/A')} ➜ **{self._get_domain_outlook(merged_user_data.get('domain', ''))}**

## 🎯 **시장 내 포지셔닝 평가**

귀하는 현재 **{self._get_career_stage(merged_user_data)}**에 위치하고 계시며, 
**{self._get_strength_summary(merged_user_data)}**가 가장 큰 강점입니다.

---

## 🚀 **맞춤형 성장 경로 제안**

데이터 분석 결과, 다음 3가지 경로가 가장 적합합니다:

### **A. 기술 전문가 경로** (Tech Leadership)
```
• 목표: 시니어/리드 개발자 → 테크리더
• 핵심 가치: 기술 깊이 + 아키텍처 설계 역량
• 예상 기간: 2-3년
• 성공 확률: ⭐⭐⭐⭐⭐
```

### **B. 팀 관리자 경로** (People Management)  
```
• 목표: 팀장 → 부서장 → 임원
• 핵심 가치: 리더십 + 비즈니스 이해
• 예상 기간: 3-5년  
• 성공 확률: ⭐⭐⭐⭐
```

### **C. 도메인 전문가 경로** (Business Expert)
```
• 목표: 도메인 스페셜리스트 → 컨설턴트
• 핵심 가치: 업계 전문성 + 문제해결 역량
• 예상 기간: 2-4년
• 성공 확률: ⭐⭐⭐⭐
```

---

**💡 어떤 경로가 가장 매력적으로 느껴지시나요?**
**A, B, C 중 하나를 선택해주시면, 해당 경로에 대한 구체적인 로드맵을 함께 설계해보겠습니다.**""",
            "career_paths": [
                {
                    "id": "A",
                    "name": "기술 전문가 경로 (Tech Lead)",
                    "description": "기술스택 심화 및 기술 리더십",
                    "focus": "technical_leadership"
                },
                {
                    "id": "B", 
                    "name": "팀 관리자 경로 (Team Manager)",
                    "description": "팀 리딩 및 관리직 성장",
                    "focus": "people_management"
                },
                {
                    "id": "C",
                    "name": "도메인 전문가 경로 (Domain Expert)", 
                    "description": "도메인 지식 확장 및 비즈니스 전문성",
                    "focus": "domain_expertise"
                }
            ]
        }
        
        return {
            **state,
            "consultation_stage": "path_selection",
            "career_paths_suggested": positioning_response["career_paths"],
            "formatted_response": positioning_response,
            "awaiting_user_input": True,
            "next_expected_input": "career_path_choice",
            "collected_user_info": collected_info,  # 수집된 정보 유지
            "processing_log": state.get("processing_log", []) + ["커리어 포지셔닝 분석 완료"]
        }
    
    def _get_experience_level(self, experience: str) -> str:
        """경력 수준을 분석한다"""
        if not experience or experience == "신입":
            return "신입급 (성장 잠재력 높음)"
        elif "1" in experience or "2" in experience:
            return "주니어급 (기초 역량 보유)"
        elif "3" in experience or "4" in experience or "5" in experience:
            return "미들급 (핵심 역량 보유)"
        else:
            return "시니어급 (전문성 확립)"
    
    def _analyze_skill_strength(self, skills: list) -> str:
        """기술스택 강점을 분석한다"""
        if not skills:
            return "역량 파악 필요"
        
        skill_count = len(skills)
        if skill_count >= 5:
            return "다양한 기술스택 보유 (풀스택 역량)"
        elif skill_count >= 3:
            return "균형잡힌 기술스택 (전문성 집중 가능)"
        else:
            return "핵심 기술 집중 (전문성 심화 필요)"
    
    def _get_domain_outlook(self, domain: str) -> str:
        """도메인 전망을 분석한다"""
        growth_domains = ["핀테크", "이커머스", "AI", "블록체인", "메타버스", "헬스케어"]
        stable_domains = ["금융", "제조", "공공", "교육"]
        
        if any(d in domain for d in growth_domains):
            return "고성장 분야 (시장 확장성 우수)"
        elif any(d in domain for d in stable_domains):
            return "안정적 분야 (지속적 수요 보장)"
        else:
            return "전문 분야 (특화 역량 중요)"
    
    def _get_career_stage(self, user_data: dict) -> str:
        """현재 커리어 단계를 분석한다"""
        experience = user_data.get('experience', '')
        if "신입" in experience or "1" in experience:
            return "커리어 탐색기"
        elif "2" in experience or "3" in experience:
            return "전문성 구축기"
        elif "4" in experience or "5" in experience or "6" in experience:
            return "리더십 준비기"
        else:
            return "전문가/리더 진입기"
    
    def _get_strength_summary(self, user_data: dict) -> str:
        """핵심 강점을 요약한다"""
        skills = user_data.get('skills', [])
        domain = user_data.get('domain', '')
        
        if len(skills) >= 4:
            return f"{domain} 분야의 다양한 기술 역량"
        elif len(skills) >= 2:
            return f"{domain} 분야의 핵심 기술 전문성"
        else:
            return f"{domain} 분야의 도메인 이해도"
