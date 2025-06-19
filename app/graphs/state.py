# app/graphs/state.py

from typing import TypedDict, Optional, List, Dict, Any

class ChatState(TypedDict):
    """LangGraph 상태 정의"""
    
    # 입력
    message_text: str
    member_id: str
    conversation_id: str
    user_info: Optional[Dict[str, Any]]
    
    # 노드별 처리 결과
    chat_history_results: Optional[List[Any]]                 # 1단계: 대화이력 검색 결과
    intent_analysis: Optional[Dict[str, Any]]                 # 2단계: 의도 분석 결과
    career_cases: Optional[List[Any]]                         # 3단계: 커리어 사례 검색
    external_trends: Optional[List[Dict[str, str]]]           # 3단계: 트렌드 정보 검색
    education_courses: Dict[str, Any]                         # 교육과정 추천 결과
    final_response: Optional[Dict[str, Any]]                  # 4단계: 최종 응답
    
    # 최종 출력
    bot_message: Optional[str]