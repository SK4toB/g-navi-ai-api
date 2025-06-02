# app/models/chat.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# 요청 모델들
class ChatRoomCreate(BaseModel):
    user_id: str = Field(..., description="사용자 ID")
    user_info: Dict[str, Any] = Field(..., description="SpringBoot에서 전달받은 사용자 정보")
    room_name: Optional[str] = Field(None, description="채팅방 이름 (선택)")

class MessageCreate(BaseModel):
    user_id: str = Field(..., description="사용자 ID")
    message: str = Field(..., min_length=1, max_length=4000, description="사용자 메시지")
    message_type: str = Field(default="user", description="메시지 타입")

# 응답 모델들
class AIMessageResponse(BaseModel):
    message_id: str
    message: str
    message_type: str
    timestamp: datetime

class MessageResponse(BaseModel):
    message_id: str = Field(..., description="사용자 메시지 ID")
    ai_response: AIMessageResponse = Field(..., description="AI 응답")

class ChatRoomResponse(BaseModel):
    room_id: str = Field(..., description="채팅방 ID")
    user_id: str = Field(..., description="사용자 ID")
    created_at: datetime = Field(..., description="생성 시간")
    initial_message: str = Field(..., description="AI 초기 인사 메시지")

# 내부 처리용 모델들
class UserInfo(BaseModel):
    user_id: str
    name: str
    projects: List[Dict[str, Any]] = []
    skills: List[str] = []
    preferences: Dict[str, Any] = {}