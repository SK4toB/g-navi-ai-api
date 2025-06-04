# app/graphs/nodes/user_input_node.py

from typing import Dict, Any
from app.graphs.state import ChatState

async def process(state: ChatState) -> ChatState:
    """
    사용자 입력 대기 노드
    이 노드에서 중단되어 RESTful API를 통한 입력을 기다림
    """
    print(f"👤 사용자 입력 대기: room_id={state.get('room_id')}")
    
    # 사용자 메시지가 있는지 확인
    user_message = state.get("user_message", "")
    
    if user_message:
        print(f"📝 사용자 메시지 수신: {user_message[:50]}...")
        # 메시지가 있으면 다음 노드로 진행
        state["input_received"] = True
    else:
        print("⏳ 사용자 입력 대기 중...")
        # 메시지가 없으면 대기 상태
        state["input_received"] = False
    
    return state