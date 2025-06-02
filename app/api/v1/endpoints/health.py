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