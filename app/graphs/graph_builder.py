# app/graphs/graph_builder.py
# G.Navi AgentRAG 시스템의 그래프 빌더 (5단계 워크플로우)

import logging
from datetime import datetime
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing import Dict, Any

from app.graphs.state import ChatState
from app.graphs.agents.retriever import CareerEnsembleRetrieverAgent as Retriever
from app.graphs.agents.analyzer import IntentAnalysisAgent as Analyzer
from app.graphs.agents.formatter import ResponseFormattingAgent as Formatter

# 새로 분리된 node 클래스들 import
from app.graphs.nodes.message_check import MessageCheckNode
from app.graphs.nodes.chat_history import ChatHistoryNode
from app.graphs.nodes.intent_analysis import IntentAnalysisNode
from app.graphs.nodes.data_retrieval import DataRetrievalNode
from app.graphs.nodes.response_formatting import ResponseFormattingNode
from app.graphs.nodes.diagram_generation import DiagramGenerationNode
from app.graphs.nodes.report_generation import ReportGenerationNode
from app.graphs.nodes.wait_node import WaitNode


class ChatGraphBuilder:
    """
    G.Navi AgentRAG 시스템의 LangGraph 빌더
    6단계 워크플로우: 히스토리 관리 → 의도 분석 → 데이터 검색 → 응답 포맷팅 → 다이어그램 생성 → 보고서 생성
    """
    
    def __init__(self):
        print("ChatGraphBuilder 초기화 (G.Navi AgentRAG)")
        self.logger = logging.getLogger(__name__)
        self.memory_saver = MemorySaver()
        
        # 세션별 정보 저장소 추가
        self.session_store = {}  # conversation_id -> {"user_info": ..., "metadata": ...}
        
        # G.Navi 에이전트들 초기화
        self.career_retriever_agent = Retriever()
        self.intent_analysis_agent = Analyzer()
        self.response_formatting_agent = Formatter()
        
        # 새로 분리된 node 클래스들 초기화
        self.message_check_node = MessageCheckNode()
        self.chat_history_node = ChatHistoryNode(self)
        self.intent_analysis_node = IntentAnalysisNode(self)
        self.data_retrieval_node = DataRetrievalNode()
        self.response_formatting_node = ResponseFormattingNode(self)
        self.diagram_generation_node = DiagramGenerationNode()
        self.report_generation_node = ReportGenerationNode()
        self.wait_node = WaitNode()
    
    def _should_process_message(self, state: ChatState) -> str:
        """메시지 처리 여부 결정"""
        # 1. 메시지 검증 실패 상태 확인 (우선순위)
        workflow_status = state.get("workflow_status", "")
        if workflow_status == "validation_failed":
            print("메시지 검증 실패 → 워크플로우 종료")
            return "wait"
        
        # 2. final_response에 validation_failed가 있는 경우도 확인
        final_response = state.get("final_response", {})
        if final_response.get("validation_failed", False):
            print("메시지 검증 실패 (final_response) → 워크플로우 종료")
            return "wait"
        
        # 3. 메시지 존재 여부 확인
        user_question = state.get("user_question", "")
        if user_question and user_question.strip():
            print(f"메시지 있음 → 처리 시작: {user_question[:30]}...")
            return "process"
        else:
            print("메시지 없음 → 대기")
            return "wait"
    
    def get_session_info(self, conversation_id: str) -> Dict[str, Any]:
        """세션 정보 조회"""
        return self.session_store.get(conversation_id, {})
    
    def get_user_info_from_session(self, state: ChatState) -> Dict[str, Any]:
        """상태에서 사용자 정보 추출 (우선순위: state > session_store)"""
        # 1. state에서 user_data 확인
        user_data = state.get("user_data", {})
        if user_data:
            return user_data
        
        # 2. session_id로 session_store에서 조회
        session_id = state.get("session_id", "")
        if session_id:
            session_info = self.get_session_info(session_id)
            return session_info.get("user_info", {})
        
        # 3. 기본값 반환
        return {}
    
    def close_session(self, conversation_id: str):
        """세션 정보 정리"""
        if conversation_id in self.session_store:
            del self.session_store[conversation_id]
            print(f"📝 GraphBuilder 세션 정보 삭제: {conversation_id}")
    
    def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """모든 세션 정보 조회 (디버깅용)"""
        return self.session_store.copy()
    
    async def build_persistent_chat_graph(self, conversation_id: str, user_info: Dict[str, Any]):
        """G.Navi AgentRAG LangGraph 빌드"""
        print(f"🔧 G.Navi AgentRAG LangGraph 빌드 시작: {conversation_id}")
        
        # 세션 정보 저장
        self.session_store[conversation_id] = {
            "user_info": user_info,
            "created_at": datetime.now(),
            "conversation_id": conversation_id
        }
        print(f"📝 세션 정보 저장 완료: {user_info.get('name', 'Unknown')} (대화방: {conversation_id})")
        
        # StateGraph 생성
        workflow = StateGraph(ChatState)
        
        # G.Navi 6단계 노드들 추가 (다이어그램 생성 포함)
        workflow.add_node("message_check", self.message_check_node.create_node())
        workflow.add_node("manage_session_history", self.chat_history_node.retrieve_chat_history_node)  # 이름 변경
        workflow.add_node("analyze_intent", self.intent_analysis_node.analyze_intent_node)
        workflow.add_node("retrieve_additional_data", self.data_retrieval_node.retrieve_additional_data_node)
        workflow.add_node("format_response", self.response_formatting_node.format_response_node)
        workflow.add_node("generate_diagram", self.diagram_generation_node.generate_diagram_node)
        workflow.add_node("generate_report", self.report_generation_node.generate_report_node)
        workflow.add_node("wait_state", self.wait_node.create_node())
        
        # 시작점
        workflow.set_entry_point("message_check")
        
        # 조건부 분기
        workflow.add_conditional_edges(
            "message_check",
            self._should_process_message,
            {
                "process": "manage_session_history",  # 노드명 변경
                "wait": END  # 검증 실패 시 바로 종료
            }
        )
        
        # G.Navi 6단계 워크플로우 (다이어그램 생성 포함)
        workflow.add_edge("manage_session_history", "analyze_intent")  # 노드명 변경
        workflow.add_edge("analyze_intent", "retrieve_additional_data")
        workflow.add_edge("retrieve_additional_data", "format_response")
        workflow.add_edge("format_response", "generate_diagram")
        workflow.add_edge("generate_diagram", "generate_report")
        
        # 처리 완료 후 종료
        workflow.add_edge("generate_report", END)
        workflow.add_edge("wait_state", END)
        
        # 컴파일
        compiled_graph = workflow.compile(
            checkpointer=self.memory_saver
        )
        
        print(f"✅ G.Navi AgentRAG LangGraph 컴파일 완료 (6단계): {conversation_id}")
        return compiled_graph