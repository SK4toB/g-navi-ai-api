# app/graphs/graph_builder.py

from langgraph.graph import StateGraph, END
from typing import Dict, Any
import asyncio

from app.graphs.state import ChatState
from app.graphs.nodes import (
    intent_node, embedding_node, memory_node,
    similarity_node, profiling_node, connection_node, output_node
)

class ChatGraphBuilder:
    """
    LangGraph 빌더 - 노드들을 연결해서 워크플로우 구성
    팀원이 주로 작업할 부분
    """
    
    def __init__(self):
        print("ChatGraphBuilder 초기화")
    
    async def build_chat_graph(self, room_id: str, user_info: Dict[str, Any]):
        """
        채팅용 LangGraph 빌드
        노드들을 연결해서 워크플로우 생성
        """
        print(f"🔧 LangGraph 빌드 시작: {room_id}")
        
        # StateGraph 생성
        workflow = StateGraph(ChatState)
        
        # 노드들 추가 (현재는 빈 구현)
        workflow.add_node("intent_analysis", intent_node.process)
        workflow.add_node("embedding", embedding_node.process)
        workflow.add_node("memory_search", memory_node.process)
        workflow.add_node("similarity_check", similarity_node.process)
        workflow.add_node("profiling", profiling_node.process)
        workflow.add_node("connection_check", connection_node.process)
        workflow.add_node("output_generation", output_node.process)
        
        # 워크플로우 흐름 정의
        workflow.set_entry_point("intent_analysis")
        
        # 순차 연결 (일단 간단하게)
        workflow.add_edge("intent_analysis", "embedding")
        workflow.add_edge("embedding", "memory_search")
        workflow.add_edge("memory_search", "similarity_check")
        workflow.add_edge("similarity_check", "profiling")
        workflow.add_edge("profiling", "connection_check")
        workflow.add_edge("connection_check", "output_generation")
        workflow.add_edge("output_generation", END)
        
        # 컴파일
        compiled_graph = workflow.compile()
        print(f"LangGraph 컴파일 완료: {room_id}")
        
        return compiled_graph
