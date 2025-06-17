# analyzer.py

from typing import Dict, Any, List
from langchain.schema import Document
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
import json
import logging

class IntentAnalysisAgent:
    """범용적 의도 분석 에이전트 - 단일 LLM 호출로 모든 질문 처리"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    
    def analyze_intent_and_context(self, 
                                 user_question: str, 
                                 user_data: Dict[str, Any], 
                                 chat_history: List[Document]) -> Dict[str, Any]:
        """범용적 의도 분석 - 모든 질문을 LLM으로 처리"""
        
        self.logger.info("범용적 의도 분석 시작")
        
        # 모든 질문을 LLM으로 통합 분석
        return self._perform_unified_analysis(user_question, user_data, chat_history)
    
    def _perform_unified_analysis(self, user_question: str, user_data: Dict[str, Any], chat_history: List[Document]) -> Dict[str, Any]:
        """단일 LLM 호출로 통합 분석 수행"""
        
        # 과거 대화내역 요약
        chat_summary = self._summarize_chat_history(chat_history)
        
        # 범용적 분석 프롬프트
        system_prompt = """당신은 AI 커리어 컨설턴트입니다. 사용자의 질문을 분석하여 반드시 유효한 JSON 형태로만 응답해주세요.

중요: 다른 텍스트 없이 오직 아래 형태의 JSON만 출력하세요. 마크다운 코드 블록이나 추가 설명은 절대 포함하지 마세요.

{{"primary_interest": "주요 관심사", "urgency": "긴급도", "complexity": 복잡도숫자, "question_type": "질문유형", "career_history": ["키워드1", "키워드2"], "external_trends": ["트렌드1", "트렌드2"], "requires_full_analysis": true, "response_strategy": "comprehensive"}}

- primary_interest: 커리어 전환, 스킬 개발, 이직 준비, 인사/소개, 일반 상담 등
- urgency: 높음, 보통, 낮음 중 하나
- complexity: 1-5 사이의 숫자 (1=간단, 5=복합적)
- question_type: 인사형, 구체적, 추상적, 탐색적 중 하나
- career_history: 커리어 사례 검색용 키워드 배열 (최대 3개)
- external_trends: 트렌드 검색용 키워드 배열 (최대 2개)"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", """
**사용자 질문:** {question}

**사용자 프로필:**
{user_profile}

**과거 대화내역:**
{chat_summary}

위 정보를 종합하여 분석해주세요.
""")
        ])
        
        try:
            # LLM 호출
            response = self.llm.invoke(prompt.format_messages(
                question=user_question,
                user_profile=json.dumps(user_data, ensure_ascii=False, indent=2),
                chat_summary=chat_summary
            ))
            
            # JSON 파싱 시도
            content = response.content.strip()
            
            # 마크다운 코드 블록 제거
            if content.startswith('```'):
                lines = content.split('\n')
                json_lines = []
                in_json = False
                for line in lines:
                    if '```' in line:
                        in_json = not in_json
                        continue
                    if in_json:
                        json_lines.append(line)
                content = '\n'.join(json_lines).strip()
            
            # JSON 파싱
            analysis_result = json.loads(content)
            
            # 필수 필드 검증
            required_fields = ["primary_interest", "urgency", "complexity", "question_type"]
            for field in required_fields:
                if field not in analysis_result:
                    self.logger.warning(f"필수 필드 누락: {field}")
                    raise ValueError(f"LLM 응답에 필수 필드 누락: {field}")
            
            self.logger.info("범용적 의도 분석 완료")
            return analysis_result
                
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON 파싱 실패: {e}")
            self.logger.error(f"LLM 응답 내용: {response.content[:200]}...")
            raise e
        except Exception as e:
            self.logger.error(f"통합 분석 실패: {e}")
            self.logger.error(f"오류 타입: {type(e).__name__}")
            if hasattr(e, 'args'):
                self.logger.error(f"오류 인자: {e.args}")
            raise e
    
    def _summarize_chat_history(self, chat_history: List[Document]) -> str:
        """과거 대화내역 간단 요약"""
        if not chat_history:
            return "과거 대화내역 없음"
        
        chat_items = []
        for doc in chat_history[:3]:  # 최근 3개만
            session_summary = doc.get('context', {}).get('session_summary', '')
            if session_summary:
                chat_items.append(f"- {session_summary}")
        
        return "\n".join(chat_items) if chat_items else "과거 대화내역 없음"


