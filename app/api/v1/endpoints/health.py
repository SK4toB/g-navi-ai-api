# app/api/v1/endpoints/health.py
from fastapi import APIRouter
from datetime import datetime
import os

router = APIRouter()

@router.get("/health")
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

@router.get("/health/detailed")
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
    

@router.get("/health/openai")
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
        
        # 간단한 테스트 요청
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "테스트"}],
            max_tokens=10
        )

        print(response)
        
        return {
            "status": "success",
            "response": response.choices[0].message.content,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }