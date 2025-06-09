# app/graphs/nodes/user_input_node.py

from typing import Dict, Any
from app.graphs.state import ChatState

async def process(state: ChatState) -> ChatState:
    """
    사용자 입력 대기 노드
    통일된 필드명 사용: message_text, member_id
    """
    print("graphs/nodes/user_input_node.py")
    print(f"conversation_id: {state.get('conversation_id')}")
    print(f"message_text: '{state.get('message_text', '')}'")
    print(f"member_id: {state.get('member_id')}")
    print(f"모든 state 키: {list(state.keys())}")
    
    # 사용자 메시지 확인
    message_text = state.get("message_text", "")
    
    if message_text:
        print(f"사용자 메시지 있음: {message_text[:50]}...")
        print(f"UserInputNode → IntentNode로 진행")
    else:
        print("사용자 입력 대기 중... (여기서 중단됨)")
    
    print(f"UserInputNode 완료")
    
    # 상태는 그대로 다음 노드로 전달
    return state