# app/graphs/state.py
"""
* @className : ChatState
* @description : G.Navi AgentRAG 시스템의 상태 정의 모듈
*                7단계 워크플로우에서 사용되는 모든 상태 정보를 정의합니다.
*                TypedDict를 상속하여 타입 안전성을 보장하고,
*                total=False로 선택적 필드를 허용합니다.
*
*                 주요 상태 그룹:
*                - 입력 데이터 (필수): 사용자 질문, 프로필, 세션 ID
*                - 대화 내역 관리: MemorySaver가 관리하는 세션 메시지
*                - G.Navi 7단계 처리 결과: 각 단계별 처리 결과
*                - 메타데이터 및 로깅: 처리 로그 및 오류 추적
*
"""

from typing import TypedDict, List, Dict, Any, Optional

class ChatState(TypedDict, total=False):  # total=False로 선택적 필드 허용
    """
    * @className : ChatState
    * @description : G.Navi AgentRAG의 상태 관리 클래스
    *                7단계 워크플로우에서 사용되는 모든 데이터를 관리합니다.
    *                각 단계별 처리 결과와 메타데이터를 포함합니다.
    *
    """
    
    # === 입력 데이터 (필수) ===
    user_question: str                   # 사용자 질문
    user_data: Dict[str, Any]           # 사용자 프로필 데이터
    session_id: str                     # 세션 식별자
    
    # === 대화 내역 관리 (MemorySaver가 관리) ===
    current_session_messages: List[Dict[str, str]]  # 현재 세션의 모든 대화 내역 (이전 메시지 + 현재 세션, role, content, timestamp)
    
    # === G.Navi 7단계 처리 결과 ===
    # 0단계: 메시지 검증 (workflow_status로 처리)
    workflow_status: str                            # 워크플로우 상태 (normal, validation_failed)
    # 1단계: 대화 내역 관리 (current_session_messages)
    intent_analysis: Dict[str, Any]                 # 2단계: 의도 분석 결과
    career_cases: List[Any]                         # 3단계: 커리어 사례 검색
    education_courses: Dict[str, Any]               # 3단계: 교육과정 추천 결과
    news_data: List[Dict[str, Any]]                 # 3단계: 뉴스 데이터 검색 결과
    formatted_response: Dict[str, Any]              # 4단계: 포맷된 응답
    mermaid_diagram: str                            # 5단계: 생성된 Mermaid 다이어그램 코드
    diagram_generated: bool                         # 5단계: 다이어그램 생성 성공 여부
    final_response: Dict[str, Any]                  # 6단계: 최종 응답 (다이어그램 통합)
    
    # === 메타데이터 및 로깅 ===
    processing_log: List[str]                       # 처리 로그 추적
    error_messages: List[str]                       # 오류 메시지 수집
    total_processing_time: float                    # 총 처리 시간
    
    # === 커리어 상담 전용 상태 ===
    conversation_flow: str                          # 대화 플로우 타입 (general, career_consultation)
    consultation_stage: str                         # 상담 진행 단계 (positioning, path_selection, deepening, planning, learning, summary)
    career_paths_suggested: List[Dict[str, Any]]    # 제시된 커리어 경로들
    selected_career_path: Dict[str, Any]            # 사용자가 선택한 커리어 경로
    awaiting_user_input: bool                       # 사용자 입력 대기 상태
    next_expected_input: str                        # 다음에 기대되는 입력 유형
    consultation_context: Dict[str, Any]            # 상담 컨텍스트 (목표, 이유 등)
    
    # === 사용자 정보 수집 관련 ===
    missing_info_fields: List[str]                  # 부족한 정보 필드들 (experience, skills, domain)
    collected_user_info: Dict[str, Any]             # 사용자로부터 수집한 추가 정보
    info_collection_stage: str                      # 정보 수집 단계 (experience, skills, domain, complete)
    
    # === 커리어 데이터 관련 ===
    retrieved_career_data: List[Dict[str, Any]]     # career_positioning에서 검색된 사내 구성원 데이터 (15명까지)
    path_selection_info: Dict[str, Any]             # path_selection 단계에서 수집된 정보
    path_deepening_info: Dict[str, Any]             # path_deepening 단계에서 수집된 액션 플랜 정보
    learning_roadmap_info: Dict[str, Any]           # learning_roadmap 단계에서 수집된 학습 로드맵 정보
    
    # === 상태 추적용 디버깅 필드 ===
    state_trace: List[str]                          # state 전달 추적용
    career_positioning_timestamp: float             # career_positioning 완료 시간