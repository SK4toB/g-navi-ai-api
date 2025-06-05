# API 라우터 모음

# app/api/v1/api.py
from fastapi import APIRouter
from app.api.v1.endpoints import conversation, message, health

api_router = APIRouter()

# 채팅방 관련 엔드포인트
api_router.include_router(
    conversation.router, 
    prefix="/chatroom", 
    tags=["conversation"]
)

# 메시지 관련 엔드포인트  
api_router.include_router(
    message.router,
    prefix="/chatroom",
    tags=["message"]
)

# 헬스체크 관련 엔드포인트
api_router.include_router(
    health.router,
    tags=["system"]
)