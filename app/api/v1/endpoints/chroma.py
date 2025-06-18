# app/api/v1/endpoints/chroma.py

from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from typing import Dict, Any

from app.core.dependencies import get_chroma_service
from app.services.chroma_service import ChromaService


router = APIRouter()


@router.get("/health")
async def chroma_health_check(
    chroma_service: ChromaService = Depends(get_chroma_service)
):
    """ChromaDB 헬스체크"""
    try:
        # 연결 테스트
        connection_result = chroma_service.test_connection()
        basic_info = chroma_service.get_basic_info()
        
        return {
            "status": "healthy" if chroma_service.is_available() else "unavailable",
            "timestamp": datetime.utcnow().isoformat(),
            "connection": connection_result,
            "info": basic_info
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/stats")
async def get_chroma_stats(
    chroma_service: ChromaService = Depends(get_chroma_service)
):
    """ChromaDB 통계 정보"""
    try:
        if not chroma_service.is_available():
            raise HTTPException(status_code=503, detail="ChromaDB 서비스를 사용할 수 없습니다")
        
        # 컬렉션 목록 조회
        collections_result = chroma_service.list_collections()
        basic_info = chroma_service.get_basic_info()
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "basic_info": basic_info,
            "collections": collections_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"통계 조회 실패: {str(e)}")


@router.get("/collections")
async def list_collections(
    chroma_service: ChromaService = Depends(get_chroma_service)
):
    """ChromaDB 컬렉션 목록 조회"""
    try:
        if not chroma_service.is_available():
            raise HTTPException(status_code=503, detail="ChromaDB 서비스를 사용할 수 없습니다")
        
        collections_result = chroma_service.list_collections()
        
        if collections_result.get("status") == "success":
            return {
                "status": "success",
                "collections": collections_result.get("collections", []),
                "total_count": collections_result.get("count", 0),
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=500, 
                detail=f"컬렉션 조회 실패: {collections_result.get('error', 'Unknown error')}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"컬렉션 조회 실패: {str(e)}")


@router.get("/test")
async def test_chroma_connection(
    chroma_service: ChromaService = Depends(get_chroma_service)
):
    """ChromaDB 연결 테스트 (개발용)"""
    try:
        connection_test = chroma_service.test_connection()
        basic_info = chroma_service.get_basic_info()
        collections = chroma_service.list_collections()
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "tests": {
                "connection": connection_test,
                "basic_info": basic_info,
                "collections_count": collections.get("count", 0) if collections.get("status") == "success" else "error"
            },
            "summary": {
                "available": chroma_service.is_available(),
                "connection_mode": basic_info.get("connection_mode"),
                "collection_name": basic_info.get("collection_name"),
                "collections_accessible": collections.get("status") == "success"
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/info")
async def get_chroma_info(
    chroma_service: ChromaService = Depends(get_chroma_service)
):
    """ChromaDB 기본 정보 조회"""
    try:
        basic_info = chroma_service.get_basic_info()
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "info": basic_info
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }