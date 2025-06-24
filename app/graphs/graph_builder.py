# app/graphs/graph_builder.py
"""
🔧 G.Navi AgentRAG 시스템의 LangGraph 빌더

이 모듈은 AgentRAG 워크플로우의 핵심인 LangGraph를 구성하고 관리합니다:

📋 7단계 워크플로우:
0. 메시지 검증 (message_check)
1. 세션 대화내역 관리 (manage_session_history) 
2. 의도 분석 (analyze_intent)
3. 추가 데이터 검색 (retrieve_additional_data)
4. 적응적 응답 포맷팅 (format_response)
5. 다이어그램 생성 (generate_diagram)
6. 관리자용 보고서 생성 (generate_report)

🔄 주요 기능:
- 상태 기반 워크플로우 관리 (StateGraph)
- MemorySaver를 통한 대화 연속성 보장
- 세션별 사용자 정보 및 메타데이터 관리
- 조건부 분기를 통한 유연한 처리 흐름
"""

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


class ChatGraphBuilder:
    """
    🔧 G.Navi AgentRAG 시스템의 LangGraph 빌더
    
    7단계 워크플로우를 구성하고 실행하는 핵심 클래스입니다:
    메시지 검증 → 히스토리 관리 → 의도 분석 → 데이터 검색 → 
    응답 포맷팅 → 다이어그램 생성 → 보고서 생성
    
    🔄 주요 역할:
    - LangGraph 워크플로우 구성 및 컴파일
    - 세션별 사용자 정보 관리
    - MemorySaver를 통한 대화 상태 지속성 보장
    - 각 노드 간의 데이터 흐름 조율
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
    
    def _should_process_message(self, state: ChatState) -> str:
        """
        🔍 메시지 처리 여부 결정
        
        메시지 검증 결과를 확인하여 후속 워크플로우 진행 여부를 결정합니다.
        현재는 모든 검증된 메시지를 처리하도록 구성되어 있습니다.
        
        Args:
            state: 현재 워크플로우 상태
            
        Returns:
            str: 항상 "process" (모든 메시지 처리)
        """
        user_question = state.get("user_question", "")
        
        if user_question and user_question.strip():
            print(f"메시지 있음 → 처리 시작: {user_question[:30]}...")
            return "process"
        else:
            print("메시지 없음 → 검증 실패 처리")
            # 빈 메시지는 메시지 검증 단계에서 이미 처리되므로 이 경우는 발생하지 않음
            return "process"
    
    def get_session_info(self, conversation_id: str) -> Dict[str, Any]:
        """세션 정보 조회"""
        return self.session_store.get(conversation_id, {})
    
    def get_user_info_from_session(self, state: ChatState) -> Dict[str, Any]:
        """
        👤 사용자 정보 추출 (우선순위 기반)
        
        다음 우선순위로 사용자 정보를 추출합니다:
        1. state의 user_data (실시간 정보)
        2. session_store의 user_info (세션 저장 정보)
        3. 기본값 빈 딕셔너리
        
        Args:
            state: 현재 워크플로우 상태
            
        Returns:
            Dict: 사용자 프로필 정보
        """
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
    
    def get_previous_messages_from_session(self, state: ChatState) -> list:
        """세션에서 이전 메시지 추출"""
        # session_id로 session_store에서 조회
        session_id = state.get("session_id", "")
        if session_id:
            session_info = self.get_session_info(session_id)
            return session_info.get("previous_messages", [])
        
        # 기본값 반환
        return []
    
    def close_session(self, conversation_id: str):
        """세션 정보 정리"""
        if conversation_id in self.session_store:
            del self.session_store[conversation_id]
            print(f"📝 GraphBuilder 세션 정보 삭제: {conversation_id}")
    
    def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """모든 세션 정보 조회 (디버깅용)"""
        return self.session_store.copy()
    
    async def build_persistent_chat_graph(self, conversation_id: str, user_info: Dict[str, Any], previous_messages: list = None):
        """
        🏗️ G.Navi AgentRAG LangGraph 빌드 및 컴파일
        
        7단계 워크플로우로 구성된 LangGraph를 생성하고 컴파일합니다.
        세션 정보를 저장하고 MemorySaver를 통한 상태 지속성을 보장합니다.
        
        Args:
            conversation_id: 대화 세션 고유 ID
            user_info: 사용자 프로필 정보
            previous_messages: SpringBoot에서 전달받은 이전 메시지들
            
        Returns:
            CompiledGraph: 컴파일된 LangGraph 워크플로우
        """
        print(f"🔧 G.Navi AgentRAG LangGraph 빌드 시작: {conversation_id}")
        
        # 세션 정보 저장 (previous_messages도 포함)
        self.session_store[conversation_id] = {
            "user_info": user_info,
            "previous_messages": previous_messages or [],
            "created_at": datetime.now(),
            "conversation_id": conversation_id
        }
        
        message_count = len(previous_messages) if previous_messages else 0
        print(f"📝 세션 정보 저장 완료: {user_info.get('name', 'Unknown')} (대화방: {conversation_id}, 이전 메시지: {message_count}개)")
        
        # StateGraph 생성
        workflow = StateGraph(ChatState)
        
        # G.Navi 7단계 노드들 추가 (메시지 검증부터 보고서 생성까지)
        workflow.add_node("message_check", self.message_check_node.create_node())
        workflow.add_node("manage_session_history", self.chat_history_node.retrieve_chat_history_node)  # 이름 변경
        workflow.add_node("analyze_intent", self.intent_analysis_node.analyze_intent_node)
        workflow.add_node("retrieve_additional_data", self.data_retrieval_node.retrieve_additional_data_node)
        workflow.add_node("format_response", self.response_formatting_node.format_response_node)
        workflow.add_node("generate_diagram", self.diagram_generation_node.generate_diagram_node)
        workflow.add_node("generate_report", self.report_generation_node.generate_report_node)
        
        # 시작점
        workflow.set_entry_point("message_check")
        
        # 조건부 분기 - 메시지 검증 후 처리 진행
        workflow.add_conditional_edges(
            "message_check",
            self._should_process_message,
            {
                "process": "manage_session_history"  # 항상 세션 관리로 진행
            }
        )
        
        # G.Navi 7단계 워크플로우 연결 (메시지 검증부터 보고서 생성까지)
        workflow.add_edge("manage_session_history", "analyze_intent")  # 1→2단계
        workflow.add_edge("analyze_intent", "retrieve_additional_data")  # 2→3단계
        workflow.add_edge("retrieve_additional_data", "format_response")  # 3→4단계
        workflow.add_edge("format_response", "generate_diagram")  # 4→5단계
        workflow.add_edge("generate_diagram", "generate_report")  # 5→6단계
        
        # 처리 완료 후 종료
        workflow.add_edge("generate_report", END)
        
        # 컴파일
        compiled_graph = workflow.compile(
            checkpointer=self.memory_saver
        )
        
        print(f"✅ G.Navi AgentRAG LangGraph 컴파일 완료 (7단계): {conversation_id}")
        return compiled_graph