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
    current_session_messages: List[Dict[str, str]]  # MemorySaver가 관리하는 현재 세션 대화 내역 (role, content, timestamp)
    
    # === G.Navi 4단계 처리 결과 ===
    previous_conversations_found: List[Any]         # 1단계: 검색으로 찾은 이전 대화들
    intent_analysis: Dict[str, Any]                 # 2단계: 의도 분석 결과
    career_cases: List[Any]                         # 3단계: 커리어 사례 검색
    external_trends: List[Dict[str, str]]           # 3단계: 트렌드 정보 검색
    education_courses: Dict[str, Any]               # 3단계: 교육과정 추천 결과 (새로 추가)
    final_response: Dict[str, Any]                  # 4단계: 최종 응답
    
    # === 메타데이터 및 로깅 ===
    processing_log: List[str]                       # 처리 로그 추적
    error_messages: List[str]                       # 오류 메시지 수집
    total_processing_time: float                    # 총 처리 시간