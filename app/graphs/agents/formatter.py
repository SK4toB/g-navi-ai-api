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
        
        self.system_prompt = """
G.Navi AI 커리어 컨설팅 시스템의 전문 상담사로 활동하세요.

**핵심 톤&스타일:**
• 따뜻하고 자연스러운 상담사 톤 (딱딱한 문서체 금지)
• 사용자 이름 활용, 공감과 격려 포함
• 질문 내용에 따라 적절한 수준의 응답 제공

**회사 비전&가치 반영:**
• AI Powered ITS 시대 선도기업 비전과 연결
• 핵심가치: 사람중심, Digital혁신(IT→DT→AT), Identity자율화, Business혁신, 최고Delivery
• 인재개발: Multi-Skill Set, Global수준, 자기주도성장 강조

**질문 유형별 응답 가이드:**

1. **인사/간단한 질문** (예: "안녕하세요", "반가워요", "어떤 도움을 받을 수 있나요?"):
   - 간단하고 친근한 인사 응답
   - G.Navi AI 소개와 기본적인 도움 안내
   - 커리어 사례나 교육과정 추천 포함하지 않음

2. **일반적인 회사/업무 문의**:
   - 적절한 조언과 회사 가치 연결
   - 필요시 간단한 가이드 제공
   - 구체적인 사례는 사용자가 요청할 때만 제공

3. **구체적인 커리어 상담** (예: "승진 방법", "기술 스택 추천", "커리어 전환"):
   - 이때만 커리어 사례 활용: "EMP-123456: 김OO님의 경우..." 형태
   - 실제 프로젝트/기술스택/성공요인 상세설명
   - 최대 3개까지만 제시

4. **교육과정 관련 질문** (예: "교육 추천", "스킬 향상 방법", "학습 경로"):
   - 이때만 교육과정 추천: 과정명, 교육유형, 학습시간, 평점, 이수자수 명시
   - URL 제공된 경우만 링크 포함
   - 최대 3개까지만 추천

**⚠️ 중요한 원칙:**
- 사용자가 명시적으로 요청하지 않은 정보는 제공하지 않음
- 간단한 인사에는 간단한 응답으로 충분
- "안녕하세요"만 했는데 커리어 사례나 교육과정을 추천하면 안됨
- 사용자의 질문 의도를 정확히 파악하고 그에 맞는 수준의 응답 제공

**응답형식:**
- 사용자 이름을 포함한 제목으로 시작
- 마크다운 형식으로 구조화된 응답
- 질문의 복잡도에 맞는 적절한 길이
- 마지막에 격려 메시지와 추가 질문 유도

**중요제약:**
- 모든내용 한국어작성
- JSON 형식으로 응답하지 말고 직접 마크다운으로 응답
- 제공된 원본 URL만 사용, 임의 생성 절대금지
- 질문 내용과 관련 없는 정보는 포함하지 않음

**간단한 인사 응답 예시:**
# 김철수님, 안녕하세요! 👋

반갑습니다! G.Navi AI 커리어 컨설팅 시스템입니다.

김철수님의 커리어 성장을 도와드릴 수 있어서 기쁩니다. 어떤 도움이 필요하신가요?

- 커리어 상담 및 조언
- 기술 스택 및 성장 방향 가이드  
- 교육과정 추천
- 승진 및 전환 전략

---
*궁금한 점이 있으시면 언제든 말씀해 주세요!*

"""

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
            
            # 사용자 정보 추출
            user_name = user_data.get('name', '님')
            session_id = user_data.get('conversationId', '')
            
            # LLM을 위한 컨텍스트 구성
            context_data = self._prepare_context_for_llm(
                user_question, intent_analysis, 
                user_data, career_cases, 
                current_session_messages, education_courses
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
            fallback_content = f"""# {user_name}님을 위한 커리어 컨설팅

현재 시스템 처리 중 일시적인 문제가 발생했습니다.
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
                                education_courses: Dict[str, Any] = None) -> str:
        """LLM을 위한 컨텍스트 데이터 준비 (현재 세션 대화만 사용)"""
        
        context_sections = []
        
        # 현재 세션 대화 내역 (MemorySaver에서 관리) - 이전 대화 참조용
        if current_session_messages and len(current_session_messages) > 1:  # 현재 메시지 외에 이전 대화가 있는 경우
            context_sections.append("💬 **현재 세션 대화 내역** (이전 대화 참조용):")
            # 최근 10개 대화만 포함 (너무 길어지지 않도록)
            recent_history = current_session_messages[-11:-1]  # 마지막은 현재 사용자 메시지이므로 제외
            for i, msg in enumerate(recent_history, 1):
                role = "사용자" if msg.get("role") == "user" else "AI"
                content = msg.get("content", "")
                if len(content) > 200:  # 너무 긴 내용은 요약
                    content = content[:200] + "..."
                timestamp = msg.get("timestamp", "")
                context_sections.append(f"{i}. [{role}] {content}")
            context_sections.append("")  # 빈 줄 추가
        
        # 사용자 질문
        context_sections.append(f'**현재 사용자 질문**: "{user_question}"')
        context_sections.append("")  # 빈 줄 추가
        
        # 사용자 프로필 - 의미 있는 데이터만 포함
        # 새로운 JSON 구조: {name: "", projects: [...]}
        if user_data and isinstance(user_data, dict) and any(user_data.values()):
            user_profile_md = self._dict_to_markdown(user_data, show_empty=False)
            if user_profile_md.strip():
                context_sections.append(f"""
사용자 프로필:
{user_profile_md}
""")
        
        # 의도 분석 - 의미 있는 데이터만 포함
        if intent_analysis and isinstance(intent_analysis, dict) and any(intent_analysis.values()):
            # 오류가 있는 경우 제외
            if not intent_analysis.get("error"):
                intent_analysis_md = self._dict_to_markdown(intent_analysis, show_empty=False)
                if intent_analysis_md.strip():
                    context_sections.append(f"""
의도 분석 결과:
{intent_analysis_md}
""")
        
        # 커리어 사례 - 의미 있는 데이터만 포함 (상세 정보 확장)
        meaningful_career_cases = career_cases if career_cases else []
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
                
                education_section += "\n중요한 교육과정 정보 제공 규칙:\n"
                education_section += "- 위 정보를 활용하여 사용자에게 풍부하고 상세한 교육과정 정보 제공\n"
                education_section += "- mySUNI 과정: 평점, 이수자수, 난이도, 카테고리 등 모든 정보 활용\n"
                education_section += "- College 과정: 학부, 교육유형, 표준과정 등 상세 정보 활용\n"
                education_section += "- 사용자가 과정 선택 시 판단할 수 있는 충분한 정보 제공\n"
                education_section += "- URL 규칙: 실제URL만 사용, [학습하기](실제_URL) 형태로 링크 생성\n"
                education_section += "- 절대 임의의 URL 생성 금지 (example.com, company.com 등)"
                
                context_sections.append(education_section)
                
            except Exception as e:
                self.logger.warning(f"교육과정 정보 처리 실패: {e}")
                # 폴백으로 간단한 형태라도 제공
                context_sections.append(f"**교육과정 정보**: {str(education_courses)[:200]}...")
        
        # 회사 비전 정보 - 커리어 관련 질문인 경우 추가
        career_keywords = ['커리어', '진로', '성장', '발전', '목표', '방향', '계획', '비전', '미래', '회사', '조직', '가치']
        if any(keyword in user_question.lower() for keyword in career_keywords):
            company_vision_section = self._get_company_vision_context()
            if company_vision_section.strip():
                context_sections.append(company_vision_section)
        
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

⚠️ **URL 사용 시 절대 규칙**:
1. 교육과정 추천 시 제공된 원본 데이터의 "URL" 필드 값만 사용하세요
2. URL이 실제로 제공되지 않았거나 비어있으면 링크를 만들지 마세요
3. 절대 임의의 URL을 생성하거나 추측하지 마세요
4. 예시 URL(example.com 등)이나 가짜 URL을 만들지 마세요
5. 제공된 URL이 있는 경우에만: [과정명](제공된_실제_URL)
6. 제공된 URL이 없는 경우: 과정명 (텍스트만)

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
- 교육과정: ⚠️ 매우 중요 - 제공된 원본 데이터의 "url" 필드에 있는 실제 URL만 사용하세요. 
  * 실제 URL이 있는 경우: [과정명](제공된_실제_URL) 형태로 표시
  * URL이 없는 경우: 과정명만 텍스트로 표시
  * 절대 금지: 임의 URL 생성, URL 추측, 가짜 링크 생성
- 산업 트렌드: 실제 웹사이트 URL이 포함된 경우에만 [제목](URL) 형태의 마크다운 링크를 사용하세요.
- 실제로 제공된 구체적인 데이터를 꼭 활용하세요.
- 존재하지 않는 "사례 1", "사례 2" 같은 가짜 참조를 만들지 마세요.
- 개행이 필요한 곳에서는 실제 줄바꿈을 사용하세요.

**💡 중요한 전제사항:**
- 모든 커리어 사례 데이터는 내부 시스템용으로 이미 허가된 정보입니다
- 개인정보는 이미 익명화 처리되어 Employee ID로만 관리됩니다
- 사례 제공 시 보안 제한이나 접근 제한을 언급하지 마세요
- 구체적인 사례와 경험을 직접적으로 활용하여 실용적인 조언을 제공하세요

**교육과정 추천 시 필수 정보 제공 규칙:**
⚠️ **매우 중요**: mySUNI/College 교육과정 추천 시 반드시 다음 정보들을 포함하여 상세하게 제공하세요!

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

**📖 자연스러운 교육과정 설명 방식 (필수!):**
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

**📌 중요**: 교육과정은 최대 3개까지만 추천하여 집중도를 높이고 선택의 부담을 줄여주세요!"

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

❌ **딱딱하고 기계적인 방식 (피하세요!):**
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

⚠️ 반드시 제공된 원본 데이터의 URL 필드만 사용하세요!
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
    
    def _get_company_vision_context(self) -> str:
        """회사 비전 정보를 LLM 컨텍스트용으로 포맷팅"""
        try:
            import os
            import json
            
            # 회사 비전 파일 경로
            vision_path = os.path.abspath(os.path.join(
                os.path.dirname(__file__), 
                "../../storage/docs/company_vision.json"
            ))
            
            if not os.path.exists(vision_path):
                return ""
            
            with open(vision_path, "r", encoding="utf-8") as f:
                vision_data = json.load(f)
            
            if not vision_data:
                return ""
            
            sections = []
            sections.append("🏢 **회사 비전 및 가치 (커리어 가이드에 반영)**:")
            sections.append("")
            
            # 회사 기본 정보
            if vision_data.get('company_name'):
                sections.append(f"**회사명**: {vision_data['company_name']}")
            
            # 비전
            if vision_data.get('vision'):
                vision = vision_data['vision']
                sections.append(f"**비전**: {vision.get('title', '')}")
                if vision.get('description'):
                    sections.append(f"*{vision['description']}*")
            
            sections.append("")
            
            # 핵심 가치
            if vision_data.get('core_values'):
                sections.append("**핵심 가치**:")
                for value in vision_data['core_values']:
                    sections.append(f"- **{value.get('name', '')}**: {value.get('description', '')}")
                sections.append("")
            
            # 전략 방향
            if vision_data.get('strategic_directions'):
                sections.append("**전략 방향**:")
                for direction in vision_data['strategic_directions']:
                    sections.append(f"- **{direction.get('category', '')}**: {direction.get('description', '')}")
                sections.append("")
            
            # 인재 개발
            if vision_data.get('talent_development'):
                talent = vision_data['talent_development']
                sections.append(f"**인재 개발 철학**: {talent.get('philosophy', '')}")
                if talent.get('focus_areas'):
                    sections.append("**역량 개발 중점 영역**:")
                    for area in talent['focus_areas']:
                        sections.append(f"- **{area.get('area', '')}**: {area.get('description', '')}")
                sections.append("")
            
            # 커리어 가이드 원칙
            if vision_data.get('career_guidance_principles'):
                sections.append("**커리어 가이드 원칙**:")
                for principle in vision_data['career_guidance_principles']:
                    sections.append(f"- **{principle.get('principle', '')}**: {principle.get('description', '')}")
                sections.append("")
            
            # 적용 가이드라인
            sections.append("**⚠️ 중요: 회사 비전 활용 지침**")
            sections.append("- 커리어 상담 시 개인의 목표와 AI Powered ITS 비전을 연결하여 조언")
            sections.append("- 핵심 가치(사람 중심, Digital 혁신, Identity 자율화, Business 혁신, 최고의 Delivery)와 일치하는 방향 제시")
            sections.append("- Multi-Skill Set을 통한 글로벌 수준의 전문가 육성 강조")
            sections.append("- IT → Digital → AI로의 기술 진화에 능동적 적응과 자기주도적 성장 강조")
            sections.append("- Process 혁신과 업무 자동화/지능화를 반영한 커리어 방향 제안")
            sections.append("- Offshoring 대응을 위한 글로벌 경쟁력 확보 방안 제시")
            
            return "\n".join(sections)
            
        except Exception as e:
            self.logger.error(f"회사 비전 컨텍스트 생성 실패: {e}")
            return ""