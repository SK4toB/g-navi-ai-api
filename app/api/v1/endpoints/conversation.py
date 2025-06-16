from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime

from app.models.chat import ChatRoomCreate, ChatRoomResponse
from app.api.deps import get_chat_service
from app.services.chat_service import ChatService


router = APIRouter()

@router.post("", response_model=ChatRoomResponse)
async def create_or_load_room(
    request: ChatRoomCreate,
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    채팅방 생성 또는 로드
    SpringBoot에서 member_id, conversation_id, user_info, messages와 함께 호출
    messages가 빈 리스트면 새 방, 아니면 기존 방 로드
    """
    try:
        print(f"채팅방 요청: member_id={request.member_id}, conversation_id={request.conversation_id}, user_info: {request.user_info}, 기존 메시지 개수: {len(request.messages)}")
        
        # messages 리스트로 새 방인지 판단
        if len(request.messages) == 0:
            is_new_room = True
            print("채팅방 생성")
        else: 
            is_new_room = False
            print("채팅방 로드")

        if is_new_room:
            bot_message = await chat_service.create_chat_session(
                conversation_id=request.conversation_id,
                user_info=request.user_info
            )
        
        else:
            load_result = await chat_service.load_chat_session(
                conversation_id=request.conversation_id,
                user_info=request.user_info,
                previous_messages=request.messages
            )
            # 로드 시에는 봇 메시지를 반환하지 않음
            bot_message = load_result.get("message", "채팅방을 로드했습니다.")
            print(f"로드 결과: {load_result['status']}")
        
        return ChatRoomResponse(
            conversationId=request.conversation_id,
            botMessage=bot_message,
            timestamp=datetime.utcnow(),
            # member_id=request.member_id,
            # is_new_room=is_new_room,
        )
        
    except Exception as e:
        print(f"채팅방 처리 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"채팅방 처리 실패: {str(e)}")