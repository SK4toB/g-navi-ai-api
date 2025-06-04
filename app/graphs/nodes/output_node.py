# app/graphs/nodes/output_node.py

from typing import Dict, Any
import os
from app.graphs.state import ChatState

class OutputNode:
    """최종 AI 응답 생성 노드"""
    
    def __init__(self):
        self.openai_client = None
        self._init_openai()
    
    def _init_openai(self):
        """OpenAI 클라이언트 초기화"""
        try:
            from openai import AsyncOpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.openai_client = AsyncOpenAI(api_key=api_key)
                self.model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
                self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "1000"))
                self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
                print("OutputNode OpenAI 연결 완료")
        except Exception as e:
            print(f"OutputNode OpenAI 초기화 실패: {e}")
    
    async def process(self, state: ChatState) -> ChatState:
        """실제 AI 응답 생성"""
        print(f"📝 OutputNode AI 응답 생성 시작")
        print(f"🔍 State 내용: {list(state.keys())}")
        
        user_message = state.get("user_message", "")
        intent = state.get("intent", "general")
        profiling_data = state.get("profiling_data", {})
        memory_results = state.get("memory_results", [])
        connection_suggestions = state.get("connection_suggestions", [])
        
        print(f"📨 사용자 메시지: '{user_message}'")
        print(f"🎯 의도: {intent}")
        print(f"🔗 OpenAI 클라이언트 상태: {self.openai_client is not None}")
        
        # 사용자 정보 추출
        user_info = state.get("user_info", {})
        user_name = user_info.get("name", "사용자")
        projects = user_info.get("projects", [])
        
        print(f"👤 사용자명: {user_name}")
        print(f"📁 프로젝트 수: {len(projects)}")
        
        if not user_message:
            # 빈 메시지인 경우 (초기 상태)
            print("⚠️ 빈 메시지 - 기본 응답 반환")
            state["final_response"] = "안녕하세요! 무엇을 도와드릴까요?"
            return state
        
        # AI 응답 생성
        try:
            print("🤖 _generate_ai_response 호출 시작")
            ai_response = await self._generate_ai_response(
                user_message=user_message,
                user_name=user_name,
                projects=projects,
                intent=intent,
                memory_results=memory_results,
                connection_suggestions=connection_suggestions
            )
            
            state["final_response"] = ai_response
            print(f"✅ OutputNode AI 응답 생성 완료: {ai_response[:100]}...")
            
        except Exception as e:
            print(f"❌ OutputNode AI 응답 생성 실패: {type(e).__name__}: {e}")
            import traceback
            print(f"📋 상세 에러: {traceback.format_exc()}")
            state["final_response"] = f"죄송합니다. 현재 '{user_message}'에 대한 답변을 준비하는 중입니다. 잠시 후 다시 시도해주세요."
        
        return state
    
    async def _generate_ai_response(
        self, 
        user_message: str, 
        user_name: str, 
        projects: list,
        intent: str,
        memory_results: list,
        connection_suggestions: list
    ) -> str:
        """OpenAI를 활용한 실제 AI 응답 생성"""
        
        if not self.openai_client:
            return f"안녕하세요 {user_name}님! '{user_message}'에 대해 답변드리겠습니다. (OpenAI 연결이 필요합니다)"
        
        # 사용자 컨텍스트 구성
        context_info = self._build_context(user_name, projects, memory_results, connection_suggestions)
        
        # 의도별 프롬프트 생성
        system_prompt = self._get_system_prompt(intent)
        user_prompt = self._build_user_prompt(user_message, context_info)
        
        try:
            print("🤖 OpenAI 응답 생성 중...")
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            ai_response = response.choices[0].message.content.strip()
            print(f"✅ OpenAI 응답 완료: {len(ai_response)}자")
            return ai_response
            
        except Exception as e:
            print(f"❌ OpenAI API 호출 실패: {e}")
            return f"죄송합니다, {user_name}님. 현재 시스템에 일시적인 문제가 있어 상세한 답변을 드리기 어렵습니다. 간단히 말씀드리면 '{user_message}'에 대해 도움을 드릴 수 있습니다."
    
    def _build_context(self, user_name: str, projects: list, memory_results: list, connection_suggestions: list) -> str:
        """사용자 컨텍스트 정보 구성"""
        context_parts = [f"사용자명: {user_name}"]
        
        # 프로젝트 경험 요약
        if projects:
            domains = [p.get("domain", "") for p in projects]
            roles = [p.get("role", "") for p in projects]
            context_parts.append(f"주요 경험 도메인: {', '.join(set(domains))}")
            context_parts.append(f"주요 역할: {', '.join(set(roles))}")
            context_parts.append(f"총 프로젝트 수: {len(projects)}개")
        
        # 과거 대화 컨텍스트 (TODO: 실제 구현 시 추가)
        if memory_results:
            context_parts.append(f"과거 대화 참고사항: {len(memory_results)}건")
        
        # 연결 제안사항
        if connection_suggestions:
            context_parts.append(f"연결 제안: {', '.join(connection_suggestions)}")
        
        return '\n'.join(context_parts)
    
    def _get_system_prompt(self, intent: str) -> str:
        """의도별 시스템 프롬프트"""
        base_prompt = """당신은 SK AX의 전문 커리어 상담사 'G.Navi'입니다. 
사내 구성원들의 커리어 성장과 발전을 도와주는 역할을 합니다.

기본 원칙:
1. 친근하고 전문적인 톤으로 상담
2. 구체적이고 실용적인 조언 제공
3. 사용자의 경험과 배경을 고려한 개인화된 답변
4. 2-3문단으로 구조화된 답변 (너무 길지 않게)
5. 한국어로 자연스럽게 답변"""

        intent_specific = {
            "career_consultation": "\n특히 커리어 상담에 집중하여 성장 방향, 스킬 개발, 역할 전환 등에 대해 조언해주세요.",
            "skill_development": "\n특히 기술 및 역량 개발에 집중하여 학습 방향과 방법에 대해 조언해주세요.",
            "project_advice": "\n특히 프로젝트 관련 조언에 집중하여 경험 활용과 향후 방향에 대해 조언해주세요.",
            "general": "\n사용자의 질문 의도를 파악하여 가장 도움이 되는 방향으로 답변해주세요."
        }
        
        return base_prompt + intent_specific.get(intent, intent_specific["general"])
    
    def _build_user_prompt(self, user_message: str, context_info: str) -> str:
        """사용자 프롬프트 구성"""
        return f"""다음은 사용자의 질문과 배경 정보입니다:

=== 사용자 질문 ===
{user_message}

=== 사용자 배경 정보 ===
{context_info}

위 정보를 바탕으로 사용자에게 도움이 되는 답변을 생성해주세요."""

# 싱글톤 인스턴스 생성
_output_node_instance = OutputNode()

# 기존 인터페이스 호환성을 위한 함수
async def process(state: ChatState) -> ChatState:
    """기존 노드 인터페이스와 호환되는 래퍼 함수"""
    return await _output_node_instance.process(state)