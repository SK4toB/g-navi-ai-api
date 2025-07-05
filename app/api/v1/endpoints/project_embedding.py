# app/api/v1/endpoints/project_embedding.py
"""
프로젝트 데이터 임베딩 저장 API
Spring에서 전달받은 프로젝트 데이터를 임베딩하여 ChromaDB에 저장
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import uuid

from app.core.dependencies import get_chroma_service
from app.services.chroma_service import ChromaService
from app.services.project_embedding_service import ProjectEmbeddingService

router = APIRouter()


class ProjectData(BaseModel):
    """Spring에서 받는 프로젝트 데이터 모델"""
    employee_id: str = Field(..., description="직원 고유 ID")
    name: str = Field(..., description="직원 이름")
    project_name: str = Field(..., description="프로젝트명")
    domain: str = Field(..., description="도메인/업계")
    role: str = Field(..., description="수행 역할")
    scale: Optional[str] = Field(None, description="프로젝트 규모")
    start_year: Optional[int] = Field(None, description="시작 연도")
    end_year: Optional[int] = Field(None, description="종료 연도")
    skills: List[str] = Field(default=[], description="활용 기술/스킬")
    description: Optional[str] = Field(None, description="프로젝트 설명")
    achievements: Optional[str] = Field(None, description="주요 성과")
    key_experience: Optional[bool] = Field(False, description="핵심 경력 여부")
    
    class Config:
        extra = "allow"  # 추가 필드 허용


class ProjectBatchData(BaseModel):
    """여러 프로젝트 데이터 배치 처리용"""
    projects: List[ProjectData] = Field(..., description="프로젝트 데이터 리스트")
    batch_id: Optional[str] = Field(None, description="배치 처리 ID")


class ProjectEmbeddingResponse(BaseModel):
    """프로젝트 임베딩 저장 응답"""
    status: str = Field(..., description="처리 상태")
    message: str = Field(..., description="처리 메시지")
    employee_id: str = Field(..., description="직원 ID")
    project_name: str = Field(..., description="프로젝트명")
    document_id: str = Field(..., description="저장된 문서 ID")
    embedding_success: bool = Field(..., description="임베딩 성공 여부")
    stored_in_vectordb: bool = Field(..., description="벡터DB 저장 성공 여부")
    timestamp: datetime = Field(..., description="처리 시간")


class BatchEmbeddingResponse(BaseModel):
    """배치 처리 응답"""
    status: str = Field(..., description="전체 처리 상태")
    batch_id: str = Field(..., description="배치 ID")
    total_projects: int = Field(..., description="총 프로젝트 수")
    successful_projects: int = Field(..., description="성공한 프로젝트 수")
    failed_projects: int = Field(..., description="실패한 프로젝트 수")
    results: List[ProjectEmbeddingResponse] = Field(..., description="개별 처리 결과")
    processing_time_ms: float = Field(..., description="총 처리 시간(ms)")
    timestamp: datetime = Field(..., description="처리 완료 시간")


@router.post("/single", response_model=ProjectEmbeddingResponse)
async def store_single_project(
    project_data: ProjectData,
    embedding_service: ProjectEmbeddingService = Depends(lambda: ProjectEmbeddingService())
):
    """
    단일 프로젝트 데이터 임베딩 저장
    
    Args:
        project_data: 프로젝트 정보
        
    Returns:
        ProjectEmbeddingResponse: 처리 결과
    """
    try:
        print(f"단일 프로젝트 임베딩 저장 요청: {project_data.employee_id} - {project_data.project_name}")
        
        # 프로젝트 데이터 임베딩 및 저장
        result = await embedding_service.process_and_store_project(project_data)
        
        return ProjectEmbeddingResponse(
            status="success",
            message="프로젝트 데이터가 성공적으로 저장되었습니다",
            employee_id=project_data.employee_id,
            project_name=project_data.project_name,
            document_id=result["document_id"],
            embedding_success=result["embedding_success"],
            stored_in_vectordb=result["stored_in_vectordb"],
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        print(f"단일 프로젝트 저장 실패: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"프로젝트 데이터 저장 실패: {str(e)}"
        )


@router.post("/batch", response_model=BatchEmbeddingResponse)
async def store_batch_projects(
    batch_data: ProjectBatchData,
    embedding_service: ProjectEmbeddingService = Depends(lambda: ProjectEmbeddingService())
):
    """
    여러 프로젝트 데이터 배치 임베딩 저장
    
    Args:
        batch_data: 프로젝트 데이터 배치
        
    Returns:
        BatchEmbeddingResponse: 배치 처리 결과
    """
    import time
    start_time = time.time()
    
    try:
        batch_id = batch_data.batch_id or str(uuid.uuid4())
        projects = batch_data.projects
        
        print(f"배치 프로젝트 임베딩 저장 요청: {batch_id} - {len(projects)}개 프로젝트")
        
        results = []
        successful_count = 0
        failed_count = 0
        
        # 각 프로젝트 순차 처리
        for i, project_data in enumerate(projects, 1):
            try:
                print(f"  처리 중 ({i}/{len(projects)}): {project_data.employee_id} - {project_data.project_name}")
                
                # 프로젝트 데이터 임베딩 및 저장
                result = await embedding_service.process_and_store_project(project_data)
                
                response = ProjectEmbeddingResponse(
                    status="success",
                    message="성공적으로 저장됨",
                    employee_id=project_data.employee_id,
                    project_name=project_data.project_name,
                    document_id=result["document_id"],
                    embedding_success=result["embedding_success"],
                    stored_in_vectordb=result["stored_in_vectordb"],
                    timestamp=datetime.utcnow()
                )
                
                results.append(response)
                successful_count += 1
                
            except Exception as e:
                print(f"  개별 프로젝트 처리 실패: {str(e)}")
                
                error_response = ProjectEmbeddingResponse(
                    status="failed",
                    message=f"저장 실패: {str(e)}",
                    employee_id=project_data.employee_id,
                    project_name=project_data.project_name,
                    document_id="",
                    embedding_success=False,
                    stored_in_vectordb=False,
                    timestamp=datetime.utcnow()
                )
                
                results.append(error_response)
                failed_count += 1
        
        # 처리 시간 계산
        end_time = time.time()
        processing_time_ms = (end_time - start_time) * 1000
        
        # 전체 상태 결정
        overall_status = "success" if failed_count == 0 else (
            "partial_success" if successful_count > 0 else "failed"
        )
        
        print(f"배치 처리 완료: 성공 {successful_count}개, 실패 {failed_count}개")
        
        return BatchEmbeddingResponse(
            status=overall_status,
            batch_id=batch_id,
            total_projects=len(projects),
            successful_projects=successful_count,
            failed_projects=failed_count,
            results=results,
            processing_time_ms=processing_time_ms,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        end_time = time.time()
        processing_time_ms = (end_time - start_time) * 1000
        
        print(f"배치 프로젝트 저장 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"배치 프로젝트 데이터 저장 실패: {str(e)}"
        )


@router.get("/status/{document_id}")
async def get_embedding_status(
    document_id: str,
    chroma_service: ChromaService = Depends(get_chroma_service)
):
    """
    저장된 프로젝트 임베딩 상태 확인
    
    Args:
        document_id: 문서 ID
        
    Returns:
        Dict: 임베딩 상태 정보
    """
    try:
        print(f"임베딩 상태 확인 요청: {document_id}")
        
        if not chroma_service.is_available():
            raise HTTPException(status_code=503, detail="ChromaDB 서비스를 사용할 수 없습니다")
        
        # ChromaDB에서 문서 검색
        search_result = chroma_service.search_documents(
            query=document_id, 
            collection_type="career",
            n_results=1
        )
        
        if search_result["status"] == "success" and search_result["result_count"] > 0:
            return {
                "status": "found",
                "document_id": document_id,
                "exists_in_vectordb": True,
                "document_info": search_result["results"][0],
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "status": "not_found",
                "document_id": document_id,
                "exists_in_vectordb": False,
                "message": "해당 문서를 찾을 수 없습니다",
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"임베딩 상태 확인 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"상태 확인 실패: {str(e)}")


@router.delete("/remove/{document_id}")
async def remove_project_embedding(
    document_id: str,
    embedding_service: ProjectEmbeddingService = Depends(lambda: ProjectEmbeddingService())
):
    """
    저장된 프로젝트 임베딩 삭제
    
    Args:
        document_id: 삭제할 문서 ID
        
    Returns:
        Dict: 삭제 결과
    """
    try:
        print(f"프로젝트 임베딩 삭제 요청: {document_id}")
        
        result = await embedding_service.remove_project_embedding(document_id)
        
        return {
            "status": "success" if result["success"] else "failed",
            "message": result["message"],
            "document_id": document_id,
            "removed_from_vectordb": result["success"],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        print(f"프로젝트 임베딩 삭제 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"임베딩 삭제 실패: {str(e)}")


@router.get("/search/employee/{employee_id}")
async def search_employee_projects(
    employee_id: str,
    limit: int = 10,
    chroma_service: ChromaService = Depends(get_chroma_service)
):
    """
    특정 직원의 프로젝트 검색
    
    Args:
        employee_id: 직원 ID
        limit: 검색 결과 수 제한
        
    Returns:
        Dict: 검색 결과
    """
    try:
        print(f"직원 프로젝트 검색: {employee_id}")
        
        if not chroma_service.is_available():
            raise HTTPException(status_code=503, detail="ChromaDB 서비스를 사용할 수 없습니다")
        
        # 직원 ID로 검색
        search_result = chroma_service.search_documents(
            query=employee_id,
            collection_type="career", 
            n_results=limit
        )
        
        if search_result["status"] == "success":
            return {
                "status": "success",
                "employee_id": employee_id,
                "project_count": search_result["result_count"],
                "projects": search_result["results"],
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "status": "failed",
                "employee_id": employee_id,
                "error": search_result.get("error", "검색 실패"),
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"직원 프로젝트 검색 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"검색 실패: {str(e)}")