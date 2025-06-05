# # app/services/openai_service.py
# from openai import AsyncOpenAI
# import os
# from typing import Optional, List, Dict, Any
# from datetime import datetime

# class OpenAIService:
#     def __init__(self):
#         # 환경변수에서 OpenAI API 키 가져오기
#         api_key = os.getenv("OPENAI_API_KEY")
#         print(api_key)
#         if not api_key:
#             raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다")
        
#         # AsyncOpenAI 클라이언트 초기화
#         self.client = AsyncOpenAI(api_key=api_key)
        
#         # 기본 설정
#         self.model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
#         self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "1000"))
#         self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    
#     async def generate_response(
#         self, 
#         user_message: str, 
#         context: Optional[str] = None,
#         conversation_history: Optional[List[Dict[str, str]]] = None
#     ) -> str:
#         """
#         OpenAI API를 사용하여 응답 생성
#         """
#         try:
#             # 메시지 구성
#             messages = [
#                 {
#                     "role": "system", 
#                     "content": self._get_system_prompt(context)
#                 }
#             ]
            
#             # 대화 히스토리 추가 (있는 경우)
#             if conversation_history:
#                 messages.extend(conversation_history)
            
#             # 현재 사용자 메시지 추가
#             messages.append({
#                 "role": "user",
#                 "content": user_message
#             })
            
#             # OpenAI API 호출 (새로운 방식)
#             response = await self.client.chat.completions.create(
#                 model=self.model,
#                 messages=messages,
#                 max_tokens=self.max_tokens,
#                 temperature=self.temperature,
#                 presence_penalty=0.0,
#                 frequency_penalty=0.0
#             )
            
#             return response.choices[0].message.content.strip()
            
#         except Exception as e:
#             # 구체적인 에러 타입 확인
#             error_message = str(e)
#             if "rate_limit" in error_message.lower():
#                 raise Exception("API 호출 한도를 초과했습니다. 잠시 후 다시 시도해주세요.")
#             elif "authentication" in error_message.lower() or "api_key" in error_message.lower():
#                 raise Exception("OpenAI API 인증에 실패했습니다. API 키를 확인해주세요.")
#             elif "insufficient_quota" in error_message.lower():
#                 raise Exception("OpenAI API 사용량을 초과했습니다.")
#             else:
#                 raise Exception(f"응답 생성 중 오류가 발생했습니다: {str(e)}")
    
#     def _get_system_prompt(self, context: Optional[str] = None) -> str:
#         """
#         시스템 프롬프트 생성
#         """
#         base_prompt = """
#         당신은 도움이 되고 친근한 AI 어시스턴트입니다.
#         사용자의 질문에 정확하고 유용한 답변을 제공해주세요.
        
#         응답 가이드라인:
#         - 한국어로 응답해주세요
#         - 친근하고 전문적인 톤을 유지해주세요
#         - 구체적이고 실용적인 정보를 제공해주세요
#         - 불확실한 정보는 추측하지 말고 모른다고 말해주세요
#         """
        
#         if context:
#             base_prompt += f"\n\n추가 컨텍스트: {context}"
        
#         return base_prompt
    
#     async def generate_initial_greeting(self, user_info: Dict[str, Any]) -> str:
#         """
#         사용자 정보를 바탕으로 개인화된 초기 인사 메시지 생성
#         """
#         try:
#             name = user_info.get('name', '사용자')
#             projects = user_info.get('projects', [])
#             skills = user_info.get('skills', [])
            
#             # 프로젝트 정보 포맷팅
#             project_info = ""
#             if projects:
#                 project_names = [p.get('name', '프로젝트') for p in projects[:3]]
#                 project_info = f"진행 중인 프로젝트: {', '.join(project_names)}"
            
#             # 스킬 정보 포맷팅
#             skill_info = ""
#             if skills:
#                 skill_info = f"보유 기술: {', '.join(skills[:5])}"
            
#             prompt = f"""
#             사용자 정보:
#             - 이름: {name}
#             {project_info}
#             {skill_info}
            
#             위 정보를 바탕으로 개인화된 인사 메시지를 생성해주세요.
#             다음 조건을 만족해야 합니다:
#             - 2-3문장으로 간결하게 작성
#             - 사용자의 프로젝트나 스킬을 자연스럽게 언급
#             - 어떤 도움을 줄 수 있는지 간략히 설명
#             - 친근하고 전문적인 톤 유지
#             """
            
#             return await self.generate_response(prompt)
            
#         except Exception as e:
#             # 기본 인사 메시지 반환
#             print(f"초기 인사 메시지 생성 실패: {e}")
#             name = user_info.get('name', '사용자')
#             return f"안녕하세요 {name}님! 저는 당신의 AI 어시스턴트입니다. 궁금한 것이 있으시면 언제든 물어보세요!"
    
#     def format_conversation_history(
#         self, 
#         messages: List[Dict[str, Any]], 
#         limit: int = 10
#     ) -> List[Dict[str, str]]:
#         """
#         메모리 저장소의 메시지 형식을 OpenAI API 형식으로 변환
#         """
#         formatted_messages = []
        
#         # 최근 메시지만 사용 (토큰 제한 고려)
#         recent_messages = messages[-limit:] if len(messages) > limit else messages
        
#         for msg in recent_messages:
#             role = "user" if msg["message_type"] == "user" else "assistant"
#             formatted_messages.append({
#                 "role": role,
#                 "content": msg["message"]
#             })
        
#         return formatted_messages

# services/openai_service.py
import openai
from openai import AsyncOpenAI
from typing import List, Dict, Any, Optional
from config.settings import settings

class OpenAIService:
    """OpenAI API 호출을 위한 서비스 클래스 (기존 settings 호환)"""
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY  # 대문자로 변경
        
        # AsyncOpenAI 클라이언트 초기화
        self.client = AsyncOpenAI(api_key=self.api_key)
        
        # 기본 설정 (대문자 필드명 사용)
        self.model = settings.OPENAI_MODEL
        self.temperature = settings.OPENAI_TEMPERATURE
        self.max_tokens = settings.OPENAI_MAX_TOKENS
    
    
    async def chat_completion(
        self, 
        messages: List[Dict[str, str]],  # [{"role": "user", "content": "..."}] 형태
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """채팅 완료 API 호출"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            raise Exception(f"OpenAI chat completion failed: {str(e)}")
    
    async def create_embedding(self, text: str) -> List[float]:
        """텍스트 임베딩 생성"""
        
        try:
            response = await self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            raise Exception(f"OpenAI embedding creation failed: {str(e)}")
    
    async def analyze_career_intent(self, user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """커리어 상담 의도 분석"""
        
        system_prompt = """당신은 지나비 프로젝트의 커리어 성장 상담 전문 AI입니다.
사용자의 메시지를 분석하여 다음 정보를 JSON 형태로 반환하세요:

{
    "intent": "의도 분류 (career_exploration, skill_development, growth_strategy, self_profiling, project_recommendation, general_chat)",
    "confidence": "신뢰도 (0.0-1.0)",
    "keywords": ["추출된 키워드들"],
    "career_level": "예상 커리어 레벨 (junior, mid, senior, unknown)",
    "urgent": "긴급도 (true/false)",
    "needs_profiling": "추가 프로파일링 필요 여부 (true/false)"
}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"사용자 메시지: {user_input}"}
        ]
        
        if context:
            messages.insert(-1, {"role": "user", "content": f"사용자 컨텍스트: {context}"})
        
        try:
            response = await self.chat_completion(messages, temperature=0.3)
            
            # JSON 파싱 시도
            import json
            result = json.loads(response)
            return result
            
        except json.JSONDecodeError:
            # JSON 파싱 실패시 기본값 반환
            return {
                "intent": "general_chat",
                "confidence": 0.5,
                "keywords": [],
                "career_level": "unknown",
                "urgent": False,
                "needs_profiling": True
            }
        except Exception as e:
            raise Exception(f"Career intent analysis failed: {str(e)}")
    
    async def generate_career_response(
        self, 
        user_input: str,
        context: Dict[str, Any],
        similar_cases: List[Dict[str, Any]] = None,
        recommendations: Dict[str, Any] = None
    ) -> str:
        """커리어 상담 응답 생성"""
        
        system_prompt = """당신은 지나비 프로젝트의 커리어 성장 상담 전문 AI입니다.
사용자의 질문에 대해 다음 원칙을 지켜 응답하세요:

1. 친근하고 공감적인 톤 사용
2. 구체적이고 실행 가능한 조언 제공
3. 회사 내부 리소스와 기회 활용 방안 제시
4. 단계별 성장 방법 제안
5. 동기부여가 되는 메시지 포함

응답은 한국어로 작성하고, 2-3문단 내외로 구성하세요."""

        user_prompt = f"""
**사용자 질문:** {user_input}

**사용자 정보:** {context}
"""
        
        if similar_cases:
            user_prompt += f"\n**관련 성장 사례들:** {similar_cases}"
        
        if recommendations:
            user_prompt += f"\n**추천 정보:** {recommendations}"
        
        user_prompt += "\n\n위 정보를 바탕으로 사용자의 질문에 대한 맞춤형 조언을 제공해주세요."

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = await self.chat_completion(messages, temperature=0.8)
            return response
            
        except Exception as e:
            return f"죄송합니다. 응답 생성 중 오류가 발생했습니다: {str(e)}"
    
    def validate_api_key(self) -> bool:
        """API 키 유효성 검증"""
        try:
            return bool(self.api_key and self.api_key.startswith('sk-'))
        except:
            return False
    
    async def test_connection(self) -> Dict[str, Any]:
        """OpenAI 연결 테스트"""
        try:
            # 간단한 테스트 요청
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello"}
            ]
            
            response = await self.chat_completion(messages, temperature=0.1)
            
            return {
                "status": "success",
                "model": self.model,
                "api_key_valid": True,
                "response_length": len(response)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "api_key_valid": False
            }