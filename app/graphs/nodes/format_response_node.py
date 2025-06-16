# G.Navi 5단계: 응답 포맷팅

from app.graphs.state import ChatState

async def process(state: ChatState) -> ChatState:
    """G.Navi 5단계: 응답 포맷팅"""
    print("=== G.Navi 5단계: 응답 포맷팅 ===")
    
    # TODO: 응답 포맷팅 로직 구현
    state["final_response"] = {}
    
    # 최종 봇 메시지 생성 (기본값)
    user_info = state.get("user_info", {})
    user_name = user_info.get("name", "사용자")
    message_text = state.get("message_text", "")
    
    state["bot_message"] = f"안녕하세요 {user_name}님! '{message_text}'에 대한 G.Navi 5단계 처리가 완료되었습니다."
    
    return state