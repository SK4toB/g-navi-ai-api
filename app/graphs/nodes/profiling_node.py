# Self Profiling agent

# app/graphs/nodes/profiling_node.py
from typing import Dict, Any
from app.graphs.state import ChatState

async def process(state: ChatState) -> ChatState:
    """사용자 Self-Profiling 처리 노드"""
    print(f"👤 Profiling: member_id={state.get('member_id')}")
    
    # TODO: 사용자 프로파일링 로직 구현
    # 현재는 기본 데이터 반환
    state["profiling_data"] = {
        "member_id": state.get("member_id"),
        "profile_updated": True
    }
    
    return state