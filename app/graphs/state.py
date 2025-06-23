# app/graphs/state.py
# G.Navi AgentRAG 시스템의 상태 정의

from typing import TypedDict, List, Dict, Any, Optional

class ChatState(TypedDict, total=False):  # total=False로 선택적 필드 허용
    """G.Navi AgentRAG의 상태 관리"""
    
    # === 입력 데이터 (필수) ===
    user_question: str                   # 사용자 질문
    user_data: Dict[str, Any]           # 사용자 프로필 데이터
    session_id: str                     # 세션 식별자
    
    # === 대화 내역 관리 (MemorySaver가 관리) ===
    current_session_messages: List[Dict[str, str]]  # 현재 세션의 모든 대화 내역 (이전 메시지 + 현재 세션, role, content, timestamp)
    
    # === G.Navi 6단계 처리 결과 ===
    intent_analysis: Dict[str, Any]                 # 2단계: 의도 분석 결과
    career_cases: List[Any]                         # 3단계: 커리어 사례 검색
    education_courses: Dict[str, Any]               # 3단계: 교육과정 추천 결과
    formatted_response: Dict[str, Any]              # 4단계: 포맷된 응답
    mermaid_diagram: str                            # 5단계: 생성된 Mermaid 다이어그램 코드
    diagram_generated: bool                         # 5단계: 다이어그램 생성 성공 여부
    final_response: Dict[str, Any]                  # 6단계: 최종 응답 (다이어그램 통합)
    
    # === 메타데이터 및 로깅 ===
    processing_log: List[str]                       # 처리 로그 추적
    error_messages: List[str]                       # 오류 메시지 수집
    total_processing_time: float                    # 총 처리 시간