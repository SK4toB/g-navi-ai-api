# app/graphs/nodes/openai_response_node.py

import os
from typing import List, Dict, Any
from app.graphs.state import ChatState

# 전역 대화 히스토리 매니저 (싱글톤)
_history_manager = None

def get_history_manager():
    """대화 히스토리 매니저 싱글톤 인스턴스 반환"""
    global _history_manager
    if _history_manager is None:
        from app.services.conversation_history_manager import ConversationHistoryManager
        _history_manager = ConversationHistoryManager(max_messages=20)
    return _history_manager

async def process(state: ChatState) -> ChatState:
    """OpenAI를 활용한 응답 생성 노드 - 세션 기반 대화 히스토리"""
    print("OpenAI Response Node (세션 기반): 응답 생성 시작")
    
    message_text = state.get("message_text", "")
    user_info = state.get("user_info", {})
    user_name = user_info.get("name", "사용자")
    member_id = state.get("member_id", "")
    conversation_id = state.get("conversation_id", "")
    
    # OpenAI API 키 확인
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("⚠️ OpenAI API 키가 없습니다. 기본 응답을 사용합니다.")
        bot_message = f"안녕하세요 {user_name}님! OpenAI API 키가 설정되지 않아 기본 응답을 드립니다: '{message_text}'"
        state["bot_message"] = bot_message
        return state
    
    try:
        from openai import AsyncOpenAI
        
        # OpenAI 클라이언트 초기화
        client = AsyncOpenAI(api_key=api_key)
        model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "1000"))
        temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
        
        print(f"OpenAI API 호출 중... (모델: {model})")
        
        # 대화 히스토리 매니저에서 이전 대화 가져오기
        history_manager = get_history_manager()
        conversation_history = history_manager.get_history(conversation_id)
        
        # 시스템 프롬프트 구성
        system_prompt = _build_system_prompt(user_name, member_id, user_info)
        
        # 메시지 구성 (시스템 + 대화 히스토리 + 현재 메시지)
        messages = _build_messages_for_openai(system_prompt, conversation_history, message_text)
        
        print(f"대화 히스토리: {len(conversation_history)}개 이전 메시지")
        print(f"OpenAI 전송 메시지 수: {len(messages)}")
        
        # OpenAI API 호출
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        # 응답 추출
        bot_message = response.choices[0].message.content.strip()
        
        print(f"OpenAI 응답 생성 완료: {bot_message[:100]}...")
        print(f"토큰 사용량 - 입력: {response.usage.prompt_tokens}, 출력: {response.usage.completion_tokens}, 총: {response.usage.total_tokens}")
        
        # 대화 히스토리에 현재 대화 저장
        history_manager.add_message(conversation_id, "user", message_text, {
            "member_id": member_id,
            "user_name": user_name
        })
        history_manager.add_message(conversation_id, "assistant", bot_message, {
            "model": model,
            "tokens_used": response.usage.total_tokens
        })
        
        state["bot_message"] = bot_message
        
    except Exception as e:
        print(f"OpenAI API 호출 실패: {e}")
        import traceback
        print(f"상세 에러: {traceback.format_exc()}")
        # 폴백 응답
        fallback_message = f"죄송합니다 {user_name}님. 일시적인 오류로 응답 생성에 실패했습니다. '{message_text}'에 대해 다시 말씀해 주시겠어요?"
        state["bot_message"] = fallback_message
        
        # 실패한 경우에도 사용자 메시지는 히스토리에 저장
        history_manager = get_history_manager()
        history_manager.add_message(conversation_id, "user", message_text, {
            "member_id": member_id,
            "user_name": user_name
        })
        history_manager.add_message(conversation_id, "assistant", fallback_message, {
            "error": str(e),
            "fallback": True
        })
    
    print(f"OpenAI Response Node 완료")
    return state


def _build_system_prompt(user_name: str, member_id: str, user_info: Dict[str, Any]) -> str:
    """시스템 프롬프트 구성"""
    
    # 사용자 프로젝트 정보 간략히 포함
    projects = user_info.get("projects", [])
    project_summary = ""
    if projects:
        project_count = len(projects)
        domains = list(set([p.get("domain", "") for p in projects[:3] if p.get("domain")]))
        roles = list(set([p.get("role", "") for p in projects[:3] if p.get("role")]))
        
        project_summary = f"\n- 총 {project_count}개 프로젝트 경험"
        if domains:
            project_summary += f"\n- 주요 도메인: {', '.join(domains)}"
        if roles:
            project_summary += f"\n- 주요 역할: {', '.join(roles)}"
    
    system_prompt = f"""당신은 SK AX 사내 커리어패스 전문 상담사 "G.Navi"입니다.

사용자 정보:
- 이름: {user_name}
- 회원ID: {member_id}{project_summary}

응답 가이드라인:
1. 친근하고 전문적인 톤 유지
2. 커리어패스, 기술 성장, 프로젝트 경험과 관련된 구체적인 조언 제공
3. 한국어로 응답
4. 이전 대화 내용을 참고하여 연속성 있는 상담 진행
5. 필요시 구체적인 질문으로 더 깊이 있는 상담 유도
6. 사용자의 현재 상황과 목표를 고려한 개인화된 조언
7. 응답은 2-4문장으로 간결하되 유용한 내용 포함"""

    return system_prompt


def _build_messages_for_openai(
    system_prompt: str, 
    conversation_history: List[Dict[str, str]], 
    current_message: str
) -> List[Dict[str, str]]:
    """OpenAI API용 메시지 구성"""
    
    messages = [{"role": "system", "content": system_prompt}]
    
    # 이전 대화 히스토리 추가
    messages.extend(conversation_history)
    
    # 현재 사용자 메시지 추가
    messages.append({"role": "user", "content": current_message})
    
    return messages