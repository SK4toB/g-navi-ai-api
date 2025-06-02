# 채팅 관련 API
# app/api/v1/endpoints/message.py

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
import uuid
from datetime import datetime

from app.models.chat import ChatRoomCreate, ChatRoomResponse, MessageCreate, MessageResponse
from app.services.openai_service import OpenAIService

router = APIRouter()

# 의존성 주입
def get_openai_service():
    return OpenAIService()


@router.post("/rooms/{room_id}/messages", response_model=MessageResponse)
async def send_message(
    room_id: str,
    message_data: MessageCreate,
    openai_service: OpenAIService = Depends(get_openai_service)
):
    """
    사용자 메시지 전송 및 AI 응답 생성
    """
    print(f"메시지 전송 요청: room_id={room_id}, user_id={message_data.user_id}")
    print(f"사용자 메시지: {message_data.message}")
    
    try:
        user_message_id = str(uuid.uuid4())
        ai_message_id = str(uuid.uuid4())
        
        print("OpenAI 응답 생성 중...")
        # OpenAI를 통한 AI 응답 생성 (단순한 응답)
        ai_response_text = await openai_service.generate_response(
            message_data.message,
            context=f"사용자 ID: {message_data.user_id}, 채팅방 ID: {room_id}"
        )
        print(f"AI 응답 생성 완료: {ai_response_text[:100]}...")
        
        # 응답 구성
        ai_response = {
            "message_id": ai_message_id,
            "message": ai_response_text,
            "message_type": "ai",
            "timestamp": datetime.utcnow()
        }
        
        return MessageResponse(
            message_id=user_message_id,
            ai_response=ai_response
        )
        
    except Exception as e:
        print(f"메시지 처리 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"메시지 처리 실패: {str(e)}")
