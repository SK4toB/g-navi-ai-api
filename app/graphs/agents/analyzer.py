from typing import Dict, Any, List
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
import json
import logging

class IntentAnalysisAgent:
    """
     의도 분석 에이전트 - 커리어 검색 키워드 추출에 집중
    
    사용자 질문을 분석하여 의도를 파악하고, 다음 단계의 
    커리어 사례 검색에 필요한 핵심 키워드를 추출합니다.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
    
    def analyze_intent_and_context(self, 
                                 user_question: str, 
                                 user_data: Dict[str, Any], 
                                 chat_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """
         사용자 의도 종합 분석
        
        사용자 질문, 프로필 정보, 대화 히스토리를 종합하여
        의도를 파악하고 커리어 검색에 필요한 키워드를 추출합니다.
        
        Args:
            user_question: 사용자 질문
            user_data: 사용자 프로필 정보
            chat_history: 과거 대화 내역
            
        Returns:
            Dict: 의도 분석 결과 (career_history 키워드 포함)
        """
        
        self.logger.info("의도 분석 시작")
        
        # 커리어 검색 키워드 추출
        return self._perform_unified_analysis(user_question, user_data, chat_history)
    
    def _perform_unified_analysis(self, user_question: str, user_data: Dict[str, Any], chat_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """
         통합 의도 분석 수행
        
        GPT-4o-mini를 사용하여 사용자 질문을 분석하고
        커리어 검색에 최적화된 키워드를 추출합니다.
        
        Args:
            user_question: 사용자 질문
            user_data: 사용자 프로필 정보  
            chat_history: 과거 대화 내역
            
        Returns:
            Dict: career_history 키워드 배열을 포함한 분석 결과
        """
        
        # 과거 대화내역 요약
        chat_summary = self._summarize_chat_history(chat_history)
        
        # 키워드 추출을 위한 분석 프롬프트
        system_prompt = """당신은 AI 커리어 컨설턴트입니다. 사용자의 질문을 분석하여 반드시 유효한 JSON 형태로만 응답해주세요.

중요: 다른 텍스트 없이 오직 아래 형태의 JSON만 출력하세요. 마크다운 코드 블록이나 추가 설명은 절대 포함하지 마세요.

{{"career_history": ["키워드1", "키워드2", "키워드3"]}}

- career_history: 사용자 질문과 관련된 커리어 사례 검색용 키워드 배열 (최대 3개)
  예시: ["데이터분석", "마케팅", "전환"], ["개발자", "프론트엔드", "경력"], ["AI", "머신러닝", "입문"]"""

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
            
            # 필수 필드 검증 (간소화)
            required_fields = ["career_history"]
            for field in required_fields:
                if field not in analysis_result:
                    self.logger.warning(f"필수 필드 누락: {field}")
                    raise ValueError(f"LLM 응답에 필수 필드 누락: {field}")
            
            # career_history가 리스트인지 확인
            if not isinstance(analysis_result.get("career_history"), list):
                self.logger.warning("career_history가 리스트가 아님")
                analysis_result["career_history"] = []
            
            self.logger.info("간소화된 의도 분석 완료")
            return analysis_result
                
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON 파싱 실패: {e}")
            self.logger.error(f"LLM 응답 내용: {response.content[:200]}...")
            raise e
        except Exception as e:
            self.logger.error(f"키워드 추출 분석 실패: {e}")
            self.logger.error(f"오류 타입: {type(e).__name__}")
            if hasattr(e, 'args'):
                self.logger.error(f"오류 인자: {e.args}")
            raise e
    
    def _summarize_chat_history(self, chat_history: List[Dict[str, str]]) -> str:
        """
         과거 대화내역 간단 요약
        
        최근 대화 내역을 분석하여 맥락 파악에 필요한
        핵심 정보만 추출합니다.
        
        Args:
            chat_history: 과거 대화 메시지 리스트
            
        Returns:
            str: 요약된 대화 내역
        """
        if not chat_history:
            return "과거 대화내역 없음"
        
        chat_items = []
        # 최근 7개 메시지만 요약 (assistant 메시지 중심)
        for msg in chat_history[-7:]:
            if msg.get('role') == 'assistant' and msg.get('content'):
                content = msg['content'][:100]  # 첫 100자만
                chat_items.append(f"- {content}...")
        
        return "\n".join(chat_items) if chat_items else "과거 대화내역 없음"
