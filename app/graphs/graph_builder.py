# app/graphs/graph_builder.py (조건부 분기 방식)

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
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
    조건부 분기 방식 LangGraph 빌더
    interrupt 대신 상태 기반 조건부 실행
    """
    
    def __init__(self):
        self.memory_saver = MemorySaver()
        print("ChatGraphBuilder __init__")
    
    def _should_process_message(self, state: ChatState) -> str:
        """
        메시지 처리 여부 결정
        """
        message_text = state.get("message_text ", "")
        
        if message_text and message_text .strip():
            print(f"메시지 있음 → 처리 시작: {message_text[:30]}...")
            return "process"
        else:
            print("메시지 없음 → 대기")
            return "wait"
    
    async def build_persistent_chat_graph(self, conversation_id: str, user_info: Dict[str, Any]):
        """
        LangGraph 빌드
        """
        print(f"{conversation_id} LangGraph 빌드 시작")
        
        # StateGraph 생성
        workflow = StateGraph(ChatState)
        
        # 노드들 추가
        workflow.add_node("message_check", user_input_node.process)     # 메시지 확인
        workflow.add_node("intent_analysis", intent_node.process)
        workflow.add_node("embedding", embedding_node.process)
        workflow.add_node("memory_search", memory_node.process)
        workflow.add_node("similarity_check", similarity_node.process)
        workflow.add_node("profiling", profiling_node.process)
        workflow.add_node("connection_check", connection_node.process)
        workflow.add_node("output_generation", output_node.process)
        workflow.add_node("wait_state", self._create_wait_node())      # 대기 상태
        
        # 시작점
        workflow.set_entry_point("message_check")
        
        # 조건부 분기
        workflow.add_conditional_edges(
            "message_check",
            self._should_process_message,
            {
                "process": "intent_analysis",  # 메시지 있으면 처리
                "wait": "wait_state"           # 메시지 없으면 대기
            }
        )
        
        # 메인 처리 플로우
        workflow.add_edge("intent_analysis", "embedding")
        workflow.add_edge("embedding", "memory_search")
        workflow.add_edge("memory_search", "similarity_check")
        workflow.add_edge("similarity_check", "profiling")
        workflow.add_edge("profiling", "connection_check")
        workflow.add_edge("connection_check", "output_generation")
        
        # 처리 완료 후 종료
        workflow.add_edge("output_generation", END)
        workflow.add_edge("wait_state", END)
        
        # 컴파일 (interrupt 없음)
        compiled_graph = workflow.compile(
            checkpointer=self.memory_saver
            # interrupt 완전 제거
        )
        
        print(f"{conversation_id} LangGraph 컴파일 완료")
        return compiled_graph
    
    def _create_wait_node(self):
        """대기 상태 노드 생성"""
        async def wait_node(state: ChatState) -> ChatState:
            print("대기 상태 (메시지 입력 필요)")
            return state
        
        return wait_node