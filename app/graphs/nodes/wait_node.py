# app/graphs/nodes/wait_node.py
# 대기 상태 노드

from app.graphs.state import ChatState


class WaitNode:
    """대기 상태 노드"""

    def __init__(self):
        pass

    def create_node(self):
        """대기 상태 노드 생성"""
        async def wait_node(state: ChatState) -> ChatState:
            print("⏳ 대기 상태 - 메시지 입력 필요")
            return state
        
        return wait_node
