# API 라우터 모음

# app/api/v1/api.py
from fastapi import APIRouter
from app.api.v1.endpoints import (
    conversation, 
    message, 
    health, 
    session_management, 
    conversation_history,
    chroma,
)

api_router = APIRouter()

# 채팅방 관련 엔드포인트
api_router.include_router(
    conversation.router, 
    prefix="/conversations", 
    tags=["conversation"]
)

# 메시지 관련 엔드포인트  
api_router.include_router(
    message.router,
    prefix="/conversations",
    tags=["message"]
)

# 헬스체크 관련 엔드포인트
api_router.include_router(
    health.router,
    prefix="/health",
    tags=["system"]
)

# 세션 관리 엔드포인트 (세션 조회/종료)
api_router.include_router(
    session_management.router,
    prefix="/sessions",
    tags=["session-management"]
)

# 대화 히스토리 관리 엔드포인트 (히스토리 조회/삭제)
api_router.include_router(
    conversation_history.router,
    prefix="/conversation-history",
    tags=["conversation-history"]
)

# ChromaDB 관련 엔드포인트
api_router.include_router(
    chroma.router,
    prefix="/chroma",
    tags=["vector-database"]
)