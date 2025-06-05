# app/graphs/nodes/user_input_node.py

from typing import Dict, Any
from app.graphs.state import ChatState

async def process(state: ChatState) -> ChatState:
    """
    사용자 입력 대기 노드
    이 노드에서 중단되어 RESTful API를 통한 입력을 기다림
    """
    print("graphs/nodes/user_input_node.py")
    print(f"room_id: {state.get('room_id')}")
    print(f"user_message: '{state.get('user_message', '')}'")
    print(f"모든 state 키: {list(state.keys())}")
    
    # 사용자 메시지 확인
    user_message = state.get("user_message", "")
    
    if user_message:
        print(f"사용자 메시지 있음: {user_message[:50]}...")
        print(f"UserInputNode → IntentNode로 진행")
    else:
        print("사용자 입력 대기 중... (여기서 중단됨)")
    
    print(f"🏁 UserInputNode 완료")
    
    # 상태는 그대로 다음 노드로 전달
    return state