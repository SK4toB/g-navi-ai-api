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
        # Agent를 직접 사용
        from app.graphs.agents.retriever import CareerEnsembleRetrieverAgent, NewsRetrieverAgent
        self.retriever_agent = CareerEnsembleRetrieverAgent()
        self.news_agent = NewsRetrieverAgent()  # 뉴스 검색 전용 에이전트 추가
    
    async def _generate_ai_action_plan(self, merged_user_data: dict, selected_path: dict, user_goals: str, retrieved_data: dict, path_selection_context: dict = None) -> str:
        """AI 기반 사내 데이터를 활용한 액션 플랜 및 멘토 추천 생성"""
        try:
            from openai import AsyncOpenAI
            
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return "AI 분석 기능이 현재 이용 불가합니다."
            
            client = AsyncOpenAI(api_key=api_key)
            
            # 회사 비전 컨텍스트 가져오기
            company_vision_context = ""
            try:
                company_vision_context = self.retriever_agent.get_company_vision_context()
                print(f"🔍 DEBUG - path_deepening에서 회사 비전 컨텍스트 가져오기 성공: {len(company_vision_context)}자")
            except Exception as e:
                print(f"❌ WARNING - path_deepening에서 회사 비전 컨텍스트 가져오기 실패: {e}")
                company_vision_context = ""
            
            path_name = selected_path.get('name', '선택된 경로')
            
            # 디버깅: AI 메서드에 전달된 데이터 확인
            print(f"🔍 DEBUG - path_deepening AI 메서드에 전달된 merged_user_data: {merged_user_data}")
            print(f"🔍 DEBUG - 상담 대상자 정보: 이름={merged_user_data.get('name', 'None')}, 경력={merged_user_data.get('experience', 'None')}, 스킬={merged_user_data.get('skills', 'None')}, 도메인={merged_user_data.get('domain', 'None')}")
            print(f"🔍 DEBUG - path_deepening user_goals: {user_goals}")
            print(f"🔍 DEBUG - path_selection_context: {path_selection_context}")
            
            # retrieved_data에서 사내 경력 데이터와 뉴스 데이터 추출
            career_data = retrieved_data.get('career_data', [])
            news_data = retrieved_data.get('news_data', [])
            
            print(f"🔍 DEBUG - career_data: {len(career_data)}개, news_data: {len(news_data)}개")
            
            career_context = ""
            news_context = ""
            
            # 사내 경력 데이터 처리 (간결하게 개선)
            if career_data:
                print(f"✅ SUCCESS - {len(career_data)}개의 사내 구성원 데이터 활용 가능")
                career_context = f"""
**사내 구성원 성공 사례 ({len(career_data)}명 분석):**
- 총 {len(career_data)}명의 유사 경력 구성원 데이터 분석 완료
- 경력 전환 및 성장 패턴 파악 가능
- 개인정보 보호를 위해 익명화 처리됨
- 실제 사내 성공 사례 기반 분석 결과 제공
"""
                print(f"🔍 DEBUG - 생성된 career_context 길이: {len(career_context)}")
            else:
                career_context = "**사내 구성원 데이터:** 현재 분석 가능한 데이터 없음"
                print("❌ WARNING - career_data가 비어있어 기본 메시지 사용")
            
            # 최신 뉴스 데이터 처리 (간결하게 개선)
            if news_data:
                print(f"✅ SUCCESS - {len(news_data)}개의 최신 뉴스 데이터 활용 가능")
                news_context = f"""
**최신 업계 동향 및 기술 트렌드 ({len(news_data)}개 뉴스 분석):**
- 총 {len(news_data)}개의 최신 뉴스 데이터 분석 완료
- 업계 최신 동향 및 기술 발전 방향 파악 가능
- 커리어 성장과 연계된 시장 트렌드 정보 제공
- 선택한 커리어 경로와 관련된 최신 업계 변화 반영
- 실제 뉴스 데이터 기반 분석 결과 제공
"""
                print(f"🔍 DEBUG - news_context 생성 완료: {len(news_context)}자")
            else:
                news_context = "**최신 뉴스 데이터:** 현재 분석 가능한 데이터 없음"
                print("❌ WARNING - news_data가 비어있어 기본 메시지 사용")
            
            # path_selection_context 정보를 프롬프트에 추가 (AI가 컨텍스트 판단)
            selection_context_str = ""
            if path_selection_context:
                combined_context = path_selection_context.get('combined_user_context', '')
                path_name = path_selection_context.get('selected_path_name', '정보 없음')
                
                # 사용자의 전체 컨텍스트가 있는 경우 AI가 분석하도록 프롬프트 구성
                if combined_context.strip():
                    selection_context_str = f"""
**🎯 {merged_user_data.get('name', '고객')}님의 경로 선택 및 상세 컨텍스트:**

**선택한 경로:** {path_name}

**사용자 답변 전체 컨텍스트:**
"{combined_context}"

**💡 AI 분석 요청:**
위의 사용자 답변을 종합적으로 분석하여 다음 요소들을 파악해주세요:
1. **경로 선택 이유**: 왜 이 경로를 선택했는지
2. **현재 상황과 고민**: 어떤 상황에서 어떤 고민을 하고 있는지
3. **구체적 목표**: 무엇을 달성하고 싶어하는지
4. **개인적 동기**: 개인적인 성장 동기와 기대사항
5. **제약 조건**: 현재 상황에서의 제약이나 우려사항

**🎯 개인화 전략:**
이 분석을 바탕으로 **{merged_user_data.get('name', '고객')}님**만을 위한 구체적이고 실행 가능한 맞춤형 조언을 제공해주세요."""
                else:
                    # 기본 컨텍스트만 있는 경우
                    selection_context_str = f"""
**경로 선택 컨텍스트:**
- **선택한 경로**: {path_name}
- **일반적인 관심 분야**: {path_name} 관련 성장 희망"""
            
            # 멘토 추천 프롬프트 개선
            # --- 데이터 기반 성장 사례 분석 섹션 작성 지침 추가 ---
            data_case_guideline = '''
**[데이터 기반 성장 사례 분석 섹션 작성 지침(무조건 준수):]**
- 반드시 실제 사내 구성원 데이터(경력, 스킬, 성장 과정 등), 뉴스만을 기반으로 작성하세요.
- "{name}님과 유사한 배경에서 시작"이라는 점을 강조하세요.
- 실제 데이터에 없는 정보(예: 이직, 외부 대기업 경력, 외부 AI팀 근무 등)는 절대 언급하지 마세요.
- 성장 스토리, 성공 패턴 등도 실제 사내 데이터(경력, 스킬, 프로젝트, 사내 활동 등)만을 바탕으로 작성하세요.
- 없는 정보, 추정/가공된 외부 경력, 허구의 이직/외부 활동 등은 절대 포함하지 마세요.
- 성공 사례는 실제 데이터가 있는 만큼만 작성하세요. (예: 1명만 있으면 1명, 2명이면 2명, 최대 3명까지)
'''.format(name=merged_user_data.get('name', '고객'))

            prompt = f"""
당신은 SKAX의 시니어 커리어 멘토입니다. 동료 구성원인 {merged_user_data.get('name', '고객')}님의 커리어 성장을 위한 실무적인 조언과 구체적인 액션 플랜을 제공해주세요.

🚨 **중요 지침 - 반드시 준수해주세요:**
1. 아래 응답 형식의 모든 섹션을 **빠짐없이** 포함해주세요
2. 특히 "사내 선배들의 성공 사례"와 "최신 업계 동향" 섹션은 **절대 생략하지 마세요**
3. 각 섹션의 하위 항목들을 **완전히 작성**해주세요
4. 답변은 상세하게 작성해주세요 (길이 제한 없음)
5. 토큰 제한으로 인해 답변이 중간에 끊어지지 않도록 주의해주세요
6. **최신 업계 동향 및 트렌드 섹션은 반드시 실제 뉴스 데이터(아래 news_data)만을 기반으로 작성하고, news_data의 실제 뉴스 기사 내용을 참고해서 구체적으로 답변하세요.**

{company_vision_context}

**상담 대상자 정보:**
- 이름: {merged_user_data.get('name', '고객')}님
- 현재 경력: {merged_user_data.get('experience', '정보 없음')}
- 보유 스킬: {merged_user_data.get('skills', '정보 없음')}
- 담당 도메인: {merged_user_data.get('domain', '정보 없음')}
- 희망 성장 방향: {path_name}
- 고민과 목표: {user_goals[:200]}

{selection_context_str}

**사내 동료들의 성장 사례:**
{career_context}

{data_case_guideline}

**최신 업계 동향 및 기술 트렌드:**
{news_context}

**데이터 기반 성장 사례 분석 섹션 작성 지침(무조건 준수):**
- 반드시 실제 사내 구성원 데이터(경력, 스킬, 성장 과정 등)만을 기반으로 작성하세요.
- "이 구성원은 {merged_user_data.get('name', '고객')}님과 유사한 배경에서 시작하여, 초기에는 온라인 강의와 사내 프로젝트에 적극 참여하고 실무경험을 쌓았다"와 같이 유사한 배경에서 시작했다는 느낌을 강조하세요.
- 실제 데이터에 없는 정보(예: 이직, 외부 대기업 경력, 외부 AI팀 근무 등)는 절대 언급하지 마세요.
- 성장 스토리, 경력 패턴 등도 실제 사내 데이터(경력, 스킬, 프로젝트, 사내 활동 등)만을 바탕으로 작성하세요.
- 없는 정보, 추정/가공된 외부 경력, 허구의 이직/외부 활동 등은 절대 포함하지 마세요.
- 성공 사례는 실제 데이터가 있는 만큼만 작성하세요. (예: 1명만 있으면 1명, 2명이면 2명, 최대 3명까지)

**🎯 핵심 요구사항**: 위에 제공된 사용자 답변을 종합적으로 분석하여 **{merged_user_data.get('name', '고객')}님**의 구체적인 상황, 고민, 목표에 직접적으로 도움이 되는 조언을 우선적으로 제공해주세요.

**💡 개인화 전략**: 사용자 답변에서 드러난 개인적 상황, 고민, 기대사항을 종합적으로 분석하여 일반적인 조언이 아닌 **{merged_user_data.get('name', '고객')}님**만을 위한 맞춤형 액션 플랜을 제시해주세요.

**⚠️ 필수 준수사항:**
1. 아래 응답 형식을 **정확히** 따라 주세요
2. 모든 섹션을 **빠짐없이** 포함해주세요
3. 특히 "사내 선배들의 성공 사례"와 "최신 업계 동향" 섹션은 **반드시 포함**해야 합니다
4. 각 섹션 제목과 하위 항목들을 **완전히 작성**해주세요
5. 답변은 상세하게 작성해주세요 (길이 제한 없음)

**멘토링 응답 형식:**

## {merged_user_data.get('name', '고객')}님을 위한 성장 로드맵

안녕하세요! {merged_user_data.get('name', '고객')}님의 **{path_name}** 방향 성장을 함께 계획해보겠습니다.

### {merged_user_data.get('name', '고객')}님의 상황 및 목표 분석

**사용자 답변 전체 컨텍스트:**
"{combined_context}"

**💡 AI 분석 결과:**
위 답변을 종합 분석하여 {merged_user_data.get('name', '고객')}님의 핵심 상황과 목표를 파악했습니다. 이를 바탕으로 실무적이고 구체적인 성장 전략을 제시하겠습니다.

### 사내 선배들의 성공 사례 (무조건 포함)

**{path_name} 로드맵 관련 동료들의 실제 성장 스토리:**

**데이터 기반 성장 사례 분석:** (무조건 포함)
{f"- **{merged_user_data.get('name', '고객')}님**과 유사한 배경을 가진 사내 선배 {min(len(career_data), 3)}명의 실제 데이터를 분석했습니다" if career_data else "- 유사한 경험을 가진 동료들의 실제 데이터를 분석해보면"}
- 구성원A: [실제 데이터를 바탕으로 한 구체적인 성장 스토리와 현재 경로 선택 배경] (실제 데이터가 있을 때만 작성)
- 구성원B: [실제 데이터를 바탕으로 한 구체적인 성장 스토리와 현재 경로 선택 배경] (2명 이상일 때만 작성)
- 구성원C: [실제 데이터를 바탕으로 한 구체적인 성장 스토리와 현재 경로 선택 배경] (3명 이상일 때만 작성)

**⚠️ 중요: 이 "사내 선배들의 성공 사례" 섹션은 반드시 포함해야 합니다. 생략하지 마세요!**

### 최신 업계 동향 및 시장 트렌드 (무조건 포함)

**{path_name} 관련 최신 업계 동향:** (무조건 포함)
{f"- **{len(news_data)}개의 최신 뉴스**를 분석하여 {path_name} 분야의 시장 동향과 기술 발전 방향을 파악했습니다" if news_data else "- 최신 업계 동향 및 기술 트렌드 분석 결과"}
- **시장 전망**: [실제 데이터를 바탕으로 한 뉴스 데이터 기반 {path_name} 분야의 성장 전망과 기회 요인]
- **기술 트렌드**: [실제 데이터를 바탕으로 한 최신 뉴스에서 확인된 핵심 기술 발전 방향과 **{merged_user_data.get('name', '고객')}님**의 성장 기회]
- **업계 변화**: [실제 데이터를 바탕으로 한 시장 변화에 따른 새로운 역할과 스킬 요구사항]
- **성장 기회**: [실제 데이터를 바탕으로 한 뉴스 분석 결과 도출된 **{merged_user_data.get('name', '고객')}님**을 위한 구체적 성장 기회]

**⚠️ 중요: 이 "최신 업계 동향" 섹션도 반드시 포함해야 합니다. 생략하지 마세요!**

**{merged_user_data.get('name', '고객')}님과의 데이터 일치점:** (무조건 포함)
- **경력 수준**: [고객의 현재 경력과 일치하는 선배들의 당시 상황]
- **기술 스택**: [고객의 보유 기술과 유사한 선배들의 시작점]
- **도메인 경험**: [고객의 도메인과 겹치는 선배들의 성장 배경]
- **성장 동기**: [고객의 목표와 일치하는 선배들의 당시 목표]

**신뢰할 수 있는 성장 패턴:** (무조건 포함)
- **핵심 성공 요인**: [실제 데이터에서 발견되는 공통적인 성장 전략]
- **단계별 성장 과정**: [데이터로 검증된 1년차→3년차→5년차 성장 경로]
- **성공 지표**: [선배들이 실제로 달성한 구체적인 성과 지표]

**{merged_user_data.get('name', '고객')}님을 위한 맞춤형 벤치마킹:** (무조건 포함)
- **답변 종합 분석**: 사용자 답변 전체를 분석하여 파악한 핵심 니즈를 바탕으로, 유사한 고민을 가졌던 선배들의 구체적인 해결 과정과 성공 전략
- **개인 맞춤 전략**: {merged_user_data.get('name', '고객')}님의 현재 상황({merged_user_data.get('experience', '정보 없음')} 경력, {', '.join(merged_user_data.get('skills', ['정보 없음'])[:3])} 스킬)과 답변에서 드러난 목표를 고려한 최적 성장 로드맵
- **트렌드 기반 기회**: 최신 뉴스 분석 결과 파악된 {path_name} 분야의 성장 기회와 **{merged_user_data.get('name', '고객')}님**의 경력을 연계한 전략적 포지셔닝
- **실행 가능한 액션**: 답변 분석 결과와 최신 트렌드를 반영하여 다음 3개월 내 즉시 시작할 수 있는 실무적 조치들
- **예상 성과 및 타임라인**: 답변에서 드러난 개인적 목표와 시장 전망을 바탕으로 한 단계별 마일스톤과 예상 기간

*🌟 이 추천 방향성은 개인의 경험 데이터와 함께 SKAX의 최신 기술 트렌드 및 비전 방향성을 종합 분석하여 제시됩니다.*

### 추천 멘토/선배 (무조건 포함)

**실제 구성원 데이터 기반 멘토 추천:** 

**멘토 A (추천도: ★★★★★)**
- **배경**: [**{merged_user_data.get('name', '고객')}님**과 유사한 경력/기술 스택을 가진 선배의 구체적 프로필]
- **추천 이유**: 사용자 답변에서 드러난 고민과 목표에 유사한 경험을 가진 실제 선배
- **성장 스토리**: 유사한 출발점에서 현재 어떤 성과를 달성했는지 구체적 데이터 기반 스토리
- **멘토링 가능 영역**: 사용자 답변 분석 결과 파악된 구체적인 니즈와 관련된 실무적 조언 가능 분야

**멘토 B (추천도: ★★★★☆)**  
- **배경**: [다른 관점에서 **{path_name}** 경로를 성공적으로 걸어온 선배의 프로필]
- **추천 이유**: 사용자 답변에서 드러나지 않은 잠재적 니즈나 놓칠 수 있는 부분을 보완해줄 수 있는 멘토
- **성장 스토리**: 해당 멘토의 독특한 성장 스토리와 핵심 인사이트
- **멘토링 가능 영역**: 답변 분석을 통해 파악된 개인 특성에 맞는 특별한 조언 가능 분야

### {merged_user_data.get('name', '고객')}님 맞춤 액션 플랜

### 개인 맞춤 액션 플랜

**1. 사용자 답변 기반 현황 분석**
- 답변에서 드러나는 **경로 선택 이유**와 **개인적 동기**
- 선택한 경로(**{path_name}**)에 대한 구체적인 관심 배경과 기대 효과  
- 현재 상황에서 드러나는 **고민 포인트**와 **성장 의지**

**2. 맞춤형 전략 수립**
- 답변에서 파악된 **구체적 목표**를 위한 실행 가능한 액션 아이템
- 개인적 상황과 **제약 조건**을 고려한 현실적 성장 로드맵
- 답변에서 드러난 **개인적 기대치**와 **우선순위**에 부합하는 성장 경로


💡 **이 계획은 {merged_user_data.get('name', '고객')}님의 전체 답변 컨텍스트를 종합 분석하여 수립되었으며, 개인적 상황과 목표에 맞춰 언제든 조정 가능합니다.**

**멘토링 신청 및 연결 방법:**
- **사내 멘토링 프로그램**: HR팀 공식 채널 통해 신청 (월 1회 매칭)
- **비공식 멘토링**: 사내 메신저나 이메일을 통한 개별 컨택
- **그룹 멘토링**: 유사한 목표를 가진 동료들과 함께하는 그룹 세션 참여

---(이 대시부분 무조건 포함)

**다음 스텝: 체계적인 학습 로드맵 설계**

**{merged_user_data.get('name', '고객')}님**의 답변 컨텍스트 분석을 바탕으로 위에서 제시한 성장 전략과 멘토링 계획을 더욱 구체적이고 실행 가능한 학습 로드맵으로 발전시켜보시겠어요?
학습 로드맵을 원하시면 "네, 학습 로드맵을 설계해주세요"라고 답변해주세요!

---

**작성 원칙:**
- 동료에게 조언하는 따뜻하고 실무적인 톤
- **사용자의 전체 답변 컨텍스트를 종합적으로 분석**하여 개인화된 조언 제공
- 답변 분석을 통해 파악된 개인적 상황과 목표에 직접 대응하는 실무적 해결책 제시
- 실제 사내에서 활용 가능한 리소스와 기회 중심
- 개인정보는 익명화하되 실제 사례의 진정성 유지
- 회사 비전 정보가 제공된 경우, 해당 가치와 전략 방향에 부합하는 멘토링과 액션 플랜 제공
- **최소 2000자 이상**으로 상세하고 구체적으로 작성
- **모든 섹션을 빠짐없이 포함**하고 각 항목을 완전히 작성
- 특히 "사내 선배들의 성공 사례"와 "최신 업계 동향" 섹션은 **절대 생략하지 말 것**

🚨 **최종 체크리스트 - 응답 전 반드시 확인:**
✓ "사내 선배들의 성공 사례" 섹션이 포함되어 있는가?
✓ "최신 업계 동향 및 시장 트렌드" 섹션이 포함되어 있는가?
✓ 각 섹션의 하위 항목들이 모두 작성되어 있는가?
✓ 답변이 최소 2000자 이상인가?
✓ 모든 섹션이 완전히 작성되어 있는가?

이제 응답을 작성해주세요:
"""
            
            # --- AI 프롬프트 지침이 답변에 포함되지 않도록 명확히 안내 ---
            prompt += """

---
**중요:** 위의 모든 지침, 체크리스트, (무조건 포함), (이 대시부분 무조건 포함), ⚠️, 🚨 등은 AI가 답변을 작성할 때 참고만 하며, 실제 응답(사용자에게 보여지는 답변)에는 절대 포함하지 마세요. 실제 답변에는 오직 요구된 마크다운 구조와 실질적 내용만 포함하세요.
아래 멘토링 응답은 '안녕하세요' 등 인사말 없이 바로 {merged_user_data.get('name', '고객')}님의 상황 분석 또는 핵심 제안으로 시작하세요. 첫 문장은 반드시 분석/제안/상황 요약으로 시작해야 합니다.

---

"""
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=6000,
                temperature=0.2
            )
            
            ai_content = response.choices[0].message.content.strip()
            
            return ai_content
            
        except Exception as e:
            print(f"AI 액션 플랜 생성 중 오류: {e}")
            return "액션 플랜을 생성하는 중 문제가 발생했습니다. 다시 시도해주세요."
    
    async def process_deepening_node(self, state: ChatState) -> Dict[str, Any]:
        """
        사용자의 목표와 이유를 분석하여 실행 전략을 제시한다.
        """
        print("🎯 경로 심화 논의 시작...")
        
        # State 전달 트레이싱 확인 (디버깅)
        print(f"🔍 DEBUG - path_deepening에서 받은 state 트레이싱:")
        print(f"🔍 DEBUG - state_trace: {state.get('state_trace', 'None')}")
        print(f"🔍 DEBUG - career_positioning_timestamp: {state.get('career_positioning_timestamp', 'None')}")
        print(f"🔍 DEBUG - consultation_stage: {state.get('consultation_stage', 'None')}")
        print(f"🔍 DEBUG - awaiting_user_input: {state.get('awaiting_user_input', 'None')}")
        
        user_response = state.get("user_question", "")
        selected_path = state.get("selected_career_path", {})
        user_data = self.graph_builder.get_user_info_from_session(state)
        collected_info = state.get("collected_user_info", {})
        merged_user_data = {**user_data, **collected_info}
        
        # path_selection 단계에서의 사용자 선택 정보 추출
        path_selection_info = state.get("path_selection_info", {})
        path_selection_context = {
            "selected_path_name": selected_path.get("name", "선택된 경로"),
            "selected_path_id": selected_path.get("id", ""),
            "combined_user_context": f"{path_selection_info.get('user_input_for_deepening', '')} {user_response}".strip()  # 전체 사용자 컨텍스트
        }
        
        # 디버깅: 데이터 확인
        print(f"🔍 DEBUG - path_deepening user_data from session: {user_data}")
        print(f"🔍 DEBUG - path_deepening collected_info: {collected_info}")
        print(f"🔍 DEBUG - path_deepening merged_user_data: {merged_user_data}")
        print(f"🔍 DEBUG - path_selection_context: {path_selection_context}")
        
        # career_positioning에서 검색된 사내 경력 데이터 활용
        # path_selection과 path_deepening 사이에는 데이터 손실이 없어야 함
        
        # 먼저 state의 모든 career 관련 키들을 확인
        career_related_keys = [key for key in state.keys() if 'career' in key.lower()]
        print(f"🔍 DEBUG - state의 career 관련 키들: {career_related_keys}")
        
        # 전체 state 키 확인 (디버깅용)
        all_state_keys = list(state.keys())
        print(f"🔍 DEBUG - 전체 state 키 개수: {len(all_state_keys)}")
        print(f"🔍 DEBUG - 모든 state 키들: {all_state_keys}")
        
        # retrieved_career_data 확인
        existing_career_data = state.get("retrieved_career_data", [])
        print(f"🔍 DEBUG - state에서 가져온 retrieved_career_data: {len(existing_career_data)}개")
        print(f"🔍 DEBUG - retrieved_career_data 타입: {type(existing_career_data)}")
        
        if existing_career_data:
            print(f"🔍 DEBUG - 첫 번째 데이터 샘플: {existing_career_data[0] if existing_career_data else 'None'}")
            print(f"🔍 DEBUG - 모든 employee_id: {[item.get('employee_id', 'N/A') for item in existing_career_data[:5]]}")
            
            # 데이터 구조 검증
            if isinstance(existing_career_data[0], dict):
                sample_keys = list(existing_career_data[0].keys())
                print(f"🔍 DEBUG - 데이터 구조 검증 OK - 샘플 키들: {sample_keys}")
            else:
                print(f"❌ WARNING - 데이터 구조 이상: 첫 번째 항목이 dict가 아님 - {type(existing_career_data[0])}")
        else:
            print("❌ WARNING - retrieved_career_data가 비어있음!")
        
        # 뉴스 검색 (간결하게 개선)
        fresh_news_data = []
        try:
            # Agent를 사용하여 뉴스 검색
            search_query = f"{selected_path.get('name', '')} {merged_user_data.get('domain', '')}"
            fresh_news_data = self.news_agent.search_relevant_news(
                query=search_query,
                n_results=10
            )
            print(f"✅ SUCCESS - Agent 기반 뉴스 검색 완료: {len(fresh_news_data)}개")
        except Exception as e:
            print(f"❌ ERROR - Agent 뉴스 검색 중 오류 발생: {e}")
            fresh_news_data = []
        
        # 최종 retrieved_data 구성
        retrieved_data = {
            "career_data": existing_career_data,
            "news_data": fresh_news_data
        }
        
        print(f"🔍 DEBUG - AI 호출 전 최종 retrieved_data: career_data={len(existing_career_data)}개, news_data={len(fresh_news_data)}개")
        
        # AI 기반 사내 데이터 활용 액션 플랜 생성 (path_selection 컨텍스트 포함)
        ai_response = await self._generate_ai_action_plan(
            merged_user_data, selected_path, user_response, retrieved_data, path_selection_context
        )
        
        # 사용자 응답 컨텍스트 저장 (path_selection 정보 포함)
        consultation_context = {
            "user_goals": user_response,
            "selected_path": selected_path,
            "path_selection_context": path_selection_context,
            "analysis_timestamp": "2025-07-02"
        }
        
        # path_deepening 단계 결과를 별도 state에 저장
        # 응답 구성
        strategy_response = {
            "message": ai_response,
            "action_plan": {
                "context": consultation_context,
                "data_sources": ["career_data", "news_data", "networking_opportunities"]
            }
        }
        # HTML 로그 저장
        save_career_response_to_html("path_deepening", strategy_response, state.get("session_id", "unknown"))

        # path_deepening_info에 결과 저장 (반환 딕셔너리에도 명시적으로 포함)
        return {
            **state,
            "consultation_stage": "learning_decision",
            "consultation_context": consultation_context,
            "formatted_response": strategy_response,
            "final_response": strategy_response,
            "path_deepening_info": strategy_response,  # 명시적으로 포함
            "awaiting_user_input": True,
            "next_expected_input": "learning_roadmap_decision",
            "processing_log": state.get("processing_log", []) + ["실행 전략 수립 완료"]
        }
