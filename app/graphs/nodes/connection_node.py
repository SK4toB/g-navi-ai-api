# 추가 연결 판단 agent

# app/graphs/nodes/connection_node.py
from typing import Dict, Any
from app.graphs.state import ChatState

async def process(state: ChatState) -> ChatState:
    """추가 연결 여부 판단 노드"""
    print(f"Connection Check")
    
    # TODO: 연결 제안 로직 구현
    # 현재는 기본 제안 반환
    state["connection_suggestions"] = [
        "Backend 개발 전문가와 연결",
        "프로젝트 관리 멘토와 연결"
    ]
    
    return state