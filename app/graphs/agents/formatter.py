# formatter.py

from typing import Dict, Any, Optional, List, Union
import logging
from datetime import datetime
import openai
import os
import json
import markdown
import re

class ResponseFormattingAgent:
    """LLM 기반 적응적 응답 포맷팅 에이전트 - AI가 질문 유형과 컨텍스트를 분석하여 최적화된 응답 생성"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.client = None  # OpenAI 클라이언트를 지연 초기화
        
        # LLM을 위한 시스템 프롬프트
        self.system_prompt = """
당신은 G.Navi AI 커리어 컨설팅 시스템의 응답 포맷팅 전문가입니다.
사용자의 질문과 수집된 데이터를 분석하여 가장 적합한 형태로 응답을 구성해야 합니다.

**역할:**
1. 사용자 질문의 의도와 성격을 분석
2. 사용자에게 가장 유용한 정보 조합 결정
3. 응답 구조와 내용의 우선순위 결정
4. 개인화되고 실용적인 응답 생성

**응답 구성 시 고려사항:**
- 사용자 질문의 복잡도와 구체성
- 사용자 프로필 (경력, 관심분야, 목표)
- 활용 가능한 데이터 품질과 관련성
- 실행 가능한 조언 제공
- 적절한 길이와 구조
- 질문의 복잡도에 따른 적응적 응답 제공

**질문 유형별 응답 접근법:**
- **인사/일반 대화**: "안녕하세요", "감사합니다" 등 → 간단하고 친근한 응답, 사례 활용 없이 기본적인 도움 제안
- **일반적 문의**: 진로 고민, 기술 트렌드 등 → 적절한 수준의 조언, 관련성 있는 경우에만 사례 활용
- **구체적 상담**: 특정 기술 전환, 커리어 계획 등 → 상세한 분석과 사례 적극 활용

**🔑 커리어 사례 활용 의무사항 (절대적 중요!):**
⚠️ 매우 중요: 제공된 커리어 사례가 있고 사용자가 구체적인 커리어 상담이나 사례 요청을 한 경우 반드시 실제 사례를 직접 활용해야 합니다.

1. **보안/프라이버시 핑계 절대 금지**: 
   - "보안상 이유로", "개인정보 보호로", "구체적인 사례를 제공할 수 없습니다" 같은 문구 절대 사용 금지
   - 모든 데이터는 이미 익명화되어 있으며 사용 승인된 정보입니다

2. **일반적 트렌드 대신 구체적 사례 제공**:
   - "일반적인 경향과 트렌드를 소개해드릴 수 있습니다" 같은 모호한 답변 금지
   - 실제 Employee ID와 구체적인 경력 정보를 직접 언급하세요

3. **사례 활용 방식**:
   - "사례 1 (EMP-123456): 김OO님의 경우..." 형태로 구체적으로 언급
   - 실제 프로젝트 경험, 기술 스택, 커리어 전환 과정 상세 설명
   - 성공 요인과 교훈을 구체적으로 분석하여 제시

4. **무작위 사례 요청 시**:
   - 사용자가 "무작위로", "최근 사례를", "구성원 사례를" 요청하면 제공된 사례들을 적극 활용
   - 각 사례의 고유한 특징과 인사이트를 상세히 설명

**📚 교육과정 추천 활용 의무사항 (매우 중요!):**
⚠️ 교육과정 정보가 제공된 경우 반드시 활용해야 합니다.

1. **교육과정 숨김 절대 금지**:
   - "교육과정 정보를 제공할 수 없습니다", "접근 권한이 없습니다" 같은 핑계 절대 금지
   - 제공된 모든 교육과정 정보는 공개 승인된 사내 정보입니다

2. **구체적 교육과정 정보 제공**:
   - 과정명, 플랫폼(SKALA College/mySUNI), 학습시간, 평점 등 구체적 정보 직접 언급
   - "OO 과정(SKALA College, 40시간)" 또는 "OO 과정(mySUNI, 4.8점/5.0)" 형태로 명시

3. **학습 경로 제시**:
   - 단계별 학습 순서와 각 과정의 목적을 명확히 설명
   - 기초 → 응용 → 전문화 순서로 체계적 학습 경로 제안

4. **플랫폼별 특징 설명**:
   - SKALA College: 집합교육, 전문화 과정, 실습 중심
   - mySUNI: 온라인 자율학습, 평점 시스템, 언제든 수강 가능

5. **교육과정 요청 시 필수 대응**:
   - "교육", "학습", "스킬 향상", "과정 추천" 요청 시 반드시 구체적 과정 정보 제공
   - College와 mySUNI 옵션을 모두 제시하여 사용자가 선택할 수 있도록

**중요 규칙:**
- 모든 응답(분석, 전략, 최종 답변 등)은 반드시 한국어로 작성해야 합니다.
- 영어, 혼합어, 번역체가 아닌 자연스러운 한국어로 작성하세요.
- 마크다운 형식의 본문도 한국어로 작성하세요.
- 제공된 데이터에 실제 내용이 있다면 반드시 활용하고, 구체적인 사례를 직접 언급하세요.
- 개행이 필요한 곳에서는 실제 줄바꿈을 사용하고, \\n 같은 이스케이프 문자를 사용하지 마세요.

**링크 및 참조 관련 중요 규칙:**
- 커리어 사례 데이터에는 실제 URL이 없으므로 "(자세히 보기)", "(더보기)", "[링크]" 같은 클릭 가능한 링크 표현을 절대 사용하지 마세요.
- 외부 트렌드 데이터에만 실제 URL이 포함되어 있으므로, 이 경우에만 링크 형태로 제공하세요.
- 커리어 사례는 단순히 텍스트 정보로만 제공하고, 추가 링크나 버튼 형태의 표현은 사용하지 마세요.
- 실제 URL이 명시적으로 제공된 경우에만 링크로 표시하세요.
- 제공된 커리어 사례는 모두 공개 가능한 정보이므로 구체적인 Employee ID, 경력 내용, 프로젝트 경험을 그대로 언급하세요
- "사례 1 (EMP-123456)" 형태로 구체적인 직원 ID와 함께 언급하되, 실제 경험과 성과를 상세히 설명하세요
- 실제 사례를 언급할 때는 구체적인 기술 스택, 프로젝트 내용, 커리어 전환 과정, 성공 요인을 상세히 제공하세요

**중요 규칙:**
- 모든 응답(분석, 전략, 최종 답변 등)은 반드시 한국어로 작성해야 합니다.
- 영어, 혼합어, 번역체가 아닌 자연스러운 한국어로 작성하세요.
- 마크다운 형식의 본문도 한국어로 작성하세요.
- 제공된 데이터에 실제 내용이 있다면 반드시 활용하고, 구체적인 사례를 직접 언급하세요.
- 개행이 필요한 곳에서는 실제 줄바꿈을 사용하고, \\n 같은 이스케이프 문자를 사용하지 마세요.

**링크 및 참조 관련 중요 규칙:**
- 커리어 사례 데이터에는 실제 URL이 없으므로 "(자세히 보기)", "(더보기)", "[링크]" 같은 클릭 가능한 링크 표현을 절대 사용하지 마세요.
- 외부 트렌드 데이터에만 실제 URL이 포함되어 있으므로, 이 경우에만 링크 형태로 제공하세요.
- 커리어 사례는 단순히 텍스트 정보로만 제공하고, 추가 링크나 버튼 형태의 표현은 사용하지 마세요.
- 실제 URL이 명시적으로 제공된 경우에만 링크로 표시하세요.

**중요: 응답 형식**
반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트나 설명은 포함하지 마세요.
JSON 앞뒤에 ```json 같은 마크다운 코드 블록 표시를 사용하지 마세요.
순수한 JSON만 반환하세요.

{
    "analysis": {
        "question_type": "질문 유형 (greeting/general_inquiry/specific_consultation/technical_advice)",
        "user_intent": "사용자 의도",
        "complexity_level": "복잡도 (1-5)",
        "key_focus_areas": ["주요 초점 영역들"],
        "information_completeness": "제공된 정보의 충분성 (1-5)",
        "should_use_career_cases": "커리어 사례 활용 여부 (true/false)"
    },
    "content_strategy": {
        "primary_components": ["사용할 주요 데이터 컴포넌트"],
        "response_structure": ["응답 구조 섹션들"],
        "tone_and_style": "응답 톤과 스타일 (casual/professional/detailed)",
        "length_target": "목표 응답 길이 (brief/medium/comprehensive)",
        "analysis_depth": "분석 깊이 수준 (basic/intermediate/advanced)"
    },
    "formatted_response": {
        "title": "응답 제목",
        "content": "마크다운 형식의 응답 내용",
        "call_to_action": "추가 행동 유도 메시지",
        "additional_questions": ["더 나은 분석을 위한 추가 질문들 (선택사항)"]
    }
}
"""

    def _dict_to_markdown(self, data: Union[Dict, List, Any], depth: int = 0, show_empty: bool = True) -> str:
        """dict, list 등의 JSON 타입을 사람이 읽기 쉬운 마크다운으로 변환"""
        indent = "  " * depth
        
        if isinstance(data, dict):
            if not data:
                return "*(내용 없음)*" if show_empty else ""
            
            markdown_lines = []
            for key, value in data.items():
                # 키 정리 (한글 키 우선, 영문 키는 한글로 번역 시도)
                display_key = self._format_key_name(key)
                
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
    
    def _format_trend_with_url(self, trend: Dict[str, Any]) -> str:
        """외부 트렌드 데이터를 URL 포함하여 포맷팅"""
        if not trend:
            return ""
        
        # URL이 있는지 확인
        url = trend.get('url', trend.get('link', trend.get('source', '')))
        title = trend.get('title', trend.get('name', ''))
        content = trend.get('content', trend.get('summary', trend.get('description', '')))
        
        result_parts = []
        
        if title:
            if url and url.startswith('http'):
                # 실제 URL이 있는 경우에만 링크로 표시
                result_parts.append(f"**제목**: [{title}]({url})")
            else:
                # URL이 없으면 일반 텍스트로
                result_parts.append(f"**제목**: {title}")
        
        if content:
            # 내용이 너무 길면 요약
            if len(content) > 200:
                content = f"{content[:200]}..."
            result_parts.append(f"**내용**: {content}")
        
        # 기타 의미있는 필드들 추가
        for key, value in trend.items():
            if key not in ['url', 'link', 'source', 'title', 'name', 'content', 'summary', 'description']:
                display_key = self._format_key_name(key)
                formatted_value = self._format_value(value)
                if formatted_value:
                    result_parts.append(f"**{display_key}**: {formatted_value}")
        
        return "\n".join(result_parts) if result_parts else ""
    
    # formatter.py의 간소화된 필터링 메서드
    def _filter_meaningful_career_cases(self, career_cases: List[Any]) -> List[Any]:
        """커리어 사례 필터링 - 완화된 버전 (빈 내용이 아니면 모두 포함)"""
        if not career_cases:
            return []
        
        meaningful_cases = []
        
        for case in career_cases:
            # 이미 딕셔너리로 변환된 경우
            if isinstance(case, dict) and 'content' in case:
                content = case.get('content', '')
                # 필터링 기준을 매우 완화 - 빈 문자열이 아니면 모두 포함
                if content and str(content).strip():
                    meaningful_cases.append(case)
            
            # Document 객체인 경우 (fallback)
            elif hasattr(case, 'page_content'):
                content = case.page_content
                # 빈 내용이 아니면 모두 포함
                if content and str(content).strip():
                    meaningful_cases.append({
                        'content': content,
                        'metadata': case.metadata if hasattr(case, 'metadata') else {},
                        'source': 'document_object'
                    })
        
        self.logger.info(f"커리어 사례 필터링: {len(meaningful_cases)}개 (원본: {len(career_cases)}개)")
        return meaningful_cases

    def _filter_meaningful_trends(self, external_trends: List[Dict]) -> List[Dict]:
        """의미 있는 외부 트렌드만 필터링"""
        if not external_trends:
            return []
        
        meaningful_trends = []
        for trend in external_trends:
            if not isinstance(trend, dict):
                continue
                
            # 필수 필드가 있는지 확인
            has_title = trend.get('title') and not self._is_empty_value(trend.get('title'))
            has_content = (trend.get('content') or trend.get('summary') or 
                          trend.get('description')) and not self._is_empty_value(
                              trend.get('content') or trend.get('summary') or trend.get('description'))
            
            if has_title or has_content:
                meaningful_trends.append(trend)
        
        self.logger.info(f"외부 트렌드 필터링: {len(meaningful_trends)}개 (원본: {len(external_trends)}개)")
        return meaningful_trends

    def _filter_meaningful_chat_history(self, chat_history: List[Any]) -> List[Any]:
        """의미 있는 대화 히스토리만 필터링 (완화된 기준)"""
        if not chat_history:
            return []
        
        meaningful_history = []
        for chat in chat_history:
            if not isinstance(chat, dict):
                continue
                
            # 기본적인 세션 정보가 있으면 포함 (매우 완화된 기준)
            has_session_id = chat.get('session_id') and not self._is_empty_value(chat.get('session_id'))
            has_user_id = chat.get('user_id') and not self._is_empty_value(chat.get('user_id'))
            
            # messages 배열이 있고 비어있지 않은지 확인
            messages = chat.get('messages', [])
            has_messages = isinstance(messages, list) and len(messages) > 0
            
            # messages 내용 확인
            has_meaningful_messages = False
            if has_messages:
                for message in messages:
                    if isinstance(message, dict):
                        content = message.get('content', '')
                        role = message.get('role', '')
                        # 내용이 있고 역할이 있으면 의미있는 메시지로 간주
                        if content and not self._is_empty_value(content) and role:
                            has_meaningful_messages = True
                            break
            
            # 레거시 format 지원 (question/response 필드)
            has_question = chat.get('question') and not self._is_empty_value(chat.get('question'))
            has_response = chat.get('response') and not self._is_empty_value(chat.get('response'))
            
            # 다음 중 하나라도 만족하면 포함 (매우 관대한 기준)
            if (has_session_id or has_user_id or has_meaningful_messages or 
                has_question or has_response):
                meaningful_history.append(chat)
        
        self.logger.info(f"대화 히스토리 필터링 : {len(meaningful_history)}개 (원본: {len(chat_history)}개)")
        return meaningful_history
    
    def _has_meaningful_data(self, data: Union[Dict, List, Any]) -> bool:
        """데이터에 의미있는 내용이 있는지 확인 (개선된 버전)"""
        if not data:
            return False
        
        if isinstance(data, dict):
            # 오류 상태인 경우 의미 없는 데이터로 간주
            if data.get("error"):
                return False
                
            for key, value in data.items():
                if key == "error":  # 에러 필드는 건너뛰기
                    continue
                    
                if not self._is_empty_value(value):
                    if isinstance(value, (dict, list)):
                        if self._has_meaningful_data(value):
                            return True
                    else:
                        # 문자열이 충분히 긴지 확인을 완화 (1자 이상이면 OK)
                        if isinstance(value, str) and len(value.strip()) >= 1:
                            return True
                        elif not isinstance(value, str):
                            return True
            return False
        
        elif isinstance(data, list):
            for item in data:
                if not self._is_empty_value(item):
                    if isinstance(item, (dict, list)):
                        if self._has_meaningful_data(item):
                            return True
                    else:
                        return True
            return False
        
        else:
            return not self._is_empty_value(data)
    
    def _is_empty_value(self, value: Any) -> bool:
        """값이 비어있는지 확인 (개선된 버전)"""
        if value is None:
            return True
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return True
            # 의미 없는 값들 확인
            empty_indicators = ['*정보 없음*', '정보 없음', '', 'N/A', 'n/a', 'null', 
                               'undefined', 'None', '빈 목록', '내용 없음', 'no data']
            if stripped.lower() in [indicator.lower() for indicator in empty_indicators]:
                return True
            # 너무 짧은 문자열 필터링을 완화 (1자 이상이면 OK)
            if len(stripped) < 1:
                return True
        if isinstance(value, (list, dict)) and not value:
            return True
        return False
    
    def _create_dict_summary(self, data: dict) -> str:
        """딕셔너리를 간단한 요약 문자열로 변환"""
        if not data:
            return ""
        
        # 모든 필드 포함
        items = []
        for key, value in data.items():
            display_key = self._format_key_name(key)
            formatted_value = self._format_value(value)
            if formatted_value:
                items.append(f"{display_key}: {formatted_value}")
        
        return " | ".join(items) if items else ""
    
    def _format_key_name(self, key: str) -> str:
        """키 이름을 사용자 친화적으로 포맷팅"""
        # 일반적인 영문 키를 한글로 매핑 (확장된 버전)
        key_mapping = {
            'name': '이름',
            'title': '제목',
            'content': '내용',
            'summary': '요약',
            'description': '설명',
            'type': '유형',
            'status': '상태',
            'date': '날짜',
            'created_at': '생성일',
            'updated_at': '수정일',
            'user_id': '사용자 ID',
            'session_id': '세션 ID',
            'recommendations': '추천사항',
            'analysis': '분석',
            'complexity': '복잡도',
            'keywords': '키워드',
            'interests': '관심분야',
            'experience': '경험',
            'skills': '기술',
            'career_goal': '커리어 목표',
            'current_job': '현재 직무',
            'company': '회사',
            'industry': '산업',
            'salary': '연봉',
            'location': '위치',
            'position': '직위',
            'domain': '분야',
            'transition_point': '전환 시점',
            'success_factors': '성공 요인',
            'model_used': '사용 모델',
            'timestamp': '생성 시간',
            'recommendation_content': '추천 내용',
            'career_cases_summary': '커리어 사례 요약',
            'source_trends': '트렌드 소스 수',
            'confidence_score': '신뢰도',
            'has_career_references': '커리어 참고 자료 여부',
            'experience_years': '경력 년수',
            'age': '나이',
            'education': '학력',
            'certification': '자격증',
            'project': '프로젝트',
            'achievement': '성과',
            'goal': '목표'
        }
        
        return key_mapping.get(key.lower(), key)
    
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
    
    def _markdown_to_html(self, markdown_text: str) -> str:
        """마크다운 텍스트를 HTML로 변환"""
        try:
            # 이스케이프 문자 처리
            processed_text = markdown_text.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')
            
            # markdown 라이브러리를 사용하여 HTML 변환
            html = markdown.markdown(
                processed_text,
                extensions=['extra', 'codehilite', 'toc'],
                extension_configs={
                    'codehilite': {
                        'css_class': 'highlight'
                    }
                }
            )
            return html
        except Exception as e:
            self.logger.warning(f"마크다운 to HTML 변환 실패: {e}")
            # 폴백: 기본 HTML 태그로 변환
            return self._simple_markdown_to_html(markdown_text)
    
    def _simple_markdown_to_html(self, text: str) -> str:
        """간단한 마크다운 to HTML 변환 (폴백용)"""
        # 이스케이프 문자 처리
        html = text.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')
        
        # 기본적인 마크다운 요소들만 변환
        # 헤더 변환
        html = re.sub(r'^### (.*$)', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.*$)', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.*$)', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        
        # 굵은 글씨 변환
        html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
        
        # 기울임 변환
        html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)
        
        # 리스트 변환 (간단한 버전)
        lines = html.split('\n')
        in_list = False
        result_lines = []
        
        for line in lines:
            if line.strip().startswith('- '):
                if not in_list:
                    result_lines.append('<ul>')
                    in_list = True
                item_text = line.strip()[2:]
                result_lines.append(f'<li>{item_text}</li>')
            else:
                if in_list:
                    result_lines.append('</ul>')
                    in_list = False
                result_lines.append(line)
        
        if in_list:
            result_lines.append('</ul>')
        
        # 줄바꿈 처리 개선
        html = '\n'.join(result_lines)
        # 빈 줄은 문단 분리로, 단일 줄바꿈은 br 태그로
        html = re.sub(r'\n\s*\n', '</p><p>', html)
        html = html.replace('\n', '<br>')
        html = f'<p>{html}</p>'
        
        # 빈 문단 제거
        html = re.sub(r'<p>\s*</p>', '', html)
        
        return html
    
    def _convert_data_to_html(self, data: Any) -> str:
        """입력 데이터를 타입에 따라 적절한 HTML로 변환"""
        if isinstance(data, str):
            # 문자열인 경우 마크다운으로 가정하고 HTML 변환
            return self._markdown_to_html(data)
        elif isinstance(data, (dict, list)):
            # dict/list인 경우 마크다운으로 변환 후 HTML 변환
            markdown_text = self._dict_to_markdown(data)
            return self._markdown_to_html(markdown_text)
        else:
            # 기타 타입은 문자열로 변환 후 HTML 변환
            text = self._format_value(data)
            return self._markdown_to_html(text)

    def format_adaptive_response(self,
                                user_question: str,
                                state: Dict[str, Any]) -> Dict[str, Any]:
        """LLM 기반 적응적 응답 포맷팅 - AI가 질문 분석부터 응답 구성까지 전체를 담당"""
        self.logger.info("LLM 기반 적응적 응답 포맷팅 시작")
        
        try:
            # GNaviState에서 데이터 추출 (추천 생성 단계 제거)
            intent_analysis = state.get("intent_analysis", {})
            user_data = state.get("user_data", {})
            career_cases = state.get("career_cases", [])
            external_trends = state.get("external_trends", [])
            chat_history = state.get("chat_history_results", [])
            education_courses = state.get("education_courses", {})  # 교육과정 정보 추가
            
            # 사용자 정보 추출
            user_name = user_data.get('name', '님')
            session_id = user_data.get('conversationId', '')
            
            # LLM을 위한 컨텍스트 구성
            context_data = self._prepare_context_for_llm(
                user_question, intent_analysis, 
                user_data, career_cases, external_trends, chat_history, education_courses
            )
            
            # LLM 호출하여 적응적 응답 생성
            llm_response = self._call_llm_for_adaptive_formatting(context_data)
            
            # LLM 응답 파싱 및 최종 형태로 변환
            formatted_result = self._process_llm_response(
                llm_response, user_name, session_id
            )
            
            # 응답 내용을 HTML로 변환
            formatted_result["formatted_content_html"] = self._convert_data_to_html(
                formatted_result.get("formatted_content", "")
            )
            
            self.logger.info(f"LLM 기반 응답 포맷팅 완료: {formatted_result.get('format_type', 'adaptive')}")
            return formatted_result
            
        except Exception as e:
            self.logger.error(f"LLM 기반 응답 포맷팅 실패: {e}")
            # 폴백: 간단한 응답 생성
            return self._create_fallback_response(user_question, user_data)
    
    def _prepare_context_for_llm(self, user_question: str, intent_analysis: Dict[str, Any],
                                user_data: Dict[str, Any],
                                career_cases: List[Any], external_trends: List[Dict],
                                chat_history: List[Any], education_courses: Dict[str, Any] = None) -> str:
        """LLM을 위한 컨텍스트 데이터 준비 (빈 데이터 필터링 개선)"""
        
        context_sections = []
        
        # 사용자 질문
        context_sections.append(f'사용자 질문: "{user_question}"')
        
        # 사용자 프로필 - 의미 있는 데이터만 포함
        # 새로운 JSON 구조: {name: "", projects: [...]}
        if self._has_meaningful_data(user_data):
            user_profile_md = self._dict_to_markdown(user_data, show_empty=False)
            if user_profile_md.strip():
                context_sections.append(f"""
사용자 프로필:
{user_profile_md}
""")
        
        # 의도 분석 - 의미 있는 데이터만 포함
        if self._has_meaningful_data(intent_analysis):
            # 오류가 있는 경우 제외
            if not intent_analysis.get("error"):
                intent_analysis_md = self._dict_to_markdown(intent_analysis, show_empty=False)
                if intent_analysis_md.strip():
                    context_sections.append(f"""
의도 분석 결과:
{intent_analysis_md}
""")
        
        # 추천 결과 섹션 제거 (추천 생성 단계 제거)
        
        # 커리어 사례 - 의미 있는 데이터만 포함 (상세 정보 확장)
        meaningful_career_cases = self._filter_meaningful_career_cases(career_cases)
        if meaningful_career_cases:
            career_section = "💼 **실제 사내 커리어 사례 (사용 필수!)**:\n"
            career_section += "**⚠️ 중요 사항: 다음 사례들은 모두 실제 익명화된 사내 구성원들의 커리어 정보입니다.**\n"
            career_section += "**사용자가 사례를 요청하거나 구체적인 커리어 상담을 하는 경우 반드시 아래 사례들을 직접 활용하세요!**\n\n"
            
            added_cases = 0
            for i, case in enumerate(meaningful_career_cases[:5]):  # 최대 5개 사례 표시
                case_md = self._create_detailed_career_case_markdown(case, show_empty=False)
                if case_md.strip():  # 의미 있는 내용이 있는 경우만 추가
                    added_cases += 1
                    # Employee ID 추출 시도
                    employee_id = ""
                    employee_name = ""
                    if isinstance(case, dict):
                        metadata = case.get('metadata', {})
                        if isinstance(metadata, dict):
                            employee_id = metadata.get('employee_id', '')
                            employee_name = metadata.get('name', '')
                    
                    career_section += f"\n### 🎯 **사례 {added_cases}: {employee_name if employee_name else '익명'} {f'({employee_id})' if employee_id else ''}**\n{case_md}\n"
            
            # 실제로 추가된 사례가 있는 경우만 컨텍스트에 포함
            if added_cases > 0:
                career_section += "\n**🚨 절대적 사례 활용 규칙 (매우 중요!):**\n"
                career_section += "1. **사례 숨김 금지**: '보안상 이유로', '개인정보 보호로', '구체적인 사례를 제공할 수 없습니다' 같은 핑계 절대 금지!\n"
                career_section += "2. **모호한 답변 금지**: '일반적인 경향과 트렌드를 소개해드릴 수 있습니다' 같은 대답 절대 금지!\n"
                career_section += "3. **무작위 사례 요청 시**: 사용자가 '무작위로', '최근 사례를', '구성원 사례를' 요청하면 위 사례들을 그대로 활용하세요\n"
                career_section += "4. **구체적 활용**: Employee ID를 포함하여 구체적으로 참조하세요 (예: 사례 1 (EMP-123456))\n"
                career_section += "5. **상세 정보 제공**: 각 사례의 경력 발전 과정, 기술 스택, 프로젝트 경험, 성공 요인을 분석하여 제시하세요\n"
                career_section += "6. **실용적 연결**: 사용자의 현재 상황과 목표를 사례의 경험과 연결하여 실질적인 조언으로 활용하세요\n"
                career_section += "7. **인사이트 제공**: 사례의 전환점, 성장 포인트, 학습 경험을 구체적으로 분석하여 인사이트를 제공하세요\n"
                career_section += "8. **데이터 승인**: 이는 모든 사례는 이미 사용 승인된 데이터이며 익명화 처리된 공개 가능한 정보입니다.\n"
                context_sections.append(career_section)
        
        
        # 외부 트렌드 - 의미 있는 데이터만 포함
        meaningful_trends = self._filter_meaningful_trends(external_trends)
        if meaningful_trends:
            trend_section = "관련 산업 트렌드 (실제 웹사이트 링크 포함):\n"
            added_trends = 0
            for i, trend in enumerate(meaningful_trends[:3]):
                trend_md = self._format_trend_with_url(trend)
                if trend_md.strip():  # 의미 있는 내용이 있는 경우만 추가
                    added_trends += 1
                    trend_section += f"\n### 트렌드 정보 {added_trends}\n{trend_md}\n"
            
            # 실제로 추가된 트렌드가 있는 경우만 컨텍스트에 포함
            if added_trends > 0:
                context_sections.append(trend_section)
        
        # 교육과정 정보 - 새로 추가
        if education_courses and self._has_meaningful_education_data(education_courses):
            education_section = self._format_education_courses_for_llm(education_courses)
            if education_section.strip():
                context_sections.append(education_section)
        
        # 대화 히스토리 - 의미 있는 데이터만 포함
        meaningful_history = self._filter_meaningful_chat_history(chat_history)
        if meaningful_history:
            history_section = "📚 과거 대화 기록 (참고용):\n"
            history_section += "사용자의 이전 질문과 답변 패턴을 참고하여 개인화된 응답을 생성하세요.\n\n"
            added_history = 0
            for i, chat in enumerate(meaningful_history[:3]):  # 최근 3개로 확장
                chat_formatted = self._format_chat_history_item(chat)
                if chat_formatted.strip():
                    added_history += 1
                    history_section += f"### 💬 대화 세션 {added_history}\n{chat_formatted}\n\n"
            
            if added_history > 0:
                history_section += "**📋 대화 히스토리 활용 지침:**\n"
                history_section += "- 사용자의 이전 관심사와 질문 패턴을 파악하여 연관성 있는 조언 제공\n"
                history_section += "- 이전 대화에서 언급된 기술이나 목표와 연결하여 일관성 있는 답변 구성\n"
                history_section += "- 사용자의 발전 과정을 고려한 단계적 조언 제공\n"
                context_sections.append(history_section)
        
        # 전체 컨텍스트 구성
        context = "\n".join(context_sections)
        
        # 데이터가 부족한 경우 안내 메시지 추가
        if len(context_sections) <= 2:  # 질문과 사용자 프로필만 있는 경우
            context += """

**참고: 현재 분석 가능한 추가 정보가 제한적입니다. 
사용자 질문과 기본 정보를 바탕으로 일반적인 조언을 제공하겠습니다.**
"""
        
        context += """

위 정보를 바탕으로 사용자에게 가장 유용하고 개인화된 응답을 생성해주세요.
질문의 성격과 사용자의 상황을 고려하여 가장 적절한 정보들을 선택하고 구성해주세요.

**🎯 질문 유형별 응답 전략:**
- **인사/일반 대화** ("안녕하세요", "감사합니다", "잘 지내세요" 등): 
  * 간단하고 친근한 응답
  * 커리어 사례나 복잡한 분석 없이 기본적인 도움 제안
  * 길이: 1-3 문단 정도로 간결하게
  
- **일반적 문의** (진로 고민, 기술 트렌드 등):
  * 적절한 수준의 조언과 정보 제공
  * 관련성이 매우 높은 경우에만 커리어 사례 선택적 활용
  * 길이: 중간 정도
  
- **구체적 상담** (특정 기술 전환, 상세한 커리어 계획 등):
  * 상세한 분석과 커리어 사례 적극 활용
  * 적응적 응답 제공
  * 길이: 상세하고 포괄적

**⚠️ 최근 사례/무작위 사례 요청 시 절대 규칙:**
사용자가 다음과 같은 요청을 하는 경우 제공된 실제 사례를 반드시 사용하세요:
- "최근 3년간의 사내 구성원 사례"
- "무작위로 사례를 보여줘"
- "구성원들의 커리어 사례"
- "실제 사례를 알고 싶어"

❌ **절대 금지 답변들:**
- "현재 제공된 정보로는 구체적인 사례보다는 일반적인 경향과 트렌드를 소개해드릴 수 있습니다"
- "보안상 이유로 구체적인 사례를 제공할 수 없습니다"
- "개인정보 보호를 위해 자세한 사례는 공유하기 어렵습니다"
- "사례 데이터에 대한 접근 권한이 제한되어 있습니다"

✅ **올바른 접근:**
- "최근 3년간 우리 조직의 흥미로운 커리어 사례들을 소개해드리겠습니다"
- "다음은 실제 구성원들의 커리어 발전 사례입니다 (Employee ID 포함)"
- 구체적인 Employee ID, 프로젝트 경험, 기술 스택, 성공 요인 직접 언급

**💼 커리어 사례 활용 강화 지침 (절대적 중요!):**
- 제공된 커리어 사례는 모두 공개 가능한 익명화된 정보입니다
- 보안이나 개인정보 보호를 이유로 사례 제공을 거부하지 마세요
- 사용자 질문이 구체적인 커리어 상담이나 기술적 조언을 명확히 요구하는 경우에는 반드시 실제 사례를 직접 활용하세요
- Employee ID를 포함하여 구체적인 경력 내용, 프로젝트 경험, 기술 스택, 성공 요인을 상세히 언급하세요
- 실제 사례를 언급할 때는 구체적인 인사이트와 함께 제공하세요
- 사례에서 얻을 수 있는 실질적인 교훈과 인사이트를 명확히 제시하세요
- 사용자 상황에 맞는 조언으로 연결하세요

**중요한 링크 처리 지침:**
- 커리어 사례: 클릭 가능한 링크가 없는 단순 텍스트 정보입니다. "(자세히 보기)", "(더보기)", "[링크]" 등의 표현을 절대 사용하지 마세요.
- 산업 트렌드: 실제 웹사이트 URL이 포함된 경우에만 [제목](URL) 형태의 마크다운 링크를 사용하세요.
- 실제로 제공된 구체적인 데이터를 꼭 활용하세요.
- 존재하지 않는 "사례 1", "사례 2" 같은 가짜 참조를 만들지 마세요.
- 개행이 필요한 곳에서는 실제 줄바꿈을 사용하세요.

**💡 중요한 전제사항:**
- 모든 커리어 사례 데이터는 내부 시스템용으로 이미 허가된 정보입니다
- 개인정보는 이미 익명화 처리되어 Employee ID로만 관리됩니다
- 사례 제공 시 보안 제한이나 접근 제한을 언급하지 마세요
- 구체적인 사례와 경험을 직접적으로 활용하여 실용적인 조언을 제공하세요
"""
        return context
    
    def _call_llm_for_adaptive_formatting(self, context_data: str) -> Dict[str, Any]:
        """LLM 호출하여 적응적 응답 생성"""
        try:
            # OpenAI 클라이언트 지연 초기화
            if self.client is None:
                self.client = openai.OpenAI()
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": context_data}
                ],
                temperature=0.3
            )
            
            # JSON 응답 파싱 (개선된 버전)
            response_text = response.choices[0].message.content
            self.logger.debug(f"LLM 원본 응답 (첫 200자): {response_text[:200]}...")
            
            # JSON 추출 및 파싱 시도
            parsed_json = self._extract_and_parse_json(response_text)
            if parsed_json:
                # JSON 구조 검증
                if self._validate_json_structure(parsed_json):
                    self.logger.info("LLM JSON 응답 파싱 성공")
                    return parsed_json
                else:
                    self.logger.warning("JSON 구조가 유효하지 않음, 텍스트 추출로 전환")
            
            # JSON 파싱 실패 시 텍스트에서 정보 추출 시도
            self.logger.warning("JSON 파싱 실패, 텍스트에서 정보 추출 시도")
            return self._extract_info_from_text(response_text)
            
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
        
        # 추가 질문이 있는 경우 포함
        additional_questions = formatted_response.get("additional_questions", [])
        if additional_questions and isinstance(additional_questions, list):
            final_content += "\n\n## 🤔 더 정확한 분석을 위한 추가 질문"
            final_content += "\n더 맞춤형 조언을 제공하기 위해 다음 사항들을 알려주시면 도움이 됩니다:\n"
            for i, question in enumerate(additional_questions[:5], 1):  # 최대 5개까지만
                if question and isinstance(question, str):
                    final_content += f"{i}. {question}\n"
        
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
            "has_additional_questions": bool(formatted_response.get("additional_questions")),
            "llm_analysis": analysis,
            "content_strategy": content_strategy
        }
    
    def _create_fallback_response(self, user_question: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """LLM 실패 시 폴백 응답 생성 (개선된 버전, 추천 생성 단계 제거)"""
        user_name = user_data.get('name', '님')
        
        self.logger.info("폴백 응답 생성 중...")
        
        # 추천사항 섹션 제거
        
        # 사용자 질문 분석해서 간단한 응답 생성
        question_lower = user_question.lower()
        
        # 질문 유형별 맞춤 응답
        if any(keyword in question_lower for keyword in ['msa', '마이크로서비스', '아키텍처']):
            tech_advice = """
## 🏗️ MSA 전환 가이드

### 기술적 준비사항
- **컨테이너화**: Docker, Kubernetes 학습
- **API 설계**: RESTful API, GraphQL 이해
- **서비스 메시**: Istio, Linkerd 등 검토
- **모니터링**: 분산 추적, 로깅 시스템 구축

### 조직적 준비사항
- **팀 구조**: 각 서비스별 전담팀 구성
- **데브옵스**: CI/CD 파이프라인 고도화
- **문서화**: API 문서, 운영 가이드 체계화
"""
            recommendation_content = tech_advice
            
        elif any(keyword in question_lower for keyword in ['리더', '팀장', '리더십']):
            leadership_advice = """
## 👥 기술 리더십 개발 로드맵

### 1단계: 기술적 신뢰 구축 (1-3개월)
- 코드 리뷰 품질 향상
- 기술 블로깅, 지식 공유
- 멘토링 경험 쌓기

### 2단계: 커뮤니케이션 스킬 (3-6개월)
- 비개발자와의 소통 연습
- 프로젝트 진행상황 보고
- 갈등 조정 경험

### 3단계: 전략적 사고 (6-12개월)
- 기술 로드맵 수립
- 팀 성과 측정 및 개선
- 채용 및 온보딩 프로세스 참여
"""
            recommendation_content = leadership_advice
            
        elif any(keyword in question_lower for keyword in ['풀스택', '프론트엔드', 'frontend']):
            fullstack_advice = """
## 🌐 백엔드에서 풀스택으로 확장

### 추천 학습 순서
1. **JavaScript 생태계**: ES6+, TypeScript
2. **리액트 기초**: 컴포넌트, 상태관리, 라이프사이클
3. **CSS 프레임워크**: Tailwind CSS, Styled Components
4. **상태관리**: Redux, Zustand, React Query
5. **빌드 도구**: Vite, Webpack 이해

### 프로젝트 아이디어
- 개인 대시보드 만들기
- REST API와 연동된 ToDo 앱
- 실시간 채팅 애플리케이션
"""
            recommendation_content = fullstack_advice

        content = f"""# {user_name}님을 위한 커리어 컨설팅

## 📋 질문 분석
**"{user_question}"**

현재 분석을 진행중입니다. 구체적인 정보를 더 제공해주시면 보다 정확한 컨설팅을 해드릴 수 있습니다.

## 💡 추가 도움말
- 구체적인 기술 스택이나 경력 단계를 알려주시면 더 맞춤형 조언을 제공할 수 있습니다.
- 현재 진행 중인 프로젝트나 학습 계획이 있다면 함께 말씀해 주세요.
- 단기적/장기적 커리어 목표를 구체적으로 설명해 주시면 더 나은 로드맵을 제시할 수 있습니다.

---
*G.Navi AI가 {user_name}님의 커리어 성장을 응원합니다!*
"""
        
        result = {
            "formatted_content": content,
            "format_type": "fallback",
            "timestamp": datetime.now().isoformat(),
            "user_name": user_name,
            "session_id": user_data.get('conversationId', ''),
            "components_used": ["recommendation"] if recommendation_content.strip() else ["general_advice"],
            "primary_focus": "fallback_guidance"
        }
        
        # HTML 버전도 생성
        result["formatted_content_html"] = self._convert_data_to_html(content)
        
        self.logger.info(f"폴백 응답 생성 완료: {len(content)}자")
        return result

    def format_final_response(self,
                            user_question: str,
                            recommendation: Dict[str, Any],
                            user_data: Dict[str, Any],
                            intent_analysis: Dict[str, Any] = None) -> Dict[str, Any]:
        """호환성을 위한 레거시 메서드 - 새로운 적응적 포맷팅으로 리다이렉트"""
        # GNaviState 형태로 변환하여 새로운 메서드 호출
        state = {
            "user_question": user_question,
            "recommendation": recommendation,
            "user_data": user_data,
            "intent_analysis": intent_analysis or {},
            "career_cases": [],
            "external_trends": [],
            "chat_history_results": []
        }
        return self.format_adaptive_response(user_question, state)
    
    def format_data_for_display(self, data: Any, output_format: str = "html", show_empty: bool = True) -> str:
        """
        임의의 데이터를 사용자 친화적인 형태로 포맷팅
        
        Args:
            data: 포맷팅할 데이터 (dict, list, str 등)
            output_format: 출력 형식 ("html" 또는 "markdown")
            show_empty: 빈 값들도 표시할지 여부
        
        Returns:
            포맷팅된 문자열
        """
        if output_format.lower() == "markdown":
            if isinstance(data, str):
                return data
            else:
                return self._dict_to_markdown(data, show_empty=show_empty)
        else:  # HTML
            if isinstance(data, str):
                return self._markdown_to_html(data)
            else:
                markdown_text = self._dict_to_markdown(data, show_empty=show_empty)
                return self._markdown_to_html(markdown_text)
    
    def _extract_and_parse_json(self, response_text: str) -> Optional[Dict[str, Any]]:
        """LLM 응답에서 JSON을 추출하고 파싱"""
        try:
            # 1. 직접 JSON 파싱 시도
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass
        
        try:
            # 2. 마크다운 코드 블록에서 JSON 추출 시도
            json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
            matches = re.findall(json_pattern, response_text, re.DOTALL | re.IGNORECASE)
            
            for match in matches:
                try:
                    return json.loads(match.strip())
                except json.JSONDecodeError:
                    continue
            
            # 3. 중괄호로 둘러싸인 JSON 추출 시도
            brace_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            matches = re.findall(brace_pattern, response_text, re.DOTALL)
            
            for match in matches:
                try:
                    return json.loads(match.strip())
                except json.JSONDecodeError:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"JSON 추출 중 오류: {e}")
        
        return None
    
    def _extract_info_from_text(self, response_text: str) -> Dict[str, Any]:
        """JSON 파싱 실패 시 텍스트에서 정보를 추출하여 구조화"""
        self.logger.info("텍스트에서 정보 추출 중...")
        
        # 기본 구조
        result = {
            "analysis": {"question_type": "general", "complexity_level": "3"},
            "content_strategy": {"primary_components": ["text_response"]},
            "formatted_response": {
                "title": "커리어 컨설팅 결과",
                "content": "",
                "call_to_action": "추가 질문이 있으시면 언제든 말씀해 주세요."
            }
        }
        
        try:
            # 텍스트 정리
            cleaned_text = response_text.strip()
            
            # JSON 파싱 오류 관련 텍스트 제거
            cleaned_text = re.sub(r'```(?:json)?\s*', '', cleaned_text)
            cleaned_text = re.sub(r'```\s*', '', cleaned_text)
            
            # 제목 추출 시도
            title_patterns = [
                r'^#\s*(.+?)(?:\n|$)',
                r'제목[:\s]*(.+?)(?:\n|$)',
                r'title[:\s]*["\']?(.+?)["\']?(?:\n|$)'
            ]
            
            for pattern in title_patterns:
                match = re.search(pattern, cleaned_text, re.IGNORECASE | re.MULTILINE)
                if match:
                    title = match.group(1).strip()
                    if title and len(title) < 100:  # 제목이 너무 길지 않은 경우
                        result["formatted_response"]["title"] = title
                        break
            
            # 내용 추출 - 의미있는 텍스트만
            content_lines = []
            for line in cleaned_text.split('\n'):
                line = line.strip()
                if line and not line.startswith('{') and not line.endswith('}'):
                    # JSON 관련 라인 제외
                    if not any(keyword in line.lower() for keyword in 
                             ['json', 'parse', 'error', '```', 'analysis', 'content_strategy']):
                        content_lines.append(line)
            
            if content_lines:
                content = '\n'.join(content_lines[:20])  # 최대 20줄까지만
                # 너무 짧거나 의미없는 내용 필터링
                if len(content.strip()) > 50:
                    result["formatted_response"]["content"] = content
                else:
                    result["formatted_response"]["content"] = "상세한 커리어 조언을 생성하는 중 문제가 발생했습니다. 다시 질문해 주시면 더 나은 답변을 제공해드리겠습니다."
            else:
                result["formatted_response"]["content"] = "죄송합니다. 응답 생성에 일시적인 문제가 발생했습니다. 다시 시도해 주세요."
            
            self.logger.info(f"텍스트에서 정보 추출 완료: 제목={result['formatted_response']['title']}, 내용 길이={len(result['formatted_response']['content'])}")
            
        except Exception as e:
            self.logger.error(f"텍스트 정보 추출 실패: {e}")
            result["formatted_response"]["content"] = "응답 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
        
        return result

    def _validate_json_structure(self, json_data: Dict[str, Any]) -> bool:
        """JSON 응답 구조가 올바른지 검증"""
        try:
            # 필수 키들이 있는지 확인
            required_keys = ["analysis", "content_strategy", "formatted_response"]
            if not all(key in json_data for key in required_keys):
                self.logger.warning(f"필수 키 누락: {[key for key in required_keys if key not in json_data]}")
                return False
            
            # formatted_response 내부 구조 확인
            formatted_response = json_data.get("formatted_response", {})
            if not isinstance(formatted_response, dict):
                self.logger.warning("formatted_response가 딕셔너리가 아님")
                return False
            
            # content 필드가 있고 비어있지 않은지 확인
            content = formatted_response.get("content", "")
            if not content or len(content.strip()) < 10:
                self.logger.warning("content 필드가 비어있거나 너무 짧음")
                return False
            
            # 선택적 필드들 검증 (있으면 타입 체크)
            analysis = json_data.get("analysis", {})
            
            if "should_use_career_cases" in analysis:
                if not isinstance(analysis["should_use_career_cases"], (bool, str)):
                    self.logger.warning("should_use_career_cases 필드 타입 오류")
                    return False
            
            if "additional_questions" in formatted_response:
                if not isinstance(formatted_response["additional_questions"], list):
                    self.logger.warning("additional_questions 필드가 리스트가 아님")
                    return False
            
            self.logger.debug("JSON 구조 검증 통과")
            return True
            
        except Exception as e:
            self.logger.error(f"JSON 구조 검증 중 오류: {e}")
            return False
    
    def _format_chat_history_item(self, chat: Dict[str, Any]) -> str:
        """대화 히스토리 항목을 읽기 쉬운 형태로 포맷팅"""
        if not isinstance(chat, dict):
            return ""
        
        result_parts = []
        
        # 세션 기본 정보
        session_id = chat.get('session_id', '')
        user_id = chat.get('user_id', '')
        timestamp = chat.get('timestamp', '')
        
        if session_id:
            result_parts.append(f"**세션 ID**: {session_id}")
        if timestamp:
            # 타임스탬프를 읽기 쉬운 형태로 변환
            try:
                from datetime import datetime
                if 'T' in timestamp:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    formatted_time = dt.strftime('%Y년 %m월 %d일 %H:%M')
                    result_parts.append(f"**날짜**: {formatted_time}")
                else:
                    result_parts.append(f"**날짜**: {timestamp}")
            except:
                result_parts.append(f"**날짜**: {timestamp}")
        
        # 메시지 내용 포맷팅
        messages = chat.get('messages', [])
        if isinstance(messages, list) and messages:
            result_parts.append("\n**대화 내용**:")
            for i, message in enumerate(messages[:4]):  # 최대 4개 메시지만
                if isinstance(message, dict):
                    role = message.get('role', '')
                    content = message.get('content', '')
                    
                    if content and not self._is_empty_value(content):
                        # 역할 한글화
                        role_korean = {'user': '사용자', 'assistant': 'AI', 'system': '시스템'}.get(role, role)
                        
                        # 내용이 너무 길면 요약
                        if len(content) > 150:
                            content = f"{content[:150]}..."
                        
                        result_parts.append(f"- **{role_korean}**: {content}")
        
        # 레거시 format 지원
        elif chat.get('question') or chat.get('response'):
            question = chat.get('question', '')
            response = chat.get('response', '')
            
            if question and not self._is_empty_value(question):
                if len(question) > 150:
                    question = f"{question[:150]}..."
                result_parts.append(f"**질문**: {question}")
            
            if response and not self._is_empty_value(response):
                if len(response) > 150:
                    response = f"{response[:150]}..."
                result_parts.append(f"**답변**: {response}")
        
        # 컨텍스트 정보 (있는 경우)
        context = chat.get('context', {})
        if isinstance(context, dict) and context:
            session_summary = context.get('session_summary', '')
            if session_summary and not self._is_empty_value(session_summary):
                result_parts.append(f"**세션 요약**: {session_summary}")
        
        return "\n".join(result_parts) if result_parts else ""
    
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
                basic_info.append(f"**👤 이름/직책:** {name} ({position})" if name and position else f"**👤 정보:** {name or position}")
            
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
                basic_info.append(f"**🏢 도메인:** {domain_text}")
            
            # 기술 스택
            current_skills = metadata.get('current_skills', [])
            if current_skills and isinstance(current_skills, list):
                skills_text = ', '.join(current_skills[:7])  # 최대 7개 기술
                if len(current_skills) > 7:
                    skills_text += f" 외 {len(current_skills)-7}개"
                basic_info.append(f"**🔧 핵심 기술:** {skills_text}")
            
            # 관심 분야
            interests = metadata.get('interests', [])
            if interests and isinstance(interests, list):
                interests_text = ', '.join(interests[:5])  # 최대 5개
                basic_info.append(f"**💡 관심 분야:** {interests_text}")
            
            # 커리어 목표
            career_goal = metadata.get('career_goal', '')
            if career_goal:
                basic_info.append(f"**🎯 커리어 목표:** {career_goal}")
            
            # 현재 프로젝트
            current_project = metadata.get('current_project', '')
            if current_project:
                basic_info.append(f"**📋 현재 프로젝트:** {current_project}")
            
            if basic_info:
                markdown_lines.extend(basic_info)
                markdown_lines.append("")  # 빈 줄 추가
            
            # 성장 및 전환 정보 섹션
            growth_info = []
            
            # 전환점
            transition_point = metadata.get('transition_point', '')
            if transition_point and transition_point != 'Unknown':
                growth_info.append(f"**🔄 커리어 전환점:** {transition_point}")
            
            # 성공 요인
            success_factors = metadata.get('success_factors', '')
            if success_factors and success_factors != 'Unknown':
                growth_info.append(f"**🌟 핵심 성공 요소:** {success_factors}")
            
            if growth_info:
                markdown_lines.append("### 📈 성장 포인트")
                markdown_lines.extend(growth_info)
                markdown_lines.append("")
            
            # 상세 경험 내용
            if content and str(content).strip():
                markdown_lines.append("### 📝 상세 경험")
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
                additional_info.append(f"**📊 경력 레벨:** {level_kr}")
            
            # 커리어 연속성
            career_continuity = metadata.get('career_continuity', '')
            if career_continuity:
                continuity_mapping = {
                    'continuous': '연속적',
                    'with_gaps': '단절 있음'
                }
                continuity_kr = continuity_mapping.get(career_continuity, career_continuity)
                additional_info.append(f"**🔗 커리어 연속성:** {continuity_kr}")
            
            # 프로젝트 규모 다양성
            has_large_projects = metadata.get('has_large_projects', '')
            if has_large_projects is not None:
                large_project_text = "대형 프로젝트 경험 있음" if has_large_projects else "중소형 프로젝트 중심"
                additional_info.append(f"**📊 프로젝트 경험:** {large_project_text}")
            
            # 기술 다양성 점수
            skill_diversity = metadata.get('skill_diversity_score', '')
            if skill_diversity and isinstance(skill_diversity, (int, float)) and skill_diversity > 0:
                additional_info.append(f"**🎨 기술 다양성:** {skill_diversity}점")
            
            if additional_info:
                markdown_lines.append("### 📋 추가 정보")
                markdown_lines.extend(additional_info)
            
            result = "\n".join(markdown_lines)
            return result.strip()
            
        except Exception as e:
            self.logger.warning(f"상세 커리어 사례 마크다운 생성 실패: {e}")
            # 폴백: 기본 방식 사용
            return self._dict_to_markdown(case, show_empty=show_empty)
    
    def _has_meaningful_education_data(self, education_courses: Dict[str, Any]) -> bool:
        """교육과정 데이터에 의미 있는 정보가 있는지 확인"""
        if not education_courses:
            return False
        
        # 추천 교육과정이 있는지 확인
        recommended_courses = education_courses.get("recommended_courses", [])
        if recommended_courses and len(recommended_courses) > 0:
            return True
        
        # 학습 경로가 있는지 확인
        learning_path = education_courses.get("learning_path", [])
        if learning_path and len(learning_path) > 0:
            return True
        
        return False
    
    def _format_education_courses_for_llm(self, education_courses: Dict[str, Any]) -> str:
        """교육과정 정보를 LLM용 텍스트로 포맷팅"""
        if not education_courses:
            return ""
        
        sections = []
        
        # 교육과정 분석 정보
        course_analysis = education_courses.get("course_analysis", {})
        recommended_courses = education_courses.get("recommended_courses", [])
        learning_path = education_courses.get("learning_path", [])
        
        if not recommended_courses and not learning_path:
            return ""
        
        sections.append("📚 **추천 교육과정 (SKALA College + mySUNI)**:")
        sections.append("**⚠️ 중요 사항: 다음은 실제 사내 교육과정 정보입니다.**")
        sections.append("**사용자가 교육, 학습, 스킬 향상을 요청하는 경우 반드시 아래 과정들을 직접 활용하세요!**\n")
        
        # 추천 교육과정 상세 정보
        if recommended_courses:
            sections.append("### 🎯 **추천 교육과정 목록:**")
            
            for i, course in enumerate(recommended_courses[:8], 1):  # 최대 8개
                course_info = self._format_single_course(course, i)
                if course_info.strip():
                    sections.append(course_info)
        
        # 학습 경로 정보
        if learning_path:
            sections.append("\n### 📈 **단계별 학습 경로:**")
            for step in learning_path:
                step_info = self._format_learning_step(step)
                if step_info.strip():
                    sections.append(step_info)
        
        # 교육과정 분석 통계
        if course_analysis and isinstance(course_analysis, dict):
            sections.append("\n### 📊 **교육과정 분석:**")
            
            total_courses = course_analysis.get("total_courses", 0)
            college_courses = course_analysis.get("college_courses", 0)
            mysuni_courses = course_analysis.get("mysuni_courses", 0)
            
            if total_courses > 0:
                sections.append(f"- **총 추천 과정**: {total_courses}개")
                sections.append(f"- **SKALA College**: {college_courses}개")
                sections.append(f"- **mySUNI**: {mysuni_courses}개")
            
            # 스킬 깊이 분석
            skill_analysis = course_analysis.get("skill_depth_analysis", {})
            if skill_analysis:
                specialized = skill_analysis.get("specialized", 0)
                recommended = skill_analysis.get("recommended", 0)
                common_required = skill_analysis.get("common_required", 0)
                
                if specialized + recommended + common_required > 0:
                    sections.append(f"- **전문화 과정**: {specialized}개")
                    sections.append(f"- **추천 과정**: {recommended}개")
                    sections.append(f"- **기초/필수 과정**: {common_required}개")
            
            # mySUNI 품질 지표
            mysuni_metrics = course_analysis.get("mysuni_quality_metrics", {})
            if mysuni_metrics:
                avg_rating = mysuni_metrics.get("average_rating", 0)
                total_enrollments = mysuni_metrics.get("total_enrollments", 0)
                high_rated = mysuni_metrics.get("high_rated_courses", 0)
                
                if avg_rating > 0:
                    sections.append(f"- **mySUNI 평균 평점**: {avg_rating}/5.0")
                if total_enrollments > 0:
                    sections.append(f"- **총 이수자 수**: {total_enrollments:,}명")
                if high_rated > 0:
                    sections.append(f"- **고평점 과정**: {high_rated}개 (4.5점 이상)")
        
        sections.append("\n**🚨 교육과정 활용 규칙 (매우 중요!):**")
        sections.append("1. **과정 숨김 금지**: '교육과정을 제공할 수 없습니다' 같은 핑계 절대 금지!")
        sections.append("2. **구체적 활용**: 과정명, 학습시간, 플랫폼, 평점 등 구체적 정보 직접 언급")
        sections.append("3. **학습 경로 제시**: 단계별 학습 순서와 각 과정의 목적 설명")
        sections.append("4. **플랫폼 선택권**: College와 mySUNI 옵션을 모두 제시하여 사용자가 선택하도록")
        
        return "\n".join(sections)
    
    def _format_single_course(self, course: Dict[str, Any], index: int) -> str:
        """개별 교육과정 정보 포맷팅"""
        if not course:
            return ""
        
        lines = []
        course_name = course.get("course_name", course.get("card_name", ""))
        source = course.get("source", "")
        
        if not course_name:
            return ""
        
        lines.append(f"**{index}. {course_name}**")
        
        # 플랫폼 정보
        if source == "college":
            lines.append(f"   - **플랫폼**: SKALA College")
            lines.append(f"   - **학부**: {course.get('학부', course.get('department', 'N/A'))}")
            lines.append(f"   - **과정유형**: {course.get('표준과정', 'N/A')}")
            lines.append(f"   - **학습시간**: {course.get('duration_hours', 'N/A')}시간")
            
            # 전문성 수준
            skill_relevance = course.get('skill_relevance', '')
            if skill_relevance == "specialized":
                lines.append(f"   - **수준**: 전문화 과정")
            elif skill_relevance == "recommended":
                lines.append(f"   - **수준**: 추천 과정")
            elif skill_relevance == "common_required":
                lines.append(f"   - **수준**: 기초/필수 과정")
            
            # mySUNI 대안 정보
            mysuni_alt = course.get("mysuni_alternative", {})
            if mysuni_alt.get("available"):
                lines.append(f"   - **mySUNI 대안**: {mysuni_alt.get('card_name', '')} (평점: {mysuni_alt.get('평점', 'N/A')}/5.0)")
                
        elif source == "mysuni":
            lines.append(f"   - **플랫폼**: mySUNI")
            lines.append(f"   - **카테고리**: {course.get('카테고리명', '')} > {course.get('채널명', '')}")
            lines.append(f"   - **난이도**: {course.get('난이도', course.get('difficulty_level', 'N/A'))}")
            lines.append(f"   - **학습시간**: {course.get('인정학습시간', course.get('duration_hours', 'N/A'))}시간")
            
            # 평점과 이수자 수
            rating = course.get('평점', 0)
            enrollments = course.get('이수자수', '0')
            if rating and rating > 0:
                lines.append(f"   - **평점**: {rating}/5.0 ({enrollments}명 이수)")
            
            lines.append(f"   - **학습방식**: 온라인 자율학습")
        
        # 대상 스킬
        target_skills = course.get('target_skills', [])
        if target_skills:
            lines.append(f"   - **대상 스킬**: {', '.join(target_skills[:3])}")  # 최대 3개만 표시
        
        return "\n".join(lines)
    
    def _format_learning_step(self, step: Dict[str, Any]) -> str:
        """학습 경로 단계 포맷팅"""
        if not step:
            return ""
        
        lines = []
        step_num = step.get("step", "")
        level = step.get("level", "")
        description = step.get("description", "")
        courses = step.get("courses", [])
        
        if step_num == "보완":
            lines.append(f"**🔄 {step_num} - {level}**")
        else:
            lines.append(f"**📚 {step_num}단계 - {level}**")
        
        if description:
            lines.append(f"   {description}")
        
        if courses:
            lines.append(f"   **추천 과정 ({len(courses)}개):**")
            for i, course in enumerate(courses[:3], 1):  # 최대 3개
                course_name = course.get("course_name", course.get("card_name", ""))
                source = course.get("source", "")
                duration = course.get("duration_hours", course.get("인정학습시간", "N/A"))
                
                platform = "SKALA College" if source == "college" else "mySUNI"
                lines.append(f"   {i}. {course_name} ({platform}, {duration}시간)")
        
        return "\n".join(lines)