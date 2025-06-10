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
        print(f"채팅방 요청: member_id={request.member_id}, conversation_id={request.conversation_id}")
        print(f"사용자 정보: {request.user_info}")
        print(f"기존 메시지 개수: {len(request.messages)}")
        
        # TODO: MongoDB에서 기존 방 확인 (나중에 추가)
        # messages 리스트로 새 방인지 판단
        if len(request.messages) == 0:
            is_new_room = True
            print("채팅방 생성")
        else: 
            is_new_room = False
            print("채팅방 로드")

        if is_new_room:
            # LangGraph 서비스로 초기 메시지 생성
            bot_message = await chat_service.create_chat_session(
                conversation_id=request.conversation_id,
                user_info=request.user_info
            )
        
            print(f"AI 응답 생성 완료: {bot_message[:50]}...")
            # bot_message = "새 채팅방이 생성되었습니다. AI가 초기 인사 메시지를 보냅니다."
        else:
            bot_message = "기존 채팅방 답장입니다."
        # TODO: MongoDB에 채팅방과 메시지 저장 (나중에 추가)
        
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