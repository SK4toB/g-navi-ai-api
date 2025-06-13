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