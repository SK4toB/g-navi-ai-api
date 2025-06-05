# API 라우터 모음

# app/api/v1/api.py
from fastapi import APIRouter
from api.v1.endpoints import room, message, health, simple_chat

api_router = APIRouter()

# 채팅방 관련 엔드포인트
api_router.include_router(
    room.router, 
    prefix="/chat", 
    tags=["rooms"]
)

# 메시지 관련 엔드포인트  
api_router.include_router(
    message.router,
    prefix="/chat",
    tags=["messages"]
)

# 헬스체크 관련 엔드포인트
api_router.include_router(
    health.router,
    tags=["system"]
)

# RAG 기반 간단한 채팅 엔드포인트 추가
api_router.include_router(
    simple_chat.router,
    prefix="/rag",
    tags=["RAG Chat"]
)