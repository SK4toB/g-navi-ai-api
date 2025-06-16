# app/graphs/graph_builder.py (조건부 분기 방식)

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing import Dict, Any
import asyncio

from app.graphs.state import ChatState
from app.graphs.nodes import (
    user_input_node, 
    retrieve_chat_history_node,
    analyze_intent_node,
    retrieve_additional_data_node,
    format_response_node,
    openai_response_node
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
        message_text = state.get("message_text", "")
        
        if message_text and message_text.strip():
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
        workflow.add_node("retrieve_chat_history", retrieve_chat_history_node.process)   # 1단계: 대화이력 검색
        workflow.add_node("analyze_intent", analyze_intent_node.process)                 # 2단계: 의도 분석
        workflow.add_node("retrieve_additional_data", retrieve_additional_data_node.process)  # 3단계: 추가 데이터 수집 
        workflow.add_node("format_response", format_response_node.process)               # 4단계: 응답 포맷팅
        workflow.add_node("openai_response", openai_response_node.process)
        workflow.add_node("wait_state", self._create_wait_node())      # 대기 상태
        
        # 시작점
        workflow.set_entry_point("message_check")
        
        # 조건부 분기
        workflow.add_conditional_edges(
            "message_check",
            self._should_process_message,
            {
                "process": "retrieve_chat_history",  # 메시지 있으면 1단계부터 처리
                "wait": "wait_state"           # 메시지 없으면 대기
            }
        )
        
        # 메인 처리 플로우
        workflow.add_edge("retrieve_chat_history", "analyze_intent")           # 1단계 → 2단계
        workflow.add_edge("analyze_intent", "retrieve_additional_data")        # 2단계 → 3단계
        workflow.add_edge("retrieve_additional_data", "format_response")       # 3단계 → 4단계
        workflow.add_edge("format_response", "openai_response")
        
        # 처리 완료 후 종료
        workflow.add_edge("openai_response", END)
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