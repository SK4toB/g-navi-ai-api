# 메모리 벡터 검색 agent

# app/graphs/nodes/memory_node.py
from typing import Dict, Any
from app.graphs.state import ChatState

async def process(state: ChatState) -> ChatState:
    """과거 대화 메모리 검색 노드"""
    print(f"🧠 Memory Search: conversation_id={state.get('conversation_id')}")
    
    # TODO: Vector DB에서 과거 대화 검색
    # 현재는 빈 결과 반환
    state["memory_results"] = []
    
    return state
