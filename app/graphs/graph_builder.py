# app/graphs/graph_builder.py
"""
* @className : ChatGraphBuilder
* @description : G.Navi AgentRAG 시스템의 LangGraph 빌더 모듈
*                범용 대화와 커리어 상담을 지원하는 이중 플로우 시스템입니다.
*                
*                 범용 대화 플로우 (7단계):
*                0. 메시지 검증 (message_check)
*                1. 세션 대화내역 관리 (manage_session_history) 
*                2. 의도 분석 (analyze_intent)
*                     # 엣지 설정 (각 노드 간의 연결 관계)
        workflow.add_edge("message_check", "manage_session_history")
        
        # 세션 관리 후 상담 진행 여부에 따른 분기
        workflow.add_conditional_edges(
            "manage_session_history",
            self._check_if_career_consultation_in_progress,
            {
                "analyze_intent": "analyze_intent",  # 새로운 대화 시작 - 의도 분석 필요
                "career_consultation_direct": "collect_user_info"  # 상담 진행 중 - 의도 분석 건너뛰고 바로 상담 단계로
            }
        )
        
        # 의도 분석 후 대화 유형에 따른 분기
        workflow.add_conditional_edges(
            "analyze_intent",
            self._determine_conversation_flow,
            {
                "general_flow": "retrieve_additional_data",  # 범용 대화 플로우
                "career_consultation": "collect_user_info"    # 커리어 상담 플로우 (정보 수집부터)
            }
        ) (retrieve_additional_data)
*                4. 적응적 응답 포맷팅 (format_response)
*                5. 다이어그램 생성 (generate_diagram)
*                6. 관리자용 보고서 생성 (generate_report)
*
*                 커리어 상담 플로우 (대화형 6단계):
*                0-2. 공통: 메시지 검증 → 세션 관리 → 의도 분석
*                3. 커리어 포지셔닝 분석 (career_positioning)
*                4. 경로 선택 및 심화 논의 (path_selection/deepening)
*                5. 실행 전략 및 학습 로드맵 (action_planning/learning)
*                6. 동기부여 및 요약 (consultation_summary)
*
*                 주요 기능:
*                - 의도 분석 기반 플로우 자동 분기
*                - 상태 기반 워크플로우 관리 (StateGraph)
*                - MemorySaver를 통한 대화 연속성 보장
*                - 세션별 사용자 정보 및 메타데이터 관리
*                - 대화형 상담을 위한 순환 구조 지원
*
"""

import logging
from datetime import datetime
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing import Dict, Any

from app.config.settings import settings
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

# 커리어 상담 전용 노드들 import
from app.graphs.nodes.career_consultation.career_positioning import CareerPositioningNode
from app.graphs.nodes.career_consultation.path_selection import PathSelectionNode
from app.graphs.nodes.career_consultation.path_deepening import PathDeepeningNode
from app.graphs.nodes.career_consultation.learning_roadmap import LearningRoadmapNode
from app.graphs.nodes.career_consultation.consultation_summary import ConsultationSummaryNode
from app.graphs.nodes.career_consultation.user_info_collection import UserInfoCollectionNode


class ChatGraphBuilder:
    """
    * @className : ChatGraphBuilder
    * @description : G.Navi AgentRAG 시스템의 LangGraph 빌더 클래스
    *                7단계 워크플로우를 구성하고 실행하는 핵심 클래스입니다:
    *                메시지 검증 → 히스토리 관리 → 의도 분석 → 데이터 검색 → 
    *                응답 포맷팅 → 다이어그램 생성 → 보고서 생성
    * 
    *                 주요 역할:
    *                - LangGraph 워크플로우 구성 및 컴파일
    *                - 세션별 사용자 정보 관리
    *                - MemorySaver를 통한 대화 상태 지속성 보장
    *                - 각 노드 간의 데이터 흐름 조율
    """
    
    def __init__(self):
        """
        ChatGraphBuilder 생성자 - 초기화 작업을 수행한다.
        """
        print("ChatGraphBuilder 초기화 (G.Navi AgentRAG)")  # 초기화 시작 메시지 출력
        self.logger = logging.getLogger(__name__)  # 로그 객체 생성
        self.memory_saver = MemorySaver()  # 대화 상태 저장을 위한 메모리 세이버 생성
        
        # 세션별 정보 저장소 추가
        self.session_store = {}  # conversation_id -> {"user_info": ..., "metadata": ...} 형태로 세션 정보 저장
        
        # G.Navi 에이전트들 초기화
        self.career_retriever_agent = Retriever()  # 커리어 검색 에이전트 생성
        self.intent_analysis_agent = Analyzer()  # 의도 분석 에이전트 생성
        self.response_formatting_agent = Formatter()  # 응답 포맷팅 에이전트 생성
        
        # 새로 분리된 node 클래스들 초기화
        self.message_check_node = MessageCheckNode()  # 메시지 검증 노드 생성
        self.chat_history_node = ChatHistoryNode(self)  # 채팅 히스토리 노드 생성
        self.intent_analysis_node = IntentAnalysisNode(self)  # 의도 분석 노드 생성
        self.data_retrieval_node = DataRetrievalNode()  # 데이터 검색 노드 생성
        self.response_formatting_node = ResponseFormattingNode(self)  # 응답 포맷팅 노드 생성
        self.diagram_generation_node = DiagramGenerationNode()  # 다이어그램 생성 노드 생성
        self.report_generation_node = ReportGenerationNode()  # 보고서 생성 노드 생성
        
        # 커리어 상담 전용 노드들 초기화
        self.career_positioning_node = CareerPositioningNode(self)  # 커리어 포지셔닝 노드
        self.path_selection_node = PathSelectionNode(self)  # 경로 선택 노드
        self.path_deepening_node = PathDeepeningNode(self)  # 경로 심화 노드
        self.learning_roadmap_node = LearningRoadmapNode(self)  # 학습 로드맵 노드
        self.consultation_summary_node = ConsultationSummaryNode(self)  # 상담 요약 노드
        self.user_info_collection_node = UserInfoCollectionNode(self)  # 사용자 정보 수집 노드
    
    def _check_if_career_consultation_in_progress(self, state: ChatState) -> str:
        """
        커리어 상담이 진행 중인지 확인한다.
        상담 진행 중이면 의도 분석을 건너뛰고 바로 상담 단계로 이동합니다.
        
        @param state: ChatState - 현재 워크플로우 상태
        @return str - "analyze_intent" 또는 "career_consultation_direct"
        """
        consultation_stage = state.get("consultation_stage", "")
        
        # 상담 완료 상태 확인
        if consultation_stage == "completed":
            print("커리어 상담 완료 - 새로운 대화로 진행")
            return "analyze_intent"
        
        # 상담이 진행 중인 단계들
        active_consultation_stages = [
            "collecting_info", "positioning_ready", "path_selection", 
            "deepening", "learning_decision", "summary_request"
        ]
        
        if consultation_stage in active_consultation_stages:
            print(f"커리어 상담 진행 중 (단계: {consultation_stage}) - 의도 분석 건너뛰기")
            return "career_consultation_direct"
        else:
            print("새로운 대화 시작 - 의도 분석 수행")
            return "analyze_intent"
    
    def _determine_conversation_flow(self, state: ChatState) -> str:
        """
        대화 유형에 따른 플로우를 결정한다.
        의도 분석 결과를 바탕으로 범용 대화 또는 커리어 상담 플로우로 분기합니다.
        
        @param state: ChatState - 현재 워크플로우 상태
        @return str - "general_flow" 또는 "career_consultation"
        """
        # 🚨 중요: 이미 커리어 상담이 진행 중인 경우 상담 플로우 유지
        consultation_stage = state.get("consultation_stage", "")
        # 상담 완료 상태는 제외하고, 진행 중인 단계만 상담 플로우 유지
        if consultation_stage and consultation_stage not in ["initial", "", "completed"]:
            print(f"커리어 상담 진행 중 - 현재 단계: {consultation_stage}")
            return "career_consultation"
        
        # 의도 분석 결과 확인
        intent_analysis = state.get("intent_analysis", {})
        intent_type = intent_analysis.get("intent_type", "general")
        user_question = state.get("user_question", "").lower()
        
        # 커리어 상담 키워드 확인 (더 구체적으로 조정)
        career_consultation_phrases = [
            # 직접적인 상담 요청
            "커리어", "career", "커리어 상담", "진로 상담", "경력 상담", "career 상담",
            "커리어 고민", "진로 고민", "경력 고민", "career 고민",
            "커리어 조언", "진로 조언", "경력 조언", "career 조언",
            
            # 구체적인 커리어 관련 질문
            "커리어 방향", "진로 방향", "경력 방향", "career path",
            "커리어 개발", "진로 개발", "경력 개발", "career development",
            "커리어 계획", "진로 계획", "경력 계획", "career planning",
            
            # 승진/이직 관련
            "승진 방법", "승진 전략", "승진하려면", "promotion",
            "이직 준비", "이직 고민", "이직하려면", "job change",
            "전직 준비", "전직 고민", "career transition",
            
            # 성장 관련 (구체화)
            "경력 성장", "커리어 성장", "진로 성장", "career growth",
            "성장 경로", "성장 방향", "성장 계획", "growth path",
            
            # 역량/스킬 관련
            "역량 개발", "스킬 개발", "능력 개발", "skill development",
            "커리어 스킬", "직무 역량", "professional skills"
        ]
        
        # 더 정확한 매칭을 위해 구문 단위로 확인
        is_career_consultation = any(phrase in user_question for phrase in career_consultation_phrases)  # 커리어 상담 키워드 포함 여부 확인
        
        # 커리어 상담이 아닌 경우를 명확히 구분 (제외 키워드)
        non_career_phrases = [
            # 기술/도구 관련
            "코딩", "프로그래밍", "개발 도구", "기술 스택", "coding", "programming",
            "버그", "에러", "오류", "디버깅", "bug", "error", "debug",
            
            # 업무 프로세스
            "프로젝트 관리", "일정 관리", "업무 프로세스", "project management",
            "회의", "미팅", "meeting", "회의실", "예약",
            
            # 회사 정보/복리후생
            "복리후생", "급여", "연봉", "휴가", "benefit", "salary",
            "회사 정보", "조직도", "company info",
            
            # 일반 업무 질문
            "사용법", "방법", "how to", "tutorial", "가이드", "guide",
            "추천", "recommend", "리스트", "list"
        ]
        
        # 제외 키워드가 있으면 일반 대화로 분류
        has_non_career_phrases = any(phrase in user_question for phrase in non_career_phrases)  # 제외 키워드 포함 여부 확인
        
        # 최종 판단: 커리어 키워드가 있고 + 제외 키워드가 없어야 커리어 상담
        is_career_consultation = is_career_consultation and not has_non_career_phrases  # 커리어 상담 최종 판단
        
        if is_career_consultation or intent_type == "career_consultation":  # 커리어 상담 조건 확인
            print("커리어 상담 플로우로 진행")  # 커리어 상담 플로우 선택 로그
            return "career_consultation"
        else:  # 일반 대화인 경우
            print("범용 대화 플로우로 진행")  # 일반 대화 플로우 선택 로그
            return "general_flow"
    
    def _should_continue_or_wait(self, state: ChatState) -> str:
        """
        사용자 입력을 기다려야 하는지 다음 단계로 진행해야 하는지 결정한다.
        
        @param state: ChatState - 현재 워크플로우 상태
        @return str - "continue" (다음 단계로) 또는 "wait" (사용자 입력 대기)
        """
        awaiting_input = state.get("awaiting_user_input", False)  # 사용자 입력 대기 상태 확인
        consultation_stage = state.get("consultation_stage", "")  # 현재 상담 단계 확인
        
        # State 전달 디버깅
        print(f" DEBUG - _should_continue_or_wait에서 state 확인:")
        print(f" DEBUG - consultation_stage: {consultation_stage}")
        print(f" DEBUG - awaiting_user_input: {awaiting_input}")
        print(f" DEBUG - state_trace: {state.get('state_trace', 'None')}")
        print(f" DEBUG - retrieved_career_data: {len(state.get('retrieved_career_data', []))}개")
        
        if awaiting_input:  # 사용자 입력 대기 중인 경우
            print(f"사용자 입력 대기 중: {consultation_stage}")  # 대기 상태 로그
            return "wait"
        else:  # 다음 단계로 진행할 경우
            print(f"다음 단계로 진행: {consultation_stage}")  # 진행 상태 로그
            return "continue"

    def _determine_career_consultation_stage(self, state: ChatState) -> str:
        """
        커리어 상담 진행 단계를 결정한다.
        현재 상담 단계와 사용자 입력을 분석하여 다음 단계를 결정합니다.
        
        @param state: ChatState - 현재 워크플로우 상태
        @return str - 다음 상담 단계
        """
        consultation_stage = state.get("consultation_stage", "initial")  # 현재 상담 단계 확인
        awaiting_input = state.get("awaiting_user_input", False)  # 사용자 입력 대기 상태 확인
        
        print(f" 상담 단계 결정: stage={consultation_stage}, awaiting_input={awaiting_input}")
        
        # 사용자 입력을 기다리는 중이라면, 해당 단계를 그대로 진행
        # (사용자가 응답했으므로 다음 단계로 진행)
        if awaiting_input:
            print(f"사용자 응답 처리: {consultation_stage} 단계에서 사용자 입력 받음")
        
        # 각 단계별 처리
        if consultation_stage == "collecting_info":
            return "process_user_info"  # 사용자 정보 처리
        elif consultation_stage == "positioning_ready":
            return "career_positioning"  # 정보 수집 완료 후 포지셔닝
        elif consultation_stage == "path_selection":
            return "process_path_selection"
        elif consultation_stage == "deepening":
            return "process_deepening"
        elif consultation_stage == "learning_decision":
            return "create_learning_roadmap"
        elif consultation_stage == "summary_request":
            return "create_consultation_summary"
        elif consultation_stage == "initial" or not consultation_stage:
            # 초기 상담 시작 시 - 사용자 정보 충분성 먼저 체크
            user_data = self.get_user_info_from_session(state)
            collected_info = state.get("collected_user_info", {})
            merged_user_data = {**user_data, **collected_info}
            
            # 필수 정보 체크 (연차, 기술스택, 도메인)
            missing_fields = []
            if not merged_user_data.get('experience'):
                missing_fields.append('experience')
            if not merged_user_data.get('skills') or len(merged_user_data.get('skills', [])) == 0:
                missing_fields.append('skills')
            if not merged_user_data.get('domain'):
                missing_fields.append('domain')
            
            if missing_fields:
                print(f"부족한 정보 감지: {missing_fields}")
                return "collect_user_info"  # 정보 수집 필요
            else:
                print("사용자 정보 충분 - 바로 포지셔닝 분석")
                return "career_positioning"  # 바로 포지셔닝 분석
        else:
            return "collect_user_info"  # 기본값
    
    def _career_consultation_router_node(self, state: ChatState) -> Dict[str, Any]:
        """
        커리어 상담 라우터 노드 - 현재 상담 단계를 확인만 하고 상태를 그대로 반환
        """
        consultation_stage = state.get("consultation_stage", "")
        print(f"커리어 상담 라우터: 현재 단계 = {consultation_stage}")
        return state
    
    def get_session_info(self, conversation_id: str) -> Dict[str, Any]:
        """
        세션 정보를 조회한다.
        
        @param conversation_id: str - 대화 세션 고유 ID
        @return Dict[str, Any] - 세션 정보 딕셔너리
        """
        return self.session_store.get(conversation_id, {})  # 세션 정보 반환, 없으면 빈 딕셔너리 반환
    
    def get_user_info_from_session(self, state: ChatState) -> Dict[str, Any]:
        """
        사용자 정보를 추출한다 (우선순위 기반).
        다음 우선순위로 사용자 정보를 추출합니다:
        1. state의 user_data (실시간 정보)
        2. session_store의 user_info (세션 저장 정보)
        3. 기본값 빈 딕셔너리
        
        @param state: ChatState - 현재 워크플로우 상태  
        @return Dict[str, Any] - 사용자 프로필 정보
        """
        # 1. state에서 user_data 확인
        user_data = state.get("user_data", {})  # 상태에서 사용자 데이터 조회
        if user_data:  # 사용자 데이터가 존재하면
            return user_data  # 사용자 데이터 반환
        
        # 2. session_id로 session_store에서 조회
        session_id = state.get("session_id", "")  # 세션 ID 조회
        if session_id:  # 세션 ID가 존재하면
            session_info = self.get_session_info(session_id)  # 세션 정보 조회
            return session_info.get("user_info", {})  # 사용자 정보 반환
        
        # 3. 기본값 반환
        return {}  # 빈 딕셔너리 반환
    
    def get_previous_messages_from_session(self, state: ChatState) -> list:
        """
        세션에서 이전 메시지를 추출한다.
        
        @param state: ChatState - 현재 워크플로우 상태
        @return list - 이전 메시지 리스트
        """
        # session_id로 session_store에서 조회
        session_id = state.get("session_id", "")  # 세션 ID 조회
        if session_id:  # 세션 ID가 존재하면
            session_info = self.get_session_info(session_id)  # 세션 정보 조회
            return session_info.get("previous_messages", [])  # 이전 메시지 반환
        
        # 기본값 반환
        return []  # 빈 리스트 반환
    
    def close_session(self, conversation_id: str):
        """
        세션 정보를 정리한다.
        
        @param conversation_id: str - 대화 세션 고유 ID
        """
        if conversation_id in self.session_store:  # 세션이 존재하면
            del self.session_store[conversation_id]  # 세션 정보 삭제
            print(f"GraphBuilder 세션 정보 삭제: {conversation_id}")  # 삭제 완료 로그 출력
    
    def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """
        모든 세션 정보를 조회한다 (디버깅용).
        
        @return Dict[str, Dict[str, Any]] - 모든 세션 정보 복사본
        """
        return self.session_store.copy()  # 세션 저장소 복사본 반환
    
    async def build_persistent_chat_graph(self, conversation_id: str, user_info: Dict[str, Any], previous_messages: list = None):
        """
        G.Navi AgentRAG LangGraph를 빌드하고 컴파일한다.
        7단계 워크플로우로 구성된 LangGraph를 생성하고 컴파일합니다.
        세션 정보를 저장하고 MemorySaver를 통한 상태 지속성을 보장합니다.
        
        @param conversation_id: str - 대화 세션 고유 ID
        @param user_info: Dict[str, Any] - 사용자 프로필 정보
        @param previous_messages: list - SpringBoot에서 전달받은 이전 메시지들
        @return CompiledGraph - 컴파일된 LangGraph 워크플로우
        """
        print(f" G.Navi AgentRAG LangGraph 빌드 시작: {conversation_id}")  # 빌드 시작 로그 출력
        
        # 세션 정보 저장 (previous_messages도 포함)
        self.session_store[conversation_id] = {  # 세션 저장소에 정보 저장
            "user_info": user_info,  # 사용자 정보 저장
            "previous_messages": previous_messages or [],  # 이전 메시지 저장 (없으면 빈 리스트)
            "created_at": datetime.now(),  # 생성 시간 저장
            "conversation_id": conversation_id  # 대화 ID 저장
        }
        
        message_count = len(previous_messages) if previous_messages else 0  # 이전 메시지 개수 계산
        print(f"세션 정보 저장 완료: {user_info.get('name', 'Unknown')} (대화방: {conversation_id}, 이전 메시지: {message_count}개)")  # 세션 저장 완료 로그
        
        # StateGraph 생성
        workflow = StateGraph(ChatState)  # 상태 그래프 생성
        
        # G.Navi 7단계 노드들 추가 (메시지 검증부터 보고서 생성까지)
        # 메시지 검증 노드는 설정에 따라 조건부로 추가
        if settings.message_check_enabled:
            workflow.add_node("message_check", self.message_check_node.create_node())  # 메시지 검증 노드 추가
        
        workflow.add_node("manage_session_history", self.chat_history_node.retrieve_chat_history_node)  # 세션 히스토리 관리 노드 추가
        workflow.add_node("analyze_intent", self.intent_analysis_node.analyze_intent_node)  # 의도 분석 노드 추가
        
        # 범용 대화 노드들
        workflow.add_node("retrieve_additional_data", self.data_retrieval_node.retrieve_additional_data_node)  # 추가 데이터 검색 노드 추가
        workflow.add_node("format_response", self.response_formatting_node.format_response_node)  # 응답 포맷팅 노드 추가
        workflow.add_node("generate_diagram", self.diagram_generation_node.generate_diagram_node)  # 다이어그램 생성 노드 추가
        workflow.add_node("generate_report", self.report_generation_node.generate_report_node)  # 보고서 생성 노드 추가
        
        # 커리어 상담 전용 노드들 추가
        workflow.add_node("collect_user_info", self.user_info_collection_node.collect_user_info_node)  # 사용자 정보 수집
        workflow.add_node("process_user_info", self.user_info_collection_node.process_user_info_node)  # 사용자 정보 처리
        workflow.add_node("career_positioning", self.career_positioning_node.analyze_career_positioning)  # 커리어 포지셔닝
        workflow.add_node("process_path_selection", self.path_selection_node.process_path_selection_node)  # 경로 선택 처리
        workflow.add_node("process_deepening", self.path_deepening_node.process_deepening_node)  # 경로 심화 노드
        workflow.add_node("create_learning_roadmap", self.learning_roadmap_node.create_learning_roadmap_node)  # 학습 로드맵
        workflow.add_node("create_consultation_summary", self.consultation_summary_node.create_consultation_summary_node)  # 상담 요약
        
        # 시작점 설정 (메시지 검증 활성화 여부에 따라)
        if settings.message_check_enabled:
            workflow.set_entry_point("message_check")  # 메시지 검증을 시작점으로 설정
            workflow.add_edge("message_check", "manage_session_history")  # 메시지 검증 후 세션 관리로 진행
        else:
            workflow.set_entry_point("manage_session_history")  # 메시지 검증 비활성화 시 세션 관리를 시작점으로 설정
        
        # 세션 관리 후 커리어 상담 진행 상태 확인
        workflow.add_conditional_edges(
            "manage_session_history",
            self._check_if_career_consultation_in_progress,
            {
                "analyze_intent": "analyze_intent",  # 새로운 대화인 경우 의도 분석
                "career_consultation_direct": "career_consultation_router"  # 상담 진행 중인 경우 상담 라우터로
            }
        )
        
        # 커리어 상담 라우터 노드 (상담 단계에 따라 적절한 노드로 라우팅)
        workflow.add_node("career_consultation_router", self._career_consultation_router_node)
        workflow.add_conditional_edges(
            "career_consultation_router",
            self._determine_career_consultation_stage,
            {
                "collect_user_info": "collect_user_info",
                "process_user_info": "process_user_info", 
                "career_positioning": "career_positioning",
                "process_path_selection": "process_path_selection",
                "process_deepening": "process_deepening",
                "create_learning_roadmap": "create_learning_roadmap",
                "create_consultation_summary": "create_consultation_summary"
            }
        )
        
        # 의도 분석 후 대화 유형에 따른 분기
        workflow.add_conditional_edges(
            "analyze_intent",
            self._determine_conversation_flow,
            {
                "general_flow": "retrieve_additional_data",  # 범용 대화 플로우
                "career_consultation": "collect_user_info"    # 커리어 상담 플로우 (정보 수집부터)
            }
        )
        
        # === 범용 대화 플로우 (기존과 동일) ===
        workflow.add_edge("retrieve_additional_data", "format_response")
        workflow.add_edge("format_response", "generate_diagram")
        workflow.add_edge("generate_diagram", "generate_report")
        workflow.add_edge("generate_report", END)
        
        # === 커리어 상담 플로우 (정보 수집 포함) ===
        # 정보 수집 단계 - 사용자 정보 충분성에 따른 분기
        workflow.add_conditional_edges(
            "collect_user_info",
            self._determine_career_consultation_stage,
            {
                "process_user_info": "process_user_info",
                "career_positioning": "career_positioning",  # 정보 충분시 바로 포지셔닝
                "collect_user_info": END  # 정보 요청 후 사용자 입력 대기
            }
        )
        
        workflow.add_conditional_edges(
            "process_user_info",
            self._determine_career_consultation_stage,
            {
                "collect_user_info": "collect_user_info",  # 추가 정보 수집 필요시
                "career_positioning": "career_positioning",  # 정보 수집 완료시
                "process_user_info": END  # 정보 처리 중 사용자 입력 대기
            }
        )
        
        # 커리어 상담 단계별 조건부 분기
        workflow.add_conditional_edges(
            "career_positioning",
            self._should_continue_or_wait,
            {
                "continue": "process_path_selection",
                "wait": END  # 첫 응답 후 사용자 입력 대기
            }
        )
        
        workflow.add_conditional_edges(
            "process_path_selection", 
            self._should_continue_or_wait,
            {
                "continue": "process_deepening",
                "wait": END  # 경로 선택 후 사용자 입력 대기
            }
        )
        
        workflow.add_conditional_edges(
            "process_deepening",
            self._should_continue_or_wait,
            {
                "continue": "create_learning_roadmap",
                "wait": END  # 심화 논의 후 사용자 입력 대기
            }
        )
        
        workflow.add_conditional_edges(
            "create_learning_roadmap",
            self._should_continue_or_wait,
            {
                "continue": "create_consultation_summary",
                "wait": END  # 로드맵 제시 후 사용자 입력 대기
            }
        )
        
        # 상담 요약 후 종료
        workflow.add_edge("create_consultation_summary", END)
        
        # 컴파일
        compiled_graph = workflow.compile(  # 워크플로우 컴파일
            checkpointer=self.memory_saver  # 메모리 세이버 설정
        )
        
        print(f"G.Navi AgentRAG LangGraph 컴파일 완료 (7단계): {conversation_id}")  # 컴파일 완료 로그 출력
        return compiled_graph  # 컴파일된 그래프 반환