# app/models/chat.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# 요청 모델들
class ChatRoomCreate(BaseModel):
    """SpringBoot에서 전달받는 요청"""
    user_id: str = Field(..., description="사용자 ID")
    user_info: Dict[str, Any] = Field(..., description="SpringBoot에서 전달받은 사용자 정보")
    room_id: str = Field(..., description="SpringBoot에서 전달받은 room_id")

class ChatRoomResponse(BaseModel):
    """SpringBoot로 반환하는 응답"""
    room_id: str = Field(..., description="채팅방 ID")
    user_id: str = Field(..., description="사용자 ID")
    created_at: datetime = Field(..., description="생성 시간")
    initial_message: str = Field(..., description="AI 초기 인사 메시지")
    is_new_room: bool = Field(..., description="새 방인지 기존 방인지")
