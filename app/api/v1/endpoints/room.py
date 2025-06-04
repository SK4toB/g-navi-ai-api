from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime

from app.models.chat import ChatRoomCreate, ChatRoomResponse
from app.services.langgraph_interface import LangGraphService, MockLangGraphService

router = APIRouter()

# 의존성 주입 - 나중에 실제 LangGraphService로 교체
def get_langgraph_service() -> LangGraphService:
    return MockLangGraphService()

@router.post("/rooms", response_model=ChatRoomResponse)
async def create_or_load_room(
    request: ChatRoomCreate,
    langgraph_service: LangGraphService = Depends(get_langgraph_service)
):
    """
    채팅방 생성 또는 로드
    SpringBoot에서 user_id, room_id, user_info와 함께 호출
    """
    try:
        print(f"📋 채팅방 요청: user_id={request.user_id}, room_id={request.room_id}")
        print(f"👤 사용자 정보: {request.user_info}")
        
        # TODO: MongoDB에서 기존 방 확인 (나중에 추가)
        # 지금은 간단하게 처리
        is_new_room = True  # 임시로 항상 새 방으로 처리
        
        print(f"🆕 {'새 채팅방' if is_new_room else '기존 채팅방'}: {request.room_id}")
        
        # LangGraph 서비스로 초기 메시지 생성
        initial_message = await langgraph_service.generate_initial_message(
            room_id=request.room_id,
            user_info=request.user_info,
            is_new_room=is_new_room
        )
        
        print(f"AI 응답 생성 완료: {initial_message[:50]}...")
        
        # TODO: MongoDB에 채팅방과 메시지 저장 (나중에 추가)
        
        return ChatRoomResponse(
            room_id=request.room_id,
            user_id=request.user_id,
            is_new_room=is_new_room,
            created_at=datetime.utcnow(),
            initial_message=initial_message
        )
        
    except Exception as e:
        print(f"❌ 채팅방 처리 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"채팅방 처리 실패: {str(e)}")