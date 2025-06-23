# app/graphs/nodes/openai_response_node.py

import os
from typing import List, Dict, Any
from app.graphs.state import ChatState

async def process(state: ChatState) -> ChatState:
    """OpenAI를 활용한 응답 생성 노드 - 의존성 주입 방식"""
    print("OpenAI Response Node (의존성 주입): 응답 생성 시작")
    
    message_text = state.get("message_text", "")
    user_info = state.get("user_info", {})
    user_name = user_info.get("name", "사용자")
    member_id = state.get("member_id", "")
    conversation_id = state.get("conversation_id", "")
    
    # OpenAI API 키 확인
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("OpenAI API 키가 없습니다. 기본 응답을 사용합니다.")
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
        
        # 의존성 주입을 통한 대화 히스토리 매니저 얻기
        from app.core.dependencies import get_service_container
        container = get_service_container()
        history_manager = container.history_manager
        
        conversation_history = history_manager.get_history(conversation_id)
        
        print(f"대화 히스토리: {len(conversation_history)}개 이전 메시지")
        if conversation_history:
            print(f"히스토리 미리보기:")
            for i, msg in enumerate(conversation_history[-3:], 1):  # 최근 3개만 미리보기
                role = msg.get("role", "unknown")
                content = msg.get("content", "")[:50]
                print(f"  {i}. [{role}] {content}...")
        
        # 이전 대화 요약 요청인지 확인
        is_history_request = _is_asking_for_history(message_text)
        
        # 시스템 프롬프트 구성 (대화 히스토리 정보 포함)
        system_prompt = _build_system_prompt(user_name, member_id, user_info, len(conversation_history), is_history_request)
        
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
        from app.core.dependencies import get_service_container
        container = get_service_container()
        history_manager = container.history_manager
        
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


def _build_system_prompt(user_name: str, member_id: str, user_info: Dict[str, Any], history_count: int = 0, is_history_request: bool = False) -> str:
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
    
    # 대화 히스토리 정보 추가
    history_info = ""
    if history_count > 0:
        history_info = f"\n\n이전 대화 내역: {history_count}개 메시지가 있습니다. 이전 대화 내용을 참고하여 연속성 있는 상담을 진행해주세요."
        
        if is_history_request:
            history_info += f"\n\n**특별 지시**: 사용자가 이전 대화 내용에 대해 질문하고 있습니다. 이전 대화 내역을 구체적으로 요약하여 제공해주세요."
    
    system_prompt = f"""당신은 SK AX 사내 커리어패스 전문 상담사 "G.Navi"입니다.

사용자 정보:
- 이름: {user_name}
- 회원ID: {member_id}{project_summary}{history_info}

응답 가이드라인:
1. 친근하고 전문적인 톤 유지
2. 커리어패스, 기술 성장, 프로젝트 경험과 관련된 구체적인 조언 제공
3. 한국어로 응답
4. **이전 대화 내용을 적극적으로 참고하여 연속성 있는 상담 진행**
5. 사용자가 이전 질문이나 대화를 언급할 때는 구체적으로 대답해주세요
6. 필요시 구체적인 질문으로 더 깊이 있는 상담 유도
7. 사용자의 현재 상황과 목표를 고려한 개인화된 조언
8. 응답은 2-4문장으로 간결하되 유용한 내용 포함"""

    return system_prompt


def _is_asking_for_history(message: str) -> bool:
    """사용자가 이전 대화 내역을 요청하는지 확인"""
    history_keywords = [
        "이전", "전에", "앞서", "과거", "예전",
        "질문했던", "말했던", "얘기했던", "상담했던",
        "대화", "히스토리", "내역", "기록",
        "무엇을", "뭘", "어떤", "언제"
    ]
    
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in history_keywords)


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


# 하위 호환성을 위한 함수 (DEPRECATED)
def get_history_manager():
    """DEPRECATED: app.core.dependencies.get_history_manager 사용"""
    from app.core.dependencies import get_service_container
    container = get_service_container()
    return container.history_manager