# app/api/v1/endpoints/vector_test.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from services.vector_db_service import query_vector

router = APIRouter()

class VectorSearchRequest(BaseModel):
    question: str
    top_k: int = 5

class VectorSearchResponse(BaseModel):
    question: str
    results: List[Dict[str, Any]]
    total_found: int

@router.post("/vector-search", response_model=VectorSearchResponse)
async def search_vectors_only(request: VectorSearchRequest):
    """OpenAI 없이 벡터 검색만 수행"""
    
    try:
        # 벡터 검색
        search_results = query_vector(request.question, top_k=request.top_k)
        
        # 결과 포맷팅
        formatted_results = []
        
        if search_results and search_results.get('documents'):
            documents = search_results['documents'][0]
            metadatas = search_results.get('metadatas', [[]])[0]
            distances = search_results.get('distances', [[]])[0]
            ids = search_results.get('ids', [[]])[0]
            
            for i, doc in enumerate(documents):
                result = {
                    "id": ids[i] if i < len(ids) else f"result_{i}",
                    "content": doc,
                    "distance": distances[i] if i < len(distances) else 1.0,
                    "similarity": 1 - (distances[i] if i < len(distances) else 1.0),
                    "metadata": {
                        "year": metadatas[i].get('year', 'N/A') if i < len(metadatas) else 'N/A',
                        "role": metadatas[i].get('role', 'N/A') if i < len(metadatas) else 'N/A',
                        "domain": metadatas[i].get('domain', 'N/A') if i < len(metadatas) else 'N/A',
                        "skills": metadatas[i].get('skills', 'N/A') if i < len(metadatas) else 'N/A'
                    }
                }
                formatted_results.append(result)
        
        return VectorSearchResponse(
            question=request.question,
            results=formatted_results,
            total_found=len(formatted_results)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"벡터 검색 중 오류 발생: {str(e)}"
        )

@router.get("/vector-stats")
async def get_vector_stats():
    """벡터 데이터베이스 통계"""
    
    try:
        from services.vector_db_service import collection
        
        count = collection.count()
        
        # 샘플 데이터 확인
        sample = collection.peek(limit=3)
        
        return {
            "total_vectors": count,
            "collection_name": "mentor_history",
            "sample_ids": sample.get('ids', []),
            "status": "healthy"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"통계 조회 중 오류 발생: {str(e)}"
        )