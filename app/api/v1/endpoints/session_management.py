# app/api/v1/endpoints/session_management.py
"""
* @className : Session Management API Endpoints
* @description : 세션 관리 API 엔드포인트 모듈
*                채팅 세션 관리 기능을 제공하는 REST API입니다.
*                세션 생성, 조회, 삭제 등의 기능을 담당합니다.
*
"""

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
    """
    🔚 특정 세션 수동 종료 (VectorDB 자동 구축 포함)
    
    세션을 수동으로 종료하면서 해당 세션의 모든 대화 내역을
    사용자별 VectorDB에 자동으로 저장합니다.
    
    Args:
        conversation_id: 종료할 세션 ID
        
    Returns:
        종료 결과 (VectorDB 구축 성공 여부 포함)
    """
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

@router.post("/cleanup")
async def manual_cleanup_sessions(
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    🧹 만료된 세션 수동 정리 (VectorDB 구축 포함)
    
    타임아웃된 모든 세션을 찾아서 각 세션의 대화 내역을
    사용자별 VectorDB에 저장한 후 세션을 정리합니다.
    
    Returns:
        정리된 세션 목록과 VectorDB 구축 결과
    """
    try:
        result = await chat_service.session_manager.manual_cleanup(chat_service.get_session_messages)
        return result
    except Exception as e:
        return {
            "status": "error",
            "message": f"수동 세션 정리 실패: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/cleanup/status")
async def get_cleanup_status(
    chat_service: ChatService = Depends(get_chat_service)
):
    """자동 정리 상태 조회"""
    try:
        status = chat_service.session_manager.get_cleanup_status()
        return {
            "status": "success",
            "cleanup_status": status,
            "message": "자동 정리 상태 조회 완료"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"자동 정리 상태 조회 실패: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }

@router.post("/cleanup/start")
async def start_auto_cleanup(
    chat_service: ChatService = Depends(get_chat_service)
):
    """자동 세션 정리 시작"""
    try:
        await chat_service.start_auto_cleanup()
        status = chat_service.session_manager.get_cleanup_status()
        return {
            "status": "success",
            "message": "자동 세션 정리 시작됨",
            "cleanup_status": status
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"자동 정리 시작 실패: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }

@router.post("/cleanup/stop")
async def stop_auto_cleanup(
    chat_service: ChatService = Depends(get_chat_service)
):
    """자동 세션 정리 중지"""
    try:
        await chat_service.stop_auto_cleanup()
        status = chat_service.session_manager.get_cleanup_status()
        return {
            "status": "success",
            "message": "자동 세션 정리 중지됨",
            "cleanup_status": status
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"자동 정리 중지 실패: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/vectordb/{member_id}/stats")
async def get_user_vectordb_stats(
    member_id: str,
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    📊 사용자별 VectorDB 통계 조회
    
    특정 사용자(member_id)의 저장된 채팅 세션 통계를 조회합니다.
    
    Args:
        member_id: 사용자 고유 ID
        
    Returns:
        {
            "member_id": "사용자 ID",
            "total_sessions": "총 저장된 세션 수",
            "created_at": "첫 세션 저장 시간",
            "last_updated": "마지막 업데이트 시간",
            "sessions": "각 세션별 상세 정보"
        }
        
    🔒 개인정보 보호: 해당 사용자의 데이터만 접근 가능
    """
    try:
        from app.utils.session_vectordb_builder import session_vectordb_builder
        stats = session_vectordb_builder.get_user_session_stats(member_id)
        return {
            "status": "success",
            "member_id": member_id,
            "stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"VectorDB 통계 조회 실패: {str(e)}",
            "member_id": member_id,
            "timestamp": datetime.utcnow().isoformat()
        }

@router.post("/vectordb/{member_id}/search")
async def search_user_sessions(
    member_id: str,
    request_body: dict,
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    🔍 사용자별 과거 세션 VectorDB 검색
    
    특정 사용자의 과거 채팅 세션에서 질문과 관련된 대화 내용을
    의미 기반으로 검색합니다.
    
    Args:
        member_id: 사용자 고유 ID
        request_body: {
            "query": "검색할 질문 또는 키워드",
            "k": "반환할 최대 결과 수 (기본값: 5)"
        }
        
    Returns:
        관련 과거 대화 내용 목록 (관련도 점수 포함)
        
    💡 사용 예시:
    - "이전에 데이터 사이언티스트에 대해 물어봤는데..."
    - "Python 학습 관련해서 상담받은 내용 찾기"
    - "커리어 전환 관련 이전 대화 검색"
    
    🔒 개인정보 보호: 해당 사용자의 VectorDB에서만 검색
    """
    try:
        query = request_body.get("query", "")
        k = request_body.get("k", 5)
        
        if not query:
            return {
                "status": "error",
                "message": "검색 쿼리가 필요합니다",
                "member_id": member_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        from app.utils.session_vectordb_builder import session_vectordb_builder
        results = session_vectordb_builder.search_user_sessions(member_id, query, k)
        
        return {
            "status": "success",
            "member_id": member_id,
            "query": query,
            "results": results,
            "result_count": len(results),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"세션 검색 실패: {str(e)}",
            "member_id": member_id,
            "timestamp": datetime.utcnow().isoformat()
        }