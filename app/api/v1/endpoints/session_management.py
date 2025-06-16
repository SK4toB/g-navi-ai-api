# app/api/v1/endpoints/session_management.py
from fastapi import APIRouter, Depends
from datetime import datetime
from app.api.deps import get_chat_service
from app.services.chat_service import ChatService

router = APIRouter()

@router.get("/list")
async def get_all_active_sessions(
    chat_service: ChatService = Depends(get_chat_service)
):
    """현재 열려있는 전체 세션 조회"""
    try:
        return chat_service.get_all_active_sessions()
    except Exception as e:
        return {
            "error": f"전체 세션 조회 실패: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/{conversation_id}")
async def get_session_health(
    conversation_id: str,
    chat_service: ChatService = Depends(get_chat_service)
):
    """특정 채팅방 세션 헬스체크"""
    try:
        health_info = chat_service.get_session_health(conversation_id)
        return health_info
    except Exception as e:
        return {
            "conversation_id": conversation_id,
            "status": "error",
            "message": f"헬스체크 실패: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }

@router.delete("/{conversation_id}")
async def close_session(
    conversation_id: str,
    chat_service: ChatService = Depends(get_chat_service)
):
    """특정 세션 수동 종료"""
    try:
        result = await chat_service.close_chat_session(conversation_id)
        return result
    except Exception as e:
        return {
            "status": "error",
            "message": f"세션 종료 실패: {str(e)}",
            "conversation_id": conversation_id,
            "timestamp": datetime.utcnow().isoformat()
        }

@router.delete("")
async def close_all_sessions(
    chat_service: ChatService = Depends(get_chat_service)
):
    """모든 세션 수동 종료"""
    try:
        result = chat_service.close_all_sessions()
        return result
    except Exception as e:
        return {
            "status": "error",
            "message": f"전체 세션 종료 실패: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }

@router.delete("/user/{user_name}")
async def close_user_sessions(
    user_name: str,
    chat_service: ChatService = Depends(get_chat_service)
):
    """특정 사용자의 모든 세션 종료"""
    try:
        result = chat_service.close_sessions_by_user(user_name)
        return result
    except Exception as e:
        return {
            "status": "error",
            "message": f"사용자 세션 종료 실패: {str(e)}",
            "user_name": user_name,
            "timestamp": datetime.utcnow().isoformat()
        }