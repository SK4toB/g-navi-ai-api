# app/graphs/graph_builder.py

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver  # 상태 저장용
from typing import Dict, Any
import asyncio

from app.graphs.state import ChatState
from app.graphs.nodes import (
    intent_node, embedding_node, memory_node,
    similarity_node, profiling_node, connection_node, output_node,
    user_input_node
)

class ChatGraphBuilder:
    """
    지속적인 대화형 LangGraph 빌더
    채팅방 생성 시 시작되어 계속 실행 상태 유지
    """
    
    def __init__(self):
        print("ChatGraphBuilder 초기화")
        self.memory_saver = MemorySaver()  # 상태 저장소
    
    async def build_persistent_chat_graph(self, room_id: str, user_info: Dict[str, Any]):
        """
        지속적인 채팅용 LangGraph 빌드
        순환 구조로 사용자 입력을 계속 대기
        """
        print(f"🔧 지속적 LangGraph 빌드 시작: {room_id}")
        
        # StateGraph 생성
        workflow = StateGraph(ChatState)
        
        # 노드들 추가
        workflow.add_node("user_input_wait", user_input_node.process)     # 사용자 입력 대기
        workflow.add_node("intent_analysis", intent_node.process)
        workflow.add_node("embedding", embedding_node.process)
        workflow.add_node("memory_search", memory_node.process)
        workflow.add_node("similarity_check", similarity_node.process)
        workflow.add_node("profiling", profiling_node.process)
        workflow.add_node("connection_check", connection_node.process)
        workflow.add_node("output_generation", output_node.process)
        
        # 순환 워크플로우 흐름 정의
        workflow.set_entry_point("user_input_wait")
        
        # 메인 처리 플로우
        workflow.add_edge("user_input_wait", "intent_analysis")
        workflow.add_edge("intent_analysis", "embedding")
        workflow.add_edge("embedding", "memory_search")
        workflow.add_edge("memory_search", "similarity_check")
        workflow.add_edge("similarity_check", "profiling")
        workflow.add_edge("profiling", "connection_check")
        workflow.add_edge("connection_check", "output_generation")
        
        # 순환: 답변 생성 후 다시 입력 대기로
        workflow.add_edge("output_generation", "user_input_wait")
        
        # 컴파일 (상태 저장소 포함)
        compiled_graph = workflow.compile(
            checkpointer=self.memory_saver,
            interrupt_before=["user_input_wait"]  # 사용자 입력 전에 중단
        )
        
        print(f"지속적 LangGraph 컴파일 완료: {room_id}")
        return compiled_graph
