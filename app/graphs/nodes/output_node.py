# app/graphs/nodes/output_node.py

from app.graphs.state import ChatState

async def process(state: ChatState) -> ChatState:
    """매우 간단한 테스트용 응답 생성"""
    print("graphs/nodes/output_node.py")
    
    user_message = state.get("user_message", "")
    user_info = state.get("user_info", {})
    user_name = user_info.get("name", "사용자")
    
    # 매우 간단한 응답
    if user_message:
        response = f"[테스트 응답] {user_name}님의 메시지 '{user_message}'를 잘 받았습니다."
    else:
        response = f"[테스트 응답] 안녕하세요 {user_name}님! 테스트 모드입니다."
    
    state["final_response"] = response
    print(f"OutputNode 완료: {response}")
    
    return state
