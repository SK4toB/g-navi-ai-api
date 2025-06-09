# app/models/message.py

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class MessageSend(BaseModel):
    """메시지 전송 요청"""
    # user_id: str = Field(..., description="사용자 ID")
    # message: str = Field(..., description="사용자 메시지", min_length=1)
    member_id: str = Field(..., alias="memberId", description="회원 ID")
    conversation_id: str = Field(..., alias="conversationId", description="대화방 ID")
    message_text: str = Field(..., alias="messageText", description="사용자 메시지", min_length=1)

class MessageResponse(BaseModel):
    """메시지 응답"""
    conversation_id: str = Field(..., alias="conversationId", description="채팅방 ID")
    member_id: str = Field(..., alias="memberId", description="사용자 ID")
    message_text: str = Field(..., alias="messageText", description="사용자 메시지")
    bot_message: str = Field(..., alias="botMessage", description="AI 응답")
    timestamp: datetime = Field(..., description="응답 시간")
    processing_time_ms: Optional[int] = Field(None, description="처리 시간(밀리초)")

class SessionStatus(BaseModel):
    """세션 상태 응답"""
    conversation_id: str = Field(..., alias="conversationId", description="채팅방 ID")
    status: str = Field(..., description="세션 상태 (active/inactive)")
    thread_id: Optional[str] = Field(None, description="LangGraph 스레드 ID")

class SessionCloseResponse(BaseModel):
    """세션 종료 응답"""
    message: str = Field(..., description="종료 메시지")
    conversation_id: str = Field(..., alias="conversationId", description="채팅방 ID")
    closed_at: datetime = Field(..., description="종료 시간")

class SessionDebugInfo(BaseModel):
    """세션 디버그 정보 (개발용)"""
    conversation_id: str = Field(...,  alias="conversationId", description="채팅방 ID")
    status: Optional[str] = Field(None, description="세션 상태")
    thread_id: Optional[str] = Field(None, description="스레드 ID")
    graph_compiled: Optional[bool] = Field(None, description="그래프 컴파일 상태")
    config: Optional[dict] = Field(None, description="그래프 설정")
    total_active_sessions: Optional[int] = Field(None, description="전체 활성 세션 수")
    error: Optional[str] = Field(None, description="에러 메시지")