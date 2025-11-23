# app/graphs/agents/formatter.py
"""
* @className : ResponseFormattingAgent
* @description : 응답 포맷팅 에이전트 모듈
*                검색된 정보를 사용자 친화적인 형태로 포맷팅하는 에이전트입니다.
*                마크다운 형식으로 구조화된 응답을 생성합니다.
*
"""

from typing import Dict, Any, Optional, List, Union
import logging
from datetime import datetime
import openai
import os
import json
import markdown
import re

class ResponseFormattingAgent:
    """
    LLM 기반 적응적 응답 포맷팅 에이전트
    
    AI가 질문 유형과 컨텍스트를 분석하여 최적화된 응답을 생성합니다.
    검색된 커리어 사례와 교육과정을 자연스럽게 통합하여 
    개인화된 커리어 가이던스를 제공합니다.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.client = None  # OpenAI 클라이언트를 지연 초기화
        
        self.system_prompt = """
G.Navi AI 커리어 컨설팅 시스템의 친근한 커리어 코치로 활동하세요.

**핵심 톤&스타일:**
• 친근하고 편안한 대화체 (마치 옆에서 조언해주는 선배처럼)
• 구어체와 줄글 형태로 자연스럽게 상담
• 공감과 격려를 자연스럽게 녹여낸 대화
• 과도한 이모지나 구조화는 피하고 자연스러운 문장으로

**중요: 첫 만남과 이어지는 대화 구분**
• 컨텍스트에 "첫 상호작용"이라고 명시된 경우에만 "안녕하세요!" 인사
• "이미 대화가 진행된 상태"라고 명시된 경우 인사말 없이 자연스럽게 질문에 바로 답변
• 매번 "안녕하세요"나 "[사용자명]님"으로 시작하지 않기
• 대화가 이어지는 경우: "그러면...", "음...", "그 부분에 대해서는..." 등으로 자연스럽게 시작

** 이전 대화 요약 요청 처리**
사용자가 다음과 같은 표현을 사용하면 이전 대화 내역을 구체적으로 요약해주세요:
• "이전에 질문했던 것들", "앞서 말했던", "과거에 상담했던", "전에 얘기했던"
• "무엇을 질문했는지", "어떤 내용을 다뤘는지", "히스토리", "기록"

**이전 대화 요약 시 가이드라인:**
1. 시간순으로 주요 질문과 답변을 정리
2. 각 대화의 핵심 내용을 2-3줄로 요약
3. "그때 이런 내용으로 상담드렸었죠", "그 당시에는 이런 질문을 해주셨었어요" 같은 자연스러운 표현 사용
4. 단순 나열보다는 대화하듯 연결해서 설명

**응답 스타일 가이드:**

1. **간단한 인사/질문**: 
   - 편안하고 친근한 톤으로 응답
   - "안녕하세요! 저는 G.Navi AI 커리어 코치예요. 무엇이 궁금하신가요?"

2. **일반적인 상담**: 
   - 마치 카페에서 대화하듯 자연스럽게
   - "그러게요, 그런 고민 정말 많이 하시죠. 제가 보기엔..."
   - 딱딱한 목록보다는 자연스러운 문단으로

3. **구체적인 커리어 상담**: 
   - 실제 사례를 자연스럽게 언급
   - "저희 회사에서 비슷한 상황이었던 분이 있는데요..."
   - 조언을 대화하듯 풀어서 설명

4. **성장 방향 상담**:
   - 체계적이지만 친근한 톤으로
   - "음, [사용자명]님 상황을 보니 이런 방향으로 접근해보시면 좋을 것 같아요"
   - 단계별로 나누되 자연스러운 문장으로 연결

5. **이전 대화 요약 요청인 경우**:
   - "아, 이전에 상담했던 내용들을 정리해드릴게요!"
   - 시간순으로 주요 내용을 자연스럽게 회상하듯 설명
   - "그때 이런저런 얘기를 나누었었죠"와 같은 친근한 톤

**응답 구조:**
- 제목: 컨텍스트에 "첫 상호작용"이라고 명시된 경우에만 "[사용자명]님 안녕하세요!"로 시작
- 이어지는 대화: 인사말 없이 바로 질문에 대한 답변으로 시작
- 본문은 자연스러운 문단 형태
- 과도한 ### 구조화나 번호 매기기 지양
- 마지막에 "혹시 더 궁금한 게 있으시면 언제든 말씀해주세요!" 같은 자연스러운 마무리

**중요 원칙:**
- 보고서나 매뉴얼 같은 형식을 요구하면, 보고서 형식으로 작성
- 친구나 선배가 조언해주는 느낌의 자연스러운 대화체
- 사용자 질문에 맞는 적절한 길이와 깊이
- 불필요한 정보는 억지로 넣지 않기
- **이전 대화 내역이 제공되면 반드시 참고하여 연속성 있는 상담 진행**

** 뉴스 데이터 활용 가이드라인:**
- 업계 트렌드나 채용 시장에 대한 질문이 있을 때 관련 뉴스 정보를 자연스럽게 활용
- "최근 뉴스를 보니까...", "업계 소식에 따르면..." 같은 자연스러운 표현으로 뉴스 내용 인용
- AI, 금융, 반도체, 제조 도메인별 최신 트렌드와 채용 정보를 활용하여 현실적인 조언 제공
- 뉴스 출처(source)와 게시일(published_date)을 간단히 언급하여 신뢰성 확보
- 단순히 뉴스를 나열하지 말고, 사용자 상황에 맞는 실용적인 조언과 연결

** 최신 뉴스/트렌드 질문 시 우선 대응 규칙:**
사용자가 다음과 같은 표현을 사용하면 뉴스 데이터를 최우선으로 활용하세요:
- "최신 뉴스", "최근 뉴스", "업계 소식", "시장 동향", "트렌드", "현재 상황"
- "요즘", "지금", "현재", "최근", "올해", "2024년", "2025년"
- "채용 시장", "취업 트렌드", "업계 변화", "산업 동향"
- "어떤 일이 일어나고 있는지", "무슨 변화가", "어떤 흐름"

**최신 뉴스 질문 감지 시 대응 방식:**
1. **우선순위**: 뉴스 데이터 > 커리어 사례 > 교육과정
2. **시작 표현**: "최근 업계 소식을 보면...", "요즘 뉴스를 살펴보니...", "최신 트렌드를 보면..."
3. **구체적 인용**: 제공된 뉴스의 제목, 내용, 출처를 구체적으로 언급
4. **실용적 연결**: 뉴스 내용을 사용자 상황에 맞는 조언으로 자연스럽게 연결
5. **신뢰성 확보**: "○○에서 보도된 바에 따르면...", "△월 발표된 자료에 의하면..." 식으로 출처 명시

**응답 예시 (자연스러운 대화체):**

[첫 상호작용인 경우]
안녕하세요! 저는 G.Navi AI 커리어 코치예요. Application PM으로의 성장 경로에 대해 궁금하시군요. 좋은 목표를 세우셨네요!

[이어지는 대화인 경우] 
Application PM으로의 성장 경로에 대해 궁금하시군요. 좋은 목표를 세우셨네요!

[이전 대화 요약 요청인 경우]
아, 이전에 상담했던 내용들을 정리해드릴게요! 그동안 이런저런 얘기를 나누었었죠.

처음에는 백엔드 개발자에서 PM으로의 전환에 대해 질문해주셨었고, 그때 기술적 백그라운드가 PM 역할에 어떤 도움이 되는지 설명드렸었어요. 그 다음에는 구체적인 스킬셋에 대해서도 물어보셨고...

(자연스럽게 이어지는 이전 대화 요약)

혹시 더 구체적으로 궁금한 부분이 있으시면 언제든 말씀해주세요!        """

    def _dict_to_markdown(self, data: Union[Dict, List, Any], depth: int = 0, show_empty: bool = True) -> str:
        """dict, list 등의 JSON 타입을 사람이 읽기 쉬운 마크다운으로 변환"""
        indent = "  " * depth
        
        if isinstance(data, dict):
            if not data:
                return "*(내용 없음)*" if show_empty else ""
            
            markdown_lines = []
            for key, value in data.items():
                # 키 정리 (언더스코어를 공백으로 변환하고 타이틀 케이스 적용)
                display_key = key.replace('_', ' ').title()
                
                if isinstance(value, (dict, list)):
                    nested_content = self._dict_to_markdown(value, depth + 1, show_empty)
                    if nested_content.strip() or show_empty:  # show_empty가 True면 빈 내용도 표시
                        markdown_lines.append(f"{indent}- **{display_key}:**")
                        markdown_lines.append(nested_content)
                else:
                    formatted_value = self._format_value(value, show_empty)
                    if formatted_value or show_empty:  # show_empty가 True면 빈 값도 표시
                        markdown_lines.append(f"{indent}- **{display_key}:** {formatted_value}")
            
            return "\n".join(markdown_lines) if markdown_lines else ("*(내용 없음)*" if show_empty else "")
        
        elif isinstance(data, list):
            if not data:
                return "*(빈 목록)*" if show_empty else ""
            
            markdown_lines = []
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    nested_content = self._dict_to_markdown(item, depth + 1, show_empty)
                    if nested_content.strip() or show_empty:  # show_empty가 True면 빈 내용도 표시
                        # 딕셔너리 리스트의 경우 더 깔끔하게 표시
                        if isinstance(item, dict) and len(item) <= 3 and not show_empty:
                            # 간단한 딕셔너리는 한 줄로 표시 (show_empty가 False일 때만)
                            summary = self._create_dict_summary(item)
                            if summary:
                                markdown_lines.append(f"{indent}{len([x for x in markdown_lines if x.strip()]) + 1}. {summary}")
                        else:
                            markdown_lines.append(f"{indent}{len([x for x in markdown_lines if x.strip()]) + 1}. ")
                            markdown_lines.append(nested_content)
                else:
                    formatted_item = self._format_value(item, show_empty)
                    if formatted_item or show_empty:  # show_empty가 True면 빈 값도 표시
                        markdown_lines.append(f"{indent}{len([x for x in markdown_lines if x.strip()]) + 1}. {formatted_item}")
            
            return "\n".join(markdown_lines) if markdown_lines else ("*(빈 목록)*" if show_empty else "")
        
        else:
            return self._format_value(data, show_empty)
    
    def _create_dict_summary(self, data: dict) -> str:
        """딕셔너리를 간단한 요약 문자열로 변환"""
        if not data:
            return ""
        
        # 모든 필드 포함
        items = []
        for key, value in data.items():
            display_key = key.replace('_', ' ').title()
            formatted_value = self._format_value(value)
            if formatted_value:
                items.append(f"{display_key}: {formatted_value}")
        
        return " | ".join(items) if items else ""
    
    def _format_value(self, value: Any, show_empty: bool = True) -> str:
        """값을 사용자 친화적으로 포맷팅"""
        if value is None:
            return "*정보 없음*" if show_empty else ""
        elif isinstance(value, bool):
            return "예" if value else "아니오"
        elif isinstance(value, (int, float)):
            # 특별한 숫자 값들 처리
            if value == 1.0 and isinstance(value, float):
                return "100%"  # confidence_score 같은 경우
            return f"{value:,}"
        elif isinstance(value, str):
            # 빈 문자열 처리
            if not value.strip():
                return "*정보 없음*" if show_empty else ""
            # 특정 패턴들 처리
            if value.strip() in ['*정보 없음*', '정보 없음', 'N/A', 'n/a', 'null', 'undefined']:
                return "*정보 없음*" if show_empty else ""
            
            # 이스케이프 문자 처리
            processed_value = value.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')
            
            # 긴 텍스트는 요약 (단, 한국어 기준으로)
            if len(processed_value) > 100:
                return f"{processed_value[:100]}..."
            return processed_value
        else:
            return str(value) if str(value) != 'None' else ("*정보 없음*" if show_empty else "")

    def format_adaptive_response(self,
                                user_question: str,
                                state: Dict[str, Any]) -> Dict[str, Any]:
        """LLM 기반 적응적 응답 포맷팅 - 직접 마크다운 응답"""
        self.logger.info("LLM 기반 적응적 응답 포맷팅 시작")
        
        try:
            # GNaviState에서 데이터 추출
            intent_analysis = state.get("intent_analysis", {})
            user_data = state.get("user_data", {})
            career_cases = state.get("career_cases", [])
            current_session_messages = state.get("current_session_messages", [])
            education_courses = state.get("education_courses", {})
            past_conversations = state.get("past_conversations", [])  # 과거 대화 내역 추가
            news_data = state.get("news_data", [])  # 뉴스 데이터 추가
            
            # 사용자 정보 추출
            user_name = user_data.get('name', '님')
            session_id = user_data.get('conversationId', '')
            
            # LLM을 위한 컨텍스트 구성
            context_data = self._prepare_context_for_llm(
                user_question, intent_analysis, 
                user_data, career_cases, 
                current_session_messages, education_courses, past_conversations, news_data
            )
            
            # LLM 호출하여 직접 마크다운 응답 생성
            formatted_content = self._call_llm_for_adaptive_formatting(context_data)
            
            # 최종 응답 구성
            result = {
                "formatted_content": formatted_content,
                "format_type": "adaptive",
                "timestamp": datetime.now().isoformat(),
                "user_name": user_name,
                "session_id": session_id
            }
            
            self.logger.info("LLM 기반 마크다운 응답 포맷팅 완료")
            return result
            
        except Exception as e:
            self.logger.error(f"LLM 기반 응답 포맷팅 실패: {e}")
            # 폴백: 간단한 응답 생성
            user_name = user_data.get('name', '님')
            
            # 첫 상호작용 여부 확인
            is_first_interaction = not current_session_messages or len(current_session_messages) <= 1
            
            if is_first_interaction:
                fallback_content = f"""# {user_name}님 안녕하세요!

현재 시스템 처리 중 일시적인 문제가 발생했습니다.
잠시 후 다시 시도해 주시거나, 더 구체적인 질문으로 다시 문의해 주세요.

---
*G.Navi AI가 {user_name}님의 커리어 성장을 응원합니다!*
"""
            else:
                fallback_content = f"""죄송합니다. 현재 시스템 처리 중 일시적인 문제가 발생했습니다.

잠시 후 다시 시도해 주시거나, 더 구체적인 질문으로 다시 문의해 주세요.

---
*G.Navi AI가 {user_name}님의 커리어 성장을 응원합니다!*
"""
            return {
                "formatted_content": fallback_content,
                "format_type": "fallback",
                "timestamp": datetime.now().isoformat(),
                "user_name": user_name,
                "session_id": user_data.get('conversationId', '')
            }
    
    def _prepare_context_for_llm(self, user_question: str, intent_analysis: Dict[str, Any],
                                user_data: Dict[str, Any],
                                career_cases: List[Any],
                                current_session_messages: List[Dict],
                                education_courses: Dict[str, Any] = None,
                                past_conversations: List[Dict] = None,
                                news_data: List[Dict] = None) -> str:
        """LLM을 위한 컨텍스트 데이터 준비 (통합된 current_session_messages 사용)"""
        
        context_sections = []
        
        #  통합된 대화 히스토리 처리 (현재 사용자 메시지 제외)
        previous_messages = current_session_messages[:-1] if len(current_session_messages) > 1 else []
        
        # 첫 상호작용 여부 판단
        is_first_interaction = len(previous_messages) == 0
        
        # 이전 대화 히스토리 표시
        if previous_messages:
            context_sections.append(" **이전 대화 기록**:")
            context_sections.append(" **중요: 이미 이전 대화가 있으므로 이를 참고하여 연속성 있는 답변을 하세요!**")
            context_sections.append(" **특별 지시**: 사용자가 '이전에', '앞서', '과거에', '전에' 등의 표현으로 이전 대화를 언급하면 아래 대화 내역을 구체적으로 요약해서 답변하세요.")
            
            # 최근 20개 대화만 포함 (통합된 만큼 조금 더 많이)
            recent_messages = previous_messages[-20:] if len(previous_messages) > 20 else previous_messages
            
            for i, msg in enumerate(recent_messages, 1):
                try:
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")
                    timestamp = msg.get("timestamp", "")
                    role_display = "사용자" if role == "user" else "AI"
                    
                    # 메시지 길이 제한 (통합된 처리)
                    if len(content) > 250:
                        content = content[:250] + "..."
                    
                    # 타임스탬프 정보 포함
                    timestamp_str = f" ({timestamp})" if timestamp else ""
                    
                    # 복원 소스 정보 추가 (선택적)
                    source_info = ""
                    restored_from = msg.get("metadata", {}).get("restored_from")
                    if restored_from == "springboot":
                        source_info = " [복원]"
                    
                    context_sections.append(f"{i}. [{role_display}]{timestamp_str}{source_info} {content}")
                except Exception as e:
                    self.logger.warning(f"메시지 파싱 오류: {e}")
                    continue
            context_sections.append("")  # 빈 줄 추가
        
        # 첫 상호작용인 경우에만 인사말 안내
        if is_first_interaction:
            context_sections.append("🔵 **첫 상호작용**: 이 사용자와의 첫 만남이므로 인사말로 시작하세요.")
            context_sections.append("")  # 빈 줄 추가
        
        # 사용자 질문
        context_sections.append(f'**현재 사용자 질문**: "{user_question}"')
        
        # 이전 대화 요약 요청인지 감지 (개선된 키워드)
        history_keywords = ['이전', '전에', '앞서', '과거', '예전', '질문했던', '말했던', '얘기했던', '상담했던', '대화', '히스토리', '내역', '기록', '무엇을', '뭘', '어떤', '언제', '처음에', '지난번', '그때']
        is_asking_for_history = any(keyword in user_question.lower() for keyword in history_keywords)
        
        if is_asking_for_history and previous_messages:
            context_sections.append(" **질문 유형 감지**: 사용자가 이전 대화 내용에 대해 질문하고 있습니다. 위의 이전 대화 기록을 참고하여 구체적으로 요약해서 답변해주세요.")
        
        
        context_sections.append("")  # 빈 줄 추가
        
        # 사용자 프로필
        # 새로운 JSON 구조: {name: "", projects: [...]}
        if user_data and isinstance(user_data, dict) and any(user_data.values()):
            user_profile_md = self._dict_to_markdown(user_data, show_empty=False)
            if user_profile_md.strip():
                context_sections.append(f"""
사용자 프로필:
{user_profile_md}
""")
        
        # 의도 분석
        if intent_analysis and isinstance(intent_analysis, dict) and any(intent_analysis.values()):
            # 오류가 있는 경우 제외
            if not intent_analysis.get("error"):
                intent_analysis_md = self._dict_to_markdown(intent_analysis, show_empty=False)
                if intent_analysis_md.strip():
                    context_sections.append(f"""
의도 분석 결과:
{intent_analysis_md}
""")
        
        # 커리어 사례
        career_cases_to_use = career_cases if career_cases else []
        if career_cases_to_use:
            career_section = " **실제 사내 커리어 사례 참고 자료**:\n"
            career_section += "저희 회사 구성원들의 실제 커리어 경험입니다. 상담할 때 자연스럽게 참고해주세요.\n\n"
            
            added_cases = 0
            for i, case in enumerate(career_cases_to_use[:5]):  # 최대 5개 사례 표시
                case_md = self._create_detailed_career_case_markdown(case, show_empty=False)
                if case_md.strip():  # 내용이 있는 경우만 추가
                    added_cases += 1
                    # Employee ID 추출 시도
                    employee_id = ""
                    employee_name = ""
                    if isinstance(case, dict):
                        metadata = case.get('metadata', {})
                        if isinstance(metadata, dict):
                            employee_id = metadata.get('employee_id', '')
                            employee_name = metadata.get('name', '')
                    
                    career_section += f"\n### **사례 {added_cases}: {employee_name if employee_name else '익명'} {f'({employee_id})' if employee_id else ''}**\n{case_md}\n"
            
            # 실제로 추가된 사례가 있는 경우만 컨텍스트에 포함
            if added_cases > 0:
                career_section += "\n**� 사례 활용 가이드:**\n"
                career_section += "- 상담할 때 '저희 회사에서 비슷한 경험을 한 분이 있는데요...' 같이 자연스럽게 언급\n"
                career_section += "- 구체적인 Employee ID나 상세 정보를 자연스럽게 대화에 녹여서 설명\n"
                career_section += "- 사용자 상황과 유사한 사례를 찾아서 경험과 조언을 공유하는 방식으로 활용\n"
                career_section += "- 딱딱한 사례 나열보다는 '그분 같은 경우에는...' 식으로 편안하게 설명\n"
                career_section += "- 성장 과정, 어려웠던 점, 극복 방법 등을 스토리텔링 방식으로 전달\n"
                context_sections.append(career_section)
        
        # 교육과정 정보 - 새로 추가
        if education_courses:
            try:
                education_section = "**교육과정 정보 (URL 포함)**:\n"
                
                # 교육과정 데이터가 딕셔너리이고 recommended_courses가 있는 경우
                if isinstance(education_courses, dict) and 'recommended_courses' in education_courses:
                    courses = education_courses['recommended_courses'][:8]  # 최대 8개로 확장
                    for i, course in enumerate(courses):
                        if isinstance(course, dict):
                            course_name = course.get('course_name', course.get('card_name', '과정명 없음'))
                            url = course.get('url', '')
                            source = course.get('source', '알 수 없음')
                            duration = course.get('duration_hours', course.get('인정학습시간', '정보 없음'))
                            
                            education_section += f"\n=== {i+1}. {course_name} ===\n"
                            education_section += f"출처: {source}\n"
                            education_section += f"학습시간: {duration}시간\n"
                            
                            # mySUNI 과정의 경우 추가 상세 정보 제공
                            if source == 'mysuni':
                                category = course.get('카테고리명', '')
                                channel = course.get('채널명', '')
                                difficulty = course.get('난이도', course.get('difficulty_level', ''))
                                rating = course.get('평점', '')
                                enrollments = course.get('이수자수', '')
                                skills = course.get('skillset', course.get('직무', []))
                                
                                if category:
                                    education_section += f"카테고리: {category}\n"
                                if channel:
                                    education_section += f"채널: {channel}\n"
                                if difficulty:
                                    education_section += f"난이도: {difficulty}\n"
                                if rating:
                                    education_section += f"평점: {rating}/5.0\n"
                                if enrollments:
                                    education_section += f"이수자수: {enrollments}명\n"
                                if skills and isinstance(skills, list) and skills:
                                    skills_str = ', '.join(skills[:3])  # 최대 3개만 표시
                                    education_section += f"관련 스킬: {skills_str}\n"
                            
                            # College 과정의 경우 추가 정보
                            elif source == 'college':
                                department = course.get('department', course.get('학부', ''))
                                course_type = course.get('course_type', course.get('교육유형', ''))
                                standard_course = course.get('표준과정', '')
                                
                                if department:
                                    education_section += f"학부: {department}\n"
                                if course_type:
                                    education_section += f"교육유형: {course_type}\n"
                                if standard_course:
                                    education_section += f"표준과정: {standard_course}\n"
                            
                            # URL 정보 - 학습하기 형태로 변경
                            if url and url.strip() and url != '정보 없음':
                                education_section += f"실제URL: {url}\n"
                                education_section += f"---\n**[학습하기]({url})**\n"
                            else:
                                education_section += f"URL: 정보 없음 (텍스트만: {course_name})\n"
                            
                            education_section += "\n"
                
                # 교육과정 데이터가 리스트인 경우
                elif isinstance(education_courses, list):
                    for i, course in enumerate(education_courses[:8]):  # 최대 8개로 확장
                        if isinstance(course, dict):
                            course_name = course.get('course_name', course.get('card_name', '과정명 없음'))
                            url = course.get('url', '')
                            source = course.get('source', '알 수 없음')
                            duration = course.get('duration_hours', course.get('인정학습시간', '정보 없음'))
                            
                            education_section += f"\n=== {i+1}. {course_name} ===\n"
                            education_section += f"출처: {source}\n"
                            education_section += f"학습시간: {duration}시간\n"
                            
                            # 추가 상세 정보 제공 (mySUNI/College 구분)
                            if source == 'mysuni':
                                category = course.get('카테고리명', '')
                                difficulty = course.get('난이도', '')
                                rating = course.get('평점', '')
                                enrollments = course.get('이수자수', '')
                                skills = course.get('skillset', course.get('직무', []))
                                
                                if category:
                                    education_section += f"카테고리: {category}\n"
                                if difficulty:
                                    education_section += f"난이도: {difficulty}\n"
                                if rating:
                                    education_section += f"평점: {rating}/5.0\n"
                                if enrollments:
                                    education_section += f"이수자수: {enrollments}명\n"
                                if skills and isinstance(skills, list) and skills:
                                    skills_str = ', '.join(skills[:3])
                                    education_section += f"관련 스킬: {skills_str}\n"
                            
                            elif source == 'college':
                                department = course.get('department', course.get('학부', ''))
                                course_type = course.get('course_type', course.get('교육유형', ''))
                                
                                if department:
                                    education_section += f"학부: {department}\n"
                                if course_type:
                                    education_section += f"교육유형: {course_type}\n"
                            
                            # URL 정보 - 학습하기 형태로 변경
                            if url and url.strip() and url != '정보 없음':
                                education_section += f"실제URL: {url}\n"
                                education_section += f"---\n**[학습하기]({url})**\n"
                            else:
                                education_section += f"URL: 정보 없음 (텍스트만: {course_name})\n"
                            
                            education_section += "\n"
                
                # 기타 형태의 데이터
                else:
                    education_section += f"{str(education_courses)[:300]}...\n"
                
                education_section += "\n 교육과정 추천 가이드:\n"
                education_section += "- 상담 시 '이런 과정이 도움이 될 것 같아요' 식으로 자연스럽게 추천\n"
                education_section += "- 평점이나 이수자수 같은 정보도 '꽤 평점이 좋더라구요' 식으로 편안하게 언급\n"
                education_section += "- URL이 있는 과정은 [학습하기] 링크로 안내\n"
                education_section += "- 사용자 상황에 맞는 과정을 골라서 추천하되 너무 많지 않게 (2-3개 정도)\n"
                education_section += "- 실제 URL만 사용하고 임의로 생성하지 않기"
                
                context_sections.append(education_section)
                
            except Exception as e:
                self.logger.warning(f"교육과정 정보 처리 실패: {e}")
                # 폴백으로 간단한 형태라도 제공
                context_sections.append(f"**교육과정 정보**: {str(education_courses)[:200]}...")
        
        # 🗃️ 새로운 과거 모든 채팅 세션의 대화내역 추가 (VectorDB에서 검색된 내용)
        if past_conversations and len(past_conversations) > 0:
            past_conversations_section = "**과거 모든 채팅 세션의 관련 대화내역**:\n"
            past_conversations_section += "이전 세션들에서 관련성이 높은 대화 내용들입니다. 사용자의 과거 질문과 상담 이력을 참고하여 연속성 있는 상담을 제공하세요.\n\n"
            
            for i, past_conv in enumerate(past_conversations[:3], 1):  # 최대 3개 과거 대화 세션
                try:
                    conversation_id = past_conv.get("conversation_id", f"세션_{i}")
                    summary = past_conv.get("summary", "")
                    content_snippet = past_conv.get("content_snippet", "")
                    created_at = past_conv.get("created_at", "")
                    relevance_score = past_conv.get("relevance_score", 0)
                    message_count = past_conv.get("message_count", 0)
                    
                    past_conversations_section += f"###  **과거 세션 {i}** (관련도: {relevance_score:.2f})\n"
                    if created_at:
                        past_conversations_section += f"**세션 날짜**: {created_at[:10]}\n"
                    past_conversations_section += f"**메시지 수**: {message_count}개\n"
                    
                    if summary and summary.strip():
                        past_conversations_section += f"**대화 요약**: {summary}\n"
                    
                    if content_snippet and content_snippet.strip():
                        past_conversations_section += f"**주요 내용**: {content_snippet}\n"
                    
                    past_conversations_section += "\n"
                    
                except Exception as e:
                    self.logger.warning(f"과거 대화 내역 파싱 오류: {e}")
                    continue
            
            past_conversations_section += "\n** 과거 대화 활용 가이드:**\n"
            past_conversations_section += "- 사용자가 '이전에', '전에', '과거에' 등의 표현을 사용하면 위 과거 대화 내용을 구체적으로 언급\n"
            past_conversations_section += "- '이전에 비슷한 질문을 해주셨었는데요...' 식으로 자연스럽게 연결\n"
            past_conversations_section += "- 과거 상담 내용과 현재 질문을 연결하여 발전적인 조언 제공\n"
            past_conversations_section += "- 사용자의 성장 과정이나 관심사의 변화를 파악하여 개인화된 상담 진행\n"
            past_conversations_section += "- 과거 대화 요약과 주요 내용을 바탕으로 구체적이고 맥락 있는 답변 제공\n"
            
            context_sections.append(past_conversations_section)
        
        # 📰 뉴스 데이터 정보 추가
        if news_data and len(news_data) > 0:
            news_section = "**최신 업계 뉴스 및 트렌드 정보**:\n"
            news_section += "업계 최신 소식과 채용 트렌드 정보입니다. 사용자 질문과 관련된 경우 자연스럽게 활용해주세요.\n\n"
            
            for i, news in enumerate(news_data[:3], 1):  # 최대 3개 뉴스
                try:
                    title = news.get("title", "제목 없음")
                    domain = news.get("domain", "")
                    category = news.get("category", "")
                    content = news.get("content", "")
                    published_date = news.get("published_date", "")
                    source = news.get("source", "")
                    similarity_score = news.get("similarity_score", 0)
                    
                    news_section += f"### **뉴스 {i}** (관련도: {similarity_score:.2f})\n"
                    news_section += f"**제목**: {title}\n"
                    if domain:
                        news_section += f"**도메인**: {domain}\n"
                    if category:
                        news_section += f"**카테고리**: {category}\n"
                    if published_date:
                        news_section += f"**발행일**: {published_date}\n"
                    if source:
                        news_section += f"**출처**: {source}\n"
                    if content:
                        news_section += f"**내용**: {content}\n"
                    
                    news_section += "\n"
                    
                except Exception as e:
                    self.logger.warning(f"뉴스 데이터 파싱 오류: {e}")
                    continue
            
            news_section += "\n** 뉴스 활용 가이드:**\n"
            news_section += "- 업계 트렌드나 채용 시장 질문 시 '최근 뉴스를 보니까...' 식으로 자연스럽게 인용\n"
            news_section += "- 출처와 발행일을 간단히 언급하여 신뢰성 확보 ('3월 테크뉴스에 따르면...')\n"
            news_section += "- 뉴스 내용을 단순 나열하지 말고 사용자 상황에 맞는 실용적 조언과 연결\n"
            news_section += "- AI, 금융, 반도체, 제조 등 도메인별 전문 정보 제공\n"
            news_section += "- 채용 트렌드, 연봉 정보, 필요 기술 등을 구체적으로 활용\n"
            news_section += "- **최신/트렌드 질문 시**: 뉴스 데이터를 가장 우선적으로 활용하여 현재 상황 설명\n"
            news_section += "- **구체적 인용**: '○○ 뉴스에서 보도된 바에 따르면...' 식으로 정확한 출처 명시\n"
            
            context_sections.append(news_section)
        
        # 질문 유형 분석 (성능 최적화)
        career_keywords = ['커리어', '진로', '목표', '방향', '계획', '비전', '미래', '회사', '조직']
        growth_keywords = ['성장', '발전', '패스', '로드맵', '어떻게', '방법', '단계', '과정']
        
        # 최신 뉴스/트렌드 질문 감지 키워드 추가
        news_keywords = ['최신', '최근', '뉴스', '업계', '소식', '시장', '동향', '트렌드', '요즘', '지금', '현재', 
                        '올해', '2024', '2025', '채용 시장', '취업 트렌드', '업계 변화', '산업 동향',
                        '어떤 일이', '무슨 변화', '어떤 흐름', '현재 상황']
        
        is_career_question = any(keyword in user_question.lower() for keyword in career_keywords)
        is_growth_guide_question = any(keyword in user_question.lower() for keyword in growth_keywords)
        is_news_trend_question = any(keyword in user_question.lower() for keyword in news_keywords)
        
        # 최신 뉴스/트렌드 질문인 경우 특별한 지침 추가
        if is_news_trend_question and news_data:
            news_priority_instruction = """

 **최신 뉴스/트렌드 질문 감지됨 - 뉴스 데이터 우선 활용 지침:**
- 사용자가 최신 정보를 원하므로 뉴스 데이터를 가장 우선적으로 활용하세요
- "최근 업계 소식을 보면...", "요즘 뉴스를 살펴보니...", "최신 트렌드를 보면..." 식으로 시작
- 제공된 뉴스의 제목, 내용, 출처를 구체적으로 언급하여 신뢰성 확보
- 뉴스 내용을 바탕으로 현실적이고 시의적절한 조언 제공
- 여러 뉴스가 있다면 도메인별로 정리하여 포괄적인 업계 현황 제시
- 커리어 사례나 교육과정은 뉴스 기반 조언을 보완하는 용도로만 활용
"""
            context_sections.append(news_priority_instruction)
        
        # 커리어 관련 질문인 경우 회사 비전 정보 추가
        if is_career_question:
            # Retriever에서 회사 비전 컨텍스트 가져오기
            from .retriever import CareerEnsembleRetrieverAgent
            retriever = CareerEnsembleRetrieverAgent()
            company_vision_section = retriever.get_company_vision_context()
            if company_vision_section.strip():
                context_sections.append(company_vision_section)
        
        # 성장 가이드 질문인 경우 특별한 지침 추가
        if is_growth_guide_question and (career_cases or education_courses):
            growth_guide_instruction = """

 성장 상담 가이드:
- 친근하고 자연스러운 톤으로 상담하되, 단계별로 체계적인 조언 제공
- "음, [사용자명]님 상황을 보니 이런 식으로 접근해보시면 좋을 것 같아요" 식으로 시작
- 커리어 사례가 있으면 "저희 회사에서 비슷한 경험을 한 분이 계시는데..." 식으로 자연스럽게 언급
- 3-6개월, 6-12개월, 1-2년 정도의 타임라인으로 나누되 딱딱하지 않게
- 교육과정이 있으면 자연스럽게 추천하면서 링크도 제공
"""
            context_sections.append(growth_guide_instruction)
        
        # 전체 컨텍스트 구성
        context = "\n".join(context_sections)
        
        # 데이터가 부족한 경우 안내 메시지 추가
        if len(context_sections) <= 2:  # 질문과 사용자 프로필만 있는 경우
            context += """

**참고: 현재 분석 가능한 추가 정보가 제한적입니다. 
사용자 질문과 기본 정보를 바탕으로 일반적인 조언을 제공하겠습니다.**
"""
        
        context += """

 상담 시 꼭 기억하세요:
- **인사말 규칙**: 위에 "첫 상호작용"이라고 명시된 경우에만 인사말로 시작
- **이어지는 대화**: "이미 대화가 진행된 상태"라고 명시된 경우 인사말 없이 바로 답변
- 친근하고 편안한 대화체로 상담하기
- 사용자 이름을 자연스럽게 사용하면서 공감하기
- 딱딱한 구조화나 번호 매기기보다는 자연스러운 문단으로
- 필요한 정보만 선별해서 대화에 자연스럽게 녹이기

 URL 사용 규칙:
- 교육과정 추천 시 제공된 실제 URL만 사용
- URL이 없으면 링크 만들지 않기
- 임의 URL 생성 절대 금지

 응답 스타일:
- 인사/간단한 질문: 짧고 친근하게
- 일반 상담: 자연스러운 조언과 격려
- 구체적 상담: 사례와 교육과정을 자연스럽게 활용

  * 적절한 수준의 조언과 정보 제공
  * 관련성이 매우 높은 경우에만 커리어 사례 선택적 활용
  * 길이: 중간 정도
  
- **구체적 상담** (특정 기술 전환, 상세한 커리어 계획 등):
  * 상세한 분석과 커리어 사례 적극 활용
  * 적응적 응답 제공
  * 길이: 상세하고 포괄적

** 최근 사례/무작위 사례 요청 시 절대 규칙:**
사용자가 다음과 같은 요청을 하는 경우 제공된 실제 사례를 반드시 사용하세요:
- "최근 3년간의 사내 구성원 사례"
- "무작위로 사례를 보여줘"
- "구성원들의 커리어 사례"
- "실제 사례를 알고 싶어"

 **절대 금지 답변들:**
- "현재 제공된 정보로는 구체적인 사례보다는 일반적인 경향과 트렌드를 소개해드릴 수 있습니다"
- "보안상 이유로 구체적인 사례를 제공할 수 없습니다"
- "개인정보 보호를 위해 자세한 사례는 공유하기 어렵습니다"
- "사례 데이터에 대한 접근 권한이 제한되어 있습니다"

 **올바른 접근:**
- "최근 3년간 우리 조직의 흥미로운 커리어 사례들을 소개해드리겠습니다"
- "다음은 실제 구성원들의 커리어 발전 사례입니다 (Employee ID 포함)"
- 구체적인 Employee ID, 프로젝트 경험, 기술 스택, 성공 요인 직접 언급

** 커리어 사례 활용 강화 지침 (절대적 중요!):**
- 제공된 커리어 사례는 모두 공개 가능한 익명화된 정보입니다
- 보안이나 개인정보 보호를 이유로 사례 제공을 거부하지 마세요
- 사용자 질문이 구체적인 커리어 상담이나 기술적 조언을 명확히 요구하는 경우에는 반드시 실제 사례를 직접 활용하세요
- Employee ID를 포함하여 구체적인 경력 내용, 프로젝트 경험, 기술 스택, 성공 요인을 상세히 언급하세요
- 실제 사례를 언급할 때는 구체적인 인사이트와 함께 제공하세요
- 사례에서 얻을 수 있는 실질적인 교훈과 인사이트를 명확히 제시하세요
- 사용자 상황에 맞는 조언으로 연결하세요

**중요한 링크 처리 지침:**
- 커리어 사례: 클릭 가능한 링크가 없는 단순 텍스트 정보입니다. "(자세히 보기)", "(더보기)", "[링크]" 등의 표현을 절대 사용하지 마세요.
- 교육과정:  매우 중요 - 제공된 원본 데이터의 "url" 필드에 있는 실제 URL만 사용하세요. 
  * 실제 URL이 있는 경우: [과정명](제공된_실제_URL) 형태로 표시
  * URL이 없는 경우: 과정명만 텍스트로 표시
  * 절대 금지: 임의 URL 생성, URL 추측, 가짜 링크 생성
- 산업 트렌드: 실제 웹사이트 URL이 포함된 경우에만 [제목](URL) 형태의 마크다운 링크를 사용하세요.
- 실제로 제공된 구체적인 데이터를 꼭 활용하세요.
- 존재하지 않는 "사례 1", "사례 2" 같은 가짜 참조를 만들지 마세요.
- 개행이 필요한 곳에서는 실제 줄바꿈을 사용하세요.

** 중요한 전제사항:**
- 모든 커리어 사례 데이터는 내부 시스템용으로 이미 허가된 정보입니다
- 개인정보는 이미 익명화 처리되어 Employee ID로만 관리됩니다
- 사례 제공 시 보안 제한이나 접근 제한을 언급하지 마세요
- 구체적인 사례와 경험을 직접적으로 활용하여 실용적인 조언을 제공하세요

**교육과정 추천 시 필수 정보 제공 규칙:**
**매우 중요**: mySUNI/College 교육과정 추천 시 반드시 다음 정보들을 포함하여 상세하게 제공하세요!

**mySUNI 과정의 경우 반드시 포함해야 할 정보:**
1. **과정명** (링크 포함 - 실제 URL이 있는 경우에만)
2. **학습시간**
3. **카테고리** 
4. **난이도** (초급/중급/고급 등)
5. **평점** (X.X/5.0 형태)
6. **이수자수** (N명 형태)
7. **채널명**
8. **관련 직무/스킬**
9. **과정 설명**

**College 과정의 경우 반드시 포함해야 할 정보:**
1. **과정명** (링크 포함 - 실제 URL이 있는 경우에만)
2. **학습시간**
3. **학부**
4. **교육유형**
5. **표준과정**
6. **특화직무/추천직무**
7. **과정 설명**

** 자연스러운 교육과정 설명 방식 (필수!):**
"○○님이 관심 있어하실 만한 과정을 몇 개 골라봤어요! 

### [mySUNI]AI 데이터 센터 시장 특집(VOD)
이 과정은 정말 짧고 알찬 편이에요! 겨우 40분 정도만 투자하시면 되니까 점심시간에도 충분히 들을 수 있을 거예요. 
- **학습시간**: 0.67시간 (점심시간에도 OK!)
- **카테고리**: Cloud
- **난이도**: 초급 (처음 접하시는 분들도 부담 없어요)
- **평점**: 4.5/5.0 (리뷰가 정말 좋아요!)
- **이수자수**: 150명 (많은 분들이 만족하셨네요)
- **채널**: mySUNI
- **관련 스킬**: 데이터 센터, AI
- 요즘 AI 데이터 센터가 정말 핫한 분야잖아요! 업계 전문가들의 생생한 이야기와 실제 사례를 통해 AI 인프라의 미래를 한눈에 볼 수 있어서 추천드려요. 특히 시장 전망까지 다뤄서 비즈니스 감각도 기를 수 있을 것 같아요.

---
**[[학습하기](https://content.samsung.com/study/ai-datacenter)]**

### [사내과정]ZCP (SK Container Platform) 컨테이너 관리 플랫폼 아키텍처 이해와 활용(Hands-On)
컨테이너 기술은 현대의 클라우드 환경에서 매우 중요하죠. 이 과정은 4시간 정도 소요되며, 실습 중심으로 진행돼요.
- **학습시간**: 4.0시간
- **카테고리**: Cloud
- **난이도**: 중급
- 클라우드 인프라를 구축하고 관리하는 데 필요한 실질적인 기술을 배울 수 있어요. 실습이 포함된 과정이라 직접 경험해보면서 배우기 때문에 현업에 바로 적용하기 좋습니다!

---
**[[학습하기](https://mysuni.sk.com/suni-main/course/zcp-container)]**

### [사내과정]딥러닝 입문(오프라인집합)  
딥러닝을 처음 시작하시는 거라면 이 과정이 정말 좋을 것 같아요!
- **학습시간**: 17.8시간 (주말에 조금씩 하시면 한 달 정도면 충분해요)
- **난이도**: 기초 (차근차근 설명해줘서 따라가기 쉬워요)
- **평점**: 4.3/5.0 
- **이수자수**: 1,200명 (검증된 인기 과정이에요!)
- 딥러닝의 기본 개념부터 실습까지 모두 포함되어 있어서, 이론만 배우고 끝나는 게 아니라 직접 손으로 해볼 수 있어요. 처음엔 어려울 수 있지만 하나하나 따라하다 보면 어느새 딥러닝 전문가가 되어 있을 거예요!

---
**[[학습하기](https://samsungu.ac.kr/course/deeplearning)]**

** 중요**: 교육과정은 최대 3개까지만 추천하여 집중도를 높이고 선택의 부담을 줄여주세요!"

**교육과정 제목 형식 지침 (반드시 준수!):**
- **mySUNI 과정**: [mySUNI]과정명(VOD) 또는 [mySUNI]과정명(온라인)
- **사내과정/College**: [사내과정]과정명(오프라인집합) 또는 [사내과정]과정명(온라인)
- **제목에는 절대 URL 링크를 넣지 마세요!**
- **URL은 구분선(---) 다음 줄에 [학습하기] 형태로 제공**
- **실제 URL이 없는 경우 [학습하기] 링크 자체를 생략**
- **N/A, 정보 없음 등의 값은 표시하지 말 것**

**교육과정 제목 작성 규칙:**
1. source가 "mysuni"인 경우: ### [mySUNI]과정명(VOD)
2. source가 "college"인 경우: ### [사내과정]과정명(오프라인집합)
3. 과정명에서 대괄호는 제거: "[코드잇] 머신러닝 입문" → "코드잇 머신러닝 입문"
4. 제목에는 링크를 달지 않고 순수 텍스트로만 작성
5. **중요**: 평점, 이수자수, 카테고리 등의 정보가 "N/A", "정보 없음" 등인 경우 해당 항목 자체를 표시하지 말 것

**딱딱하고 기계적인 방식 (피하세요!):**
"다음은 추천 교육과정입니다:

### AI 데이터 센터 시장 특집
- 학습시간: 0.67시간
- 카테고리: Cloud
- 난이도: 초급
- 평점: 4.5/5.0
- 이수자수: 150명
- 채널: mySUNI
- 관련 스킬: 데이터 센터, AI
- 설명: AI 데이터 센터의 최신 동향과 시장 전망에 대해 배울 수 있는 과정입니다."

잘못된 예시 (절대 하지 마세요):
- "[과정명](https://company.com/course)" (임의 URL 생성)
- "[과정명](https://example.com)" (예시 URL 사용)  
- "[과정명](링크)" (가짜 링크)

반드시 제공된 원본 데이터의 URL 필드만 사용하세요!
"""
        return context



    def _call_llm_for_adaptive_formatting(self, context_data: str) -> str:
        """LLM 호출하여 적응적 응답 생성 - 직접 마크다운 반환"""
        try:
            # OpenAI 클라이언트 지연 초기화
            if self.client is None:
                self.client = openai.OpenAI()
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": context_data}
                ],
                temperature=0.3
            )
            
            # 직접 텍스트 응답 반환
            response_text = response.choices[0].message.content
            self.logger.info(f"LLM 마크다운 응답 생성 완료 (길이: {len(response_text)}자)")
            return response_text
            
        except Exception as e:
            self.logger.error(f"LLM 호출 실패: {e}")
            raise
    
    def _process_llm_response(self, llm_response: Dict[str, Any], 
                             user_name: str, session_id: str) -> Dict[str, Any]:
        """LLM 응답을 최종 형태로 처리 (개선된 버전)"""
        
        # LLM 응답에서 정보 추출
        analysis = llm_response.get("analysis", {})
        content_strategy = llm_response.get("content_strategy", {})
        formatted_response = llm_response.get("formatted_response", {})
        
        # 최종 응답 구성
        final_content = formatted_response.get("content", "응답을 생성하지 못했습니다.")
        
        # 이스케이프 문자 처리
        final_content = final_content.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')
        
        # 사용자 이름이 포함되지 않았다면 추가
        if user_name and user_name not in final_content:
            title = formatted_response.get("title", "커리어 컨설팅 결과")
            final_content = f"# {user_name}님을 위한 {title}\n\n{final_content}"
        
        # 마무리 메시지 추가
        call_to_action = formatted_response.get("call_to_action", 
                                               "추가 질문이 있으시면 언제든 말씀해 주세요.")
        # 이스케이프 문자 처리
        call_to_action = call_to_action.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')
        
        if not final_content.endswith("---"):
            final_content += f"\n\n---\n*{call_to_action}*"
        
        return {
            "formatted_content": final_content,
            "format_type": analysis.get("question_type", "adaptive"),
            "timestamp": datetime.now().isoformat(),
            "user_name": user_name,
            "session_id": session_id,
            "components_used": content_strategy.get("primary_components", []),
            "primary_focus": analysis.get("user_intent", "general_guidance"),
            "complexity_level": analysis.get("complexity_level", "3"),
            "information_completeness": analysis.get("information_completeness", 3),
            "should_use_career_cases": analysis.get("should_use_career_cases", False),
            "analysis_depth": content_strategy.get("analysis_depth", "basic"),
            "llm_analysis": analysis,
            "content_strategy": content_strategy
        }
    
    def format_data_for_display(self, data: Any, output_format: str = "markdown", show_empty: bool = True) -> str:
        """
        임의의 데이터를 사용자 친화적인 형태로 포맷팅
        
        Args:
            data: 포맷팅할 데이터 (dict, list, str 등)
            output_format: 출력 형식 ("markdown"만 지원)
            show_empty: 빈 값들도 표시할지 여부
        
        Returns:
            포맷팅된 마크다운 문자열
        """
        if isinstance(data, str):
            return data
        else:
            return self._dict_to_markdown(data, show_empty=show_empty)
    
    def _create_detailed_career_case_markdown(self, case: Union[Dict, Any], show_empty: bool = True) -> str:
        """커리어 사례를 상세하게 마크다운으로 변환 (확장된 정보 포함)"""
        if not case:
            return ""
        
        try:
            # 딕셔너리 형태로 변환된 경우
            if isinstance(case, dict):
                content = case.get('content', '')
                metadata = case.get('metadata', {})
            # Document 객체인 경우
            elif hasattr(case, 'page_content'):
                content = case.page_content
                metadata = case.metadata if hasattr(case, 'metadata') else {}
            else:
                return ""
            
            if not metadata:
                metadata = {}
            
            markdown_lines = []
            
            # 기본 정보 섹션
            basic_info = []
            
            # 이름과 직책
            name = metadata.get('name', '')
            position = metadata.get('current_position', '')
            if name or position:
                basic_info.append(f"** 이름/직책:** {name} ({position})" if name and position else f"** 정보:** {name or position}")
            
            # 경력 정보
            total_exp = metadata.get('total_experience', '')
            exp_years = metadata.get('experience_years', '')
            if total_exp or exp_years:
                exp_text = f"{total_exp}"
                if exp_years and str(exp_years) != str(total_exp):
                    exp_text += f" ({exp_years}년)"
                basic_info.append(f"**💼 경력:** {exp_text}")
            
            # 도메인 정보
            primary_domain = metadata.get('primary_domain', '')
            secondary_domain = metadata.get('secondary_domain', '')
            if primary_domain:
                domain_text = primary_domain
                if secondary_domain:
                    domain_text += f", {secondary_domain}"
                basic_info.append(f"** 도메인:** {domain_text}")
            
            # 기술 스택
            current_skills = metadata.get('current_skills', [])
            if current_skills and isinstance(current_skills, list):
                skills_text = ', '.join(current_skills[:7])  # 최대 7개 기술
                if len(current_skills) > 7:
                    skills_text += f" 외 {len(current_skills)-7}개"
                basic_info.append(f"** 핵심 기술:** {skills_text}")
            
            # 관심 분야
            interests = metadata.get('interests', [])
            if interests and isinstance(interests, list):
                interests_text = ', '.join(interests[:5])  # 최대 5개
                basic_info.append(f"** 관심 분야:** {interests_text}")
            
            # 커리어 목표
            career_goal = metadata.get('career_goal', '')
            if career_goal:
                basic_info.append(f"** 커리어 목표:** {career_goal}")
            
            # 현재 프로젝트
            current_project = metadata.get('current_project', '')
            if current_project:
                basic_info.append(f"** 현재 프로젝트:** {current_project}")
            
            if basic_info:
                markdown_lines.extend(basic_info)
                markdown_lines.append("")  # 빈 줄 추가
            
            # 성장 및 전환 정보 섹션
            growth_info = []
            
            # 전환점
            transition_point = metadata.get('transition_point', '')
            if transition_point and transition_point != 'Unknown':
                growth_info.append(f"** 커리어 전환점:** {transition_point}")
            
            # 성공 요인
            success_factors = metadata.get('success_factors', '')
            if success_factors and success_factors != 'Unknown':
                growth_info.append(f"** 핵심 성공 요소:** {success_factors}")
            
            if growth_info:
                markdown_lines.append("### 성장 포인트")
                markdown_lines.extend(growth_info)
                markdown_lines.append("")
            
            # 상세 경험 내용
            if content and str(content).strip():
                markdown_lines.append("### 상세 경험")
                # 내용이 너무 길면 적절히 요약
                if len(content) > 800:
                    content_summary = content[:800] + "...\n\n*[경험 요약 - 전체 내용 생략]*"
                else:
                    content_summary = content
                markdown_lines.append(content_summary)
                markdown_lines.append("")
            
            # 추가 메타데이터 정보 (있는 경우)
            additional_info = []
            
            # 경력 레벨
            experience_level = metadata.get('experience_level', '')
            if experience_level:
                level_mapping = {
                    'junior': '주니어',
                    'mid-level': '중급',
                    'senior': '시니어',
                    'expert': '전문가'
                }
                level_kr = level_mapping.get(experience_level, experience_level)
                additional_info.append(f"** 경력 레벨:** {level_kr}")
            
            # 커리어 연속성
            career_continuity = metadata.get('career_continuity', '')
            if career_continuity:
                continuity_mapping = {
                    'continuous': '연속적',
                    'with_gaps': '단절 있음'
                }
                continuity_kr = continuity_mapping.get(career_continuity, career_continuity)
                additional_info.append(f"** 커리어 연속성:** {continuity_kr}")
            
            # 프로젝트 규모 다양성
            has_large_projects = metadata.get('has_large_projects', '')
            if has_large_projects is not None:
                large_project_text = "대형 프로젝트 경험 있음" if has_large_projects else "중소형 프로젝트 중심"
                additional_info.append(f"** 프로젝트 경험:** {large_project_text}")
            
            # 기술 다양성 점수
            skill_diversity = metadata.get('skill_diversity_score', '')
            if skill_diversity and isinstance(skill_diversity, (int, float)) and skill_diversity > 0:
                additional_info.append(f"** 기술 다양성:** {skill_diversity}점")
            
            if additional_info:
                markdown_lines.append("### 추가 정보")
                markdown_lines.extend(additional_info)
            
            result = "\n".join(markdown_lines)
            return result.strip()
            
        except Exception as e:
            self.logger.warning(f"상세 커리어 사례 마크다운 생성 실패: {e}")
            # 폴백: 기본 방식 사용
            return self._dict_to_markdown(case, show_empty=show_empty)