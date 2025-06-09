# app/models/chat.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# 요청 모델들
class ChatRoomCreate(BaseModel):
    """SpringBoot에서 전달받는 요청"""
    member_id: str = Field(..., alias="memberId", description="사용자 ID")
    conversation_id: str = Field(..., alias="conversationId", description="SpringBoot에서 전달받은 conversation ID")
    user_info: Dict[str, Any] = Field(..., description="SpringBoot에서 전달받은 사용자 정보")

class ChatRoomResponse(BaseModel):
    """SpringBoot로 반환하는 응답"""
    conversation_id: str = Field(..., alias="conversationId", description="채팅방 ID")
    bot_message: str = Field(..., alias="botMessage", description="AI 초기 인사 메시지")
    timestamp: datetime = Field(..., description="생성 시간")
    # member_id: str = Field(..., description="사용자 ID")
    # is_new_room: bool = Field(..., description="새 방인지 기존 방인지")
