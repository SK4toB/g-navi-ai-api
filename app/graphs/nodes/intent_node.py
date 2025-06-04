# 의도 파악 agent

# app/graphs/nodes/intent_node.py
from typing import Dict, Any
from app.graphs.state import ChatState

async def process(state: ChatState) -> ChatState:
    """사용자 발화 의도 분석 노드"""
    print(f"Intent Analysis: {state.get('user_message', '')[:50]}...")
    
    # TODO: 실제 의도 분석 로직 구현
    # 현재는 기본값 반환
    state["intent"] = "career_consultation"
    
    return state