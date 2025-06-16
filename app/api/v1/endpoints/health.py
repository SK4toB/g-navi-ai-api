# app/api/v1/endpoints/health.py
from fastapi import APIRouter, Depends
from datetime import datetime
import os
from app.api.deps import get_chat_service
from app.services.chat_service import ChatService

router = APIRouter()

@router.get("")
async def health_check():
    """
    시스템 헬스체크
    """
    return {
        "status": "healthy",
        "service": "career_path_chat_api",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": os.getenv("ENVIRONMENT", "development")
    }

@router.get("/detailed")
async def detailed_health_check():
    """
    상세 헬스체크 (필요시 사용)
    """
    try:
        # OpenAI API 키 존재 여부 확인
        openai_status = "configured" if os.getenv("OPENAI_API_KEY") else "not_configured"
        
        return {
            "status": "healthy",
            "service": "career_path_chat_api",
            "version": "1.0.0", 
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "openai": openai_status,
                "api": "operational"
            },
            "environment": os.getenv("ENVIRONMENT", "development")
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
    

@router.get("/openai")
async def test_openai():
    """OpenAI API 간단한 연결 테스트"""
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        return {
            "status": "failed",
            "error": "OPENAI_API_KEY가 설정되지 않았습니다",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    try:
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(api_key=api_key)
        
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": "당신은 시스템 상태를 확인하는 봇입니다. 한 문장으로 간단히 응답하세요."
                },
                {
                    "role": "user", 
                    "content": "OpenAI API 연결 테스트입니다. 정상 작동 확인 메시지를 보내주세요."
                }
            ],
            max_tokens=50,
            temperature=0.1
        )

        test_response = response.choices[0].message.content.strip()
        
        return {
            "status": "success",
            "message": "OpenAI API 연결 및 응답 생성 정상",
            "test_response": test_response,
            "model_used": response.model,
            "tokens_used": {
                "prompt": response.usage.prompt_tokens,
                "completion": response.usage.completion_tokens,
                "total": response.usage.total_tokens
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
    

###############################################################

# 대화 히스토리 관련 엔드포인트들
@router.get("/conversations/history")
async def get_all_conversation_histories():
    """전체 대화 히스토리 요약 조회"""
    try:
        from app.graphs.nodes.openai_response_node import get_history_manager
        
        history_manager = get_history_manager()
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

@router.get("/conversations/{conversation_id}/history")
async def get_conversation_history(conversation_id: str):
    """특정 대화방의 히스토리 조회"""
    try:
        from app.graphs.nodes.openai_response_node import get_history_manager
        
        history_manager = get_history_manager()
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

@router.delete("/conversations/{conversation_id}/history")
async def clear_conversation_history(conversation_id: str):
    """특정 대화방의 히스토리 삭제"""
    try:
        from app.graphs.nodes.openai_response_node import get_history_manager
        
        history_manager = get_history_manager()
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

###############################################################

@router.get("/sessions/list")
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


@router.get("/sessions/{conversation_id}")
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


@router.delete("/sessions/{conversation_id}")
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

@router.delete("/sessions")
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

@router.delete("/sessions/user/{user_name}")
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