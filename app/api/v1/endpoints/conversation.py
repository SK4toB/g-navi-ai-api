"""
* @className : Conversation API Endpoints
* @description : 채팅방 관리 API 엔드포인트 모듈
*                G-Navi AI 시스템의 채팅방 생성, 로드, 관리 기능을 제공하는 REST API입니다.
*                SpringBoot 백엔드와 연동하여 채팅방 생명주기를 관리합니다.
*
*                주요 기능:
*                - 채팅방 생성 또는 기존 채팅방 로드
*                - SpringBoot와의 데이터 연동
*                - 채팅방 상태 관리 및 응답
*                - 에러 처리 및 예외 관리
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime

from app.models.chat import ChatRoomCreate, ChatRoomResponse
from app.api.deps import get_chat_service
from app.services.chat_service import ChatService


router = APIRouter()  # FastAPI 라우터 생성

@router.post("", response_model=ChatRoomResponse)
async def create_or_load_room(
    request: ChatRoomCreate,
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    채팅방을 생성하거나 로드한다.
    SpringBoot에서 member_id, conversation_id, user_info, messages와 함께 호출됩니다.
    messages가 빈 리스트면 새 방을 생성하고, 아니면 기존 방을 로드합니다.
    
    @param request: ChatRoomCreate - 채팅방 생성 요청 정보
    @param chat_service: ChatService - 주입된 채팅 서비스
    @return ChatRoomResponse - 채팅방 생성/로드 결과 응답
    @throws HTTPException - 채팅방 생성/로드 실패 시
    """
    try:  # 예외 처리 시작
        print(f"채팅방 요청: member_id={request.member_id}, conversation_id={request.conversation_id}, user_info: {request.user_info}, 기존 메시지 개수: {len(request.messages)}")  # 요청 정보 로그
        
        # messages 리스트로 새 방인지 판단
        if len(request.messages) == 0:  # 메시지가 없으면 새 채팅방
            is_new_room = True  # 새 방 플래그 설정
            print("채팅방 생성")  # 새 방 생성 로그
        else:  # 메시지가 있으면 기존 채팅방
            is_new_room = False
            print("채팅방 로드")  # 기존 방 로드 로그

        if is_new_room:
            enhanced_user_info = {**request.user_info, "member_id": request.member_id}
            
            bot_message = await chat_service.create_chat_session(
                conversation_id=request.conversation_id,
                user_info=enhanced_user_info
            )
        
        else:
            enhanced_user_info = {**request.user_info, "member_id": request.member_id}
            
            load_result = await chat_service.load_chat_session(
                conversation_id=request.conversation_id,
                user_info=enhanced_user_info,
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