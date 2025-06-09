# 유사도 조사 agent

# app/graphs/nodes/similarity_node.py
from typing import Dict, Any
from app.graphs.state import ChatState

async def process(state: ChatState) -> ChatState:
    """유사 발화/상황 판단 노드"""
    print(f"🔍 Similarity Check")
    
    # TODO: 실제 유사도 계산 로직 구현
    # 현재는 기본값 반환
    state["similarity_score"] = 0.8
    
    return state
