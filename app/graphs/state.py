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
    intent: Optional[str]
    embedding_vector: Optional[List[float]]
    memory_results: Optional[List[Dict[str, Any]]]
    similarity_score: Optional[float]
    profiling_data: Optional[Dict[str, Any]]
    connection_suggestions: Optional[List[str]]
    
    # 최종 출력
    bot_message: Optional[str]