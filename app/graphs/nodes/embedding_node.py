# 질문 벡터화 agent

# app/graphs/nodes/embedding_node.py
from typing import Dict, Any
from app.graphs.state import ChatState

async def process(state: ChatState) -> ChatState:
    """사용자 입력 벡터화 처리 노드"""
    print(f"📊 Embedding: {state.get('user_message', '')[:50]}...")
    
    # TODO: 실제 임베딩 로직 구현
    # 현재는 더미 벡터 반환
    state["embedding_vector"] = [0.1] * 768  # 768차원 더미 벡터
    
    return state