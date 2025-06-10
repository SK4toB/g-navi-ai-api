# app/models/chat.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# MongoDB에서 오는 실제 메시지 형태를 처리하는 모델
class MongoMessage(BaseModel):
    """MongoDB에서 오는 실제 메시지 형태"""
    sender_type: str = Field(..., alias="senderType", description="발신자 타입 (USER/BOT)")
    message_text: str = Field(..., alias="messageText", description="메시지 내용")
    timestamp: Any = Field(None, description="메시지 시간 (받기만 하고 사용하지 않음)")
    
    class Config:
        extra = "ignore"  # 추가 필드들은 무시


# 요청 모델들
class ChatRoomCreate(BaseModel):
    """SpringBoot에서 전달받는 요청"""
    member_id: str = Field(..., alias="memberId", description="사용자 ID")
    conversation_id: str = Field(..., alias="conversationId", description="SpringBoot에서 전달받은 conversation ID")
    user_info: Dict[str, Any] = Field(..., alias="userInfo", description="SpringBoot에서 전달받은 사용자 정보")
    messages: List[MongoMessage] = Field(default=[], description="기존 메시지 목록 (빈 리스트면 새 방)")

class ChatRoomResponse(BaseModel):
    """SpringBoot로 반환하는 응답"""
    conversation_id: str = Field(..., alias="conversationId", description="채팅방 ID")
    bot_message: str = Field(..., alias="botMessage", description="AI 초기 인사 메시지")
    timestamp: datetime = Field(..., description="생성 시간")
    # member_id: str = Field(..., description="사용자 ID")
    # is_new_room: bool = Field(..., description="새 방인지 기존 방인지")