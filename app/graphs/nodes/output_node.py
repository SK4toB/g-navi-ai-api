# app/graphs/nodes/output_node.py

from app.graphs.state import ChatState

async def process(state: ChatState) -> ChatState:
    """응답 생성 노드 - 통일된 필드명 사용"""
    print("OutputNode: 응답 생성 시작")
    
    message_text = state.get("message_text", "")
    user_info = state.get("user_info", {})
    user_name = user_info.get("name", "사용자")
    
    # 간단한 응답 생성 (나중에 OpenAI 연동으로 대체)
    if message_text:
        bot_message = f"[테스트 응답] {user_name}님의 메시지 '{message_text}'를 잘 받았습니다."
    else:
        bot_message = f"[테스트 응답] 안녕하세요 {user_name}님! 테스트 모드입니다."
    
    state["bot_message"] = bot_message
    print(f"OutputNode 완료: {bot_message}")
    
    return state
