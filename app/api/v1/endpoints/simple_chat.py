from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from services.rag_service import RAGService

router = APIRouter()

class SimpleChatRequest(BaseModel):
    question: str
    top_k: Optional[int] = 5

class SimpleChatResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float
    question: str

@router.post("/simple-chat", response_model=SimpleChatResponse)
async def simple_chat_with_jinavi(request: SimpleChatRequest):
    """구성원 성장 이력 기반 간단한 채팅"""
    
    try:
        if not request.question.strip():
            raise HTTPException(
                status_code=400,
                detail="질문을 입력해주세요."
            )
        
        # RAG 서비스 초기화
        rag_service = RAGService()
        
        # 답변 생성
        result = await rag_service.generate_answer(
            user_question=request.question,
            top_k=request.top_k
        )
        
        # 에러가 있는 경우 처리
        if "error" in result:
            raise HTTPException(
                status_code=500,
                detail=f"답변 생성 실패: {result['error']}"
            )
        
        return SimpleChatResponse(
            answer=result["answer"],
            sources=result["sources"],
            confidence=result["confidence"],
            question=result["question"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"처리 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/search-cases")
async def search_growth_cases(request: SimpleChatRequest):
    """성장 사례만 검색 (답변 생성 없이)"""
    
    try:
        from services.vector_db_service import query_vector
        
        # 벡터 검색만 수행
        search_results = query_vector(request.question, top_k=request.top_k)
        
        # 결과 포맷팅
        rag_service = RAGService()
        formatted_cases = rag_service.format_search_results(search_results)
        confidence = rag_service.calculate_confidence(search_results)
        
        return {
            "query": request.question,
            "cases": formatted_cases,
            "confidence": confidence,
            "total_found": len(formatted_cases)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"검색 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/health")
async def health_check():
    """RAG 서비스 상태 확인"""
    
    try:
        from services.vector_db_service import collection
        
        # ChromaDB 컬렉션 상태 확인
        count = collection.count()
        
        return {
            "status": "healthy",
            "vector_db": "connected",
            "total_vectors": count,
            "collection_name": "mentor_history"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }