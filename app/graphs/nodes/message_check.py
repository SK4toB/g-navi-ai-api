# app/graphs/nodes/message_check.py
# 메시지 확인 및 상태 초기화 노드

from app.graphs.state import ChatState


class MessageCheckNode:
    """메시지 확인 및 상태 초기화 노드"""

    def __init__(self):
        pass

    def create_node(self):
        """메시지 확인 및 상태 초기화 노드 생성"""
        async def message_check_node(state: ChatState) -> ChatState:
            print("📝 메시지 확인 및 상태 초기화")
            
            # 상태 초기화
            state.setdefault("chat_history_results", [])
            state.setdefault("intent_analysis", {})
            state.setdefault("career_cases", [])
            state.setdefault("external_trends", [])
            state.setdefault("final_response", {})
            state.setdefault("processing_log", [])
            state.setdefault("error_messages", [])
            state.setdefault("total_processing_time", 0.0)
            
            return state
        
        return message_check_node
