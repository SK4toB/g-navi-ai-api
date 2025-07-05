# app/api/v1/endpoints/conversation_history.py
"""
* @className : Conversation History API Endpoints
* @description : 대화 내역 API 엔드포인트 모듈
*                사용자의 대화 내역을 관리하는 REST API를 제공합니다.
*                대화 기록 조회, 삭제, 통계 기능을 담당합니다.
*
* @modification : 2025.07.01(이재원) 최초생성
*
* @author 이재원
* @Date 2025.07.01
* @version 1.0
* @see FastAPI, ConversationHistoryManager
*  == 개정이력(Modification Information) ==
*  
*   수정일        수정자        수정내용
*   ----------   --------     ---------------------------
*   2025.07.01   이재원       최초 생성
*  
* Copyright (C) by G-Navi AI System All right reserved.
"""
from fastapi import APIRouter
from datetime import datetime

router = APIRouter()

@router.get("")
async def get_all_conversation_histories():
    """전체 대화 히스토리 요약 조회"""
    try:
        from app.core.dependencies import get_service_container
        
        container = get_service_container()
        history_manager = container.history_manager
        active_conversations = history_manager.get_all_active_conversations()
        
        histories = []
        for conv_id in active_conversations:
            summary = history_manager.get_history_summary(conv_id)
            histories.append(summary)
        
        return {
            "status": "success",
            "total_conversations": len(histories),
            "conversations": histories,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"대화 히스토리 조회 실패: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/{conversation_id}")
async def get_conversation_history(conversation_id: str):
    """특정 대화방의 히스토리 조회"""
    try:
        from app.core.dependencies import get_service_container
        
        container = get_service_container()
        history_manager = container.history_manager
        history = history_manager.get_history_with_metadata(conversation_id)
        summary = history_manager.get_history_summary(conversation_id)
        
        return {
            "status": "success",
            "conversation_id": conversation_id,
            "summary": summary,
            "messages": history,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "conversation_id": conversation_id,
            "error": f"대화 히스토리 조회 실패: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }

@router.delete("/{conversation_id}")
async def clear_conversation_history(conversation_id: str):
    """특정 대화방의 히스토리 삭제"""
    try:
        from app.core.dependencies import get_service_container
        
        container = get_service_container()
        history_manager = container.history_manager
        history_manager.clear_history(conversation_id)
        
        return {
            "status": "success",
            "message": f"대화 히스토리가 삭제되었습니다: {conversation_id}",
            "conversation_id": conversation_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "conversation_id": conversation_id,
            "error": f"대화 히스토리 삭제 실패: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }