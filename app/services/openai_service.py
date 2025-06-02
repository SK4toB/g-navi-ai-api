# app/services/openai_service.py
from openai import AsyncOpenAI
import os
from typing import Optional, List, Dict, Any
from datetime import datetime

class OpenAIService:
    def __init__(self):
        # 환경변수에서 OpenAI API 키 가져오기
        api_key = os.getenv("OPENAI_API_KEY")
        print(api_key)
        if not api_key:
            raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다")
        
        # AsyncOpenAI 클라이언트 초기화
        self.client = AsyncOpenAI(api_key=api_key)
        
        # 기본 설정
        self.model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "1000"))
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    
    async def generate_response(
        self, 
        user_message: str, 
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        OpenAI API를 사용하여 응답 생성
        """
        try:
            # 메시지 구성
            messages = [
                {
                    "role": "system", 
                    "content": self._get_system_prompt(context)
                }
            ]
            
            # 대화 히스토리 추가 (있는 경우)
            if conversation_history:
                messages.extend(conversation_history)
            
            # 현재 사용자 메시지 추가
            messages.append({
                "role": "user",
                "content": user_message
            })
            
            # OpenAI API 호출 (새로운 방식)
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                presence_penalty=0.0,
                frequency_penalty=0.0
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            # 구체적인 에러 타입 확인
            error_message = str(e)
            if "rate_limit" in error_message.lower():
                raise Exception("API 호출 한도를 초과했습니다. 잠시 후 다시 시도해주세요.")
            elif "authentication" in error_message.lower() or "api_key" in error_message.lower():
                raise Exception("OpenAI API 인증에 실패했습니다. API 키를 확인해주세요.")
            elif "insufficient_quota" in error_message.lower():
                raise Exception("OpenAI API 사용량을 초과했습니다.")
            else:
                raise Exception(f"응답 생성 중 오류가 발생했습니다: {str(e)}")
    
    def _get_system_prompt(self, context: Optional[str] = None) -> str:
        """
        시스템 프롬프트 생성
        """
        base_prompt = """
        당신은 도움이 되고 친근한 AI 어시스턴트입니다.
        사용자의 질문에 정확하고 유용한 답변을 제공해주세요.
        
        응답 가이드라인:
        - 한국어로 응답해주세요
        - 친근하고 전문적인 톤을 유지해주세요
        - 구체적이고 실용적인 정보를 제공해주세요
        - 불확실한 정보는 추측하지 말고 모른다고 말해주세요
        """
        
        if context:
            base_prompt += f"\n\n추가 컨텍스트: {context}"
        
        return base_prompt
    
    async def generate_initial_greeting(self, user_info: Dict[str, Any]) -> str:
        """
        사용자 정보를 바탕으로 개인화된 초기 인사 메시지 생성
        """
        try:
            name = user_info.get('name', '사용자')
            projects = user_info.get('projects', [])
            skills = user_info.get('skills', [])
            
            # 프로젝트 정보 포맷팅
            project_info = ""
            if projects:
                project_names = [p.get('name', '프로젝트') for p in projects[:3]]
                project_info = f"진행 중인 프로젝트: {', '.join(project_names)}"
            
            # 스킬 정보 포맷팅
            skill_info = ""
            if skills:
                skill_info = f"보유 기술: {', '.join(skills[:5])}"
            
            prompt = f"""
            사용자 정보:
            - 이름: {name}
            {project_info}
            {skill_info}
            
            위 정보를 바탕으로 개인화된 인사 메시지를 생성해주세요.
            다음 조건을 만족해야 합니다:
            - 2-3문장으로 간결하게 작성
            - 사용자의 프로젝트나 스킬을 자연스럽게 언급
            - 어떤 도움을 줄 수 있는지 간략히 설명
            - 친근하고 전문적인 톤 유지
            """
            
            return await self.generate_response(prompt)
            
        except Exception as e:
            # 기본 인사 메시지 반환
            print(f"초기 인사 메시지 생성 실패: {e}")
            name = user_info.get('name', '사용자')
            return f"안녕하세요 {name}님! 저는 당신의 AI 어시스턴트입니다. 궁금한 것이 있으시면 언제든 물어보세요!"
    
    def format_conversation_history(
        self, 
        messages: List[Dict[str, Any]], 
        limit: int = 10
    ) -> List[Dict[str, str]]:
        """
        메모리 저장소의 메시지 형식을 OpenAI API 형식으로 변환
        """
        formatted_messages = []
        
        # 최근 메시지만 사용 (토큰 제한 고려)
        recent_messages = messages[-limit:] if len(messages) > limit else messages
        
        for msg in recent_messages:
            role = "user" if msg["message_type"] == "user" else "assistant"
            formatted_messages.append({
                "role": role,
                "content": msg["message"]
            })
        
        return formatted_messages