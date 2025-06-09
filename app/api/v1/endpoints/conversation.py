from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime

from app.models.chat import ChatRoomCreate, ChatRoomResponse
from app.api.deps import get_chat_service
from app.services.chat_service import ChatService


router = APIRouter()

@router.post("/", response_model=ChatRoomResponse)
async def create_or_load_room(
    request: ChatRoomCreate,
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    채팅방 생성 또는 로드
    SpringBoot에서 member_id, conversation_id, user_info와 함께 호출
    """
    try:
        print(f"채팅방 요청: member_id={request.member_id}, conversation_id={request.conversation_id}")
        print(f"사용자 정보: {request.user_info}")
        
        # TODO: MongoDB에서 기존 방 확인 (나중에 추가)
        # 지금은 간단하게 처리
        is_new_room = True  # 임시로 항상 새 방으로 처리
        
        print(f"{'새 채팅방' if is_new_room else '기존 채팅방'}: {request.conversation_id}")
        
        # LangGraph 서비스로 초기 메시지 생성
        bot_message = await chat_service.create_chat_session(
            conversation_id=request.conversation_id,
            user_info=request.user_info
        )
        
        print(f"AI 응답 생성 완료: {bot_message[:50]}...")
        
        # TODO: MongoDB에 채팅방과 메시지 저장 (나중에 추가)
        
        return ChatRoomResponse(
            conversation_id=request.conversation_id,
            bot_message=bot_message,
            timestamp=datetime.utcnow(),
            # member_id=request.member_id,
            # is_new_room=is_new_room,
        )
        
    except Exception as e:
        print(f"채팅방 처리 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"채팅방 처리 실패: {str(e)}")