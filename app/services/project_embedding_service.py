            # app/services/project_embedding_service.py
"""
프로젝트 데이터 임베딩 및 벡터DB 저장 서비스
"""

import os
import json
import uuid
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document

from app.config.settings import settings


class ProjectEmbeddingService:
    """프로젝트 데이터 임베딩 및 ChromaDB 저장 서비스"""
    
    def __init__(self):
        # ChromaDB 설정 (기존 설정과 동일)
        self.base_url = "https://sk-gnavi4.skala25a.project.skala-ai.com/vector/api/v2"
        self.tenant = "default_tenant"
        self.database = "default_database"
        self.collections_url = f"{self.base_url}/tenants/{self.tenant}/databases/{self.database}/collections"
        
        # 기존 career_history 컬렉션 사용
        self.collection_name = "gnavi4_career_history_prod"
        self.collection_id = None
        
        # 임베딩 설정
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            dimensions=1536
        )
        
        # HTTP 헤더
        self.headers = {"Content-Type": "application/json"}
        
        # 컬렉션 ID 조회
        self._get_collection_id()
    
    def _get_collection_id(self):
        """컬렉션 ID 조회 및 설정"""
        try:
            response = requests.get(self.collections_url, headers=self.headers, timeout=30)
            if response.status_code == 200:
                collections = response.json()
                for collection in collections:
                    if collection.get('name') == self.collection_name:
                        self.collection_id = collection.get('id')
                        print(f" [ProjectEmbeddingService] 컬렉션 연결: {self.collection_name} (ID: {self.collection_id})")
                        return
                print(f"- [ProjectEmbeddingService] 컬렉션을 찾을 수 없습니다: {self.collection_name}")
            else:
                print(f"- [ProjectEmbeddingService] 컬렉션 목록 조회 실패: {response.status_code}")
                
        except Exception as e:
            print(f"- [ProjectEmbeddingService] 컬렉션 ID 조회 실패: {e}")
    
    def search_projects_by_query(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        """쿼리로 프로젝트 검색"""
        if not self.collection_id:
            return {
                "success": False,
                "message": "ChromaDB 컬렉션 ID를 찾을 수 없습니다"
            }
        
        try:
            # 쿼리 임베딩 생성
            query_embedding = self.embeddings.embed_query(query)
            
            # 검색 요청
            search_data = {
                "query_embeddings": [query_embedding],
                "n_results": n_results,
                "include": ["documents", "metadatas"]
            }
            
            search_url = f"{self.collections_url}/{self.collection_id}/query"
            response = requests.post(
                search_url,
                headers=self.headers,
                json=search_data,
                timeout=30
            )
            
            if response.status_code == 200:
                results = response.json()
                documents = results.get('documents', [[]])
                metadatas = results.get('metadatas', [[]])
                
                # 결과 포맷팅
                formatted_results = []
                if documents and len(documents) > 0:
                    for i in range(len(documents[0])):
                        doc = documents[0][i] if documents[0] else ""
                        meta = metadatas[0][i] if metadatas and metadatas[0] else {}
                        
                        formatted_results.append({
                            "document": doc,
                            "metadata": meta,
                            "rank": i + 1
                        })
                
                return {
                    "success": True,
                    "results": formatted_results,
                    "total_results": len(formatted_results)
                }
            else:
                return {
                    "success": False,
                    "message": f"검색 실패: HTTP {response.status_code}"
                }
                
        except Exception as e:
            print(f"- [ProjectEmbeddingService] 검색 중 오류: {str(e)}")
            return {
                "success": False,
                "message": f"검색 오류: {str(e)}"
            }
    
    async def process_and_store_project(self, project_data) -> Dict[str, Any]:
        """
        프로젝트 데이터를 처리하여 임베딩하고 ChromaDB에 저장
        
        Args:
            project_data: ProjectData 모델 인스턴스
            
        Returns:
            Dict: 처리 결과
        """
        try:
            # 1. 프로젝트 데이터를 문서 형태로 변환
            document_content = self._format_project_as_document(project_data)
            
            # 2. 임베딩 생성
            embedding = await self._create_embedding(document_content)
            
            # 3. 메타데이터 생성
            metadata = self._create_metadata(project_data)
            
            # 4. 문서 ID 생성 (익명 식별자 기반)
            anonymous_id = getattr(project_data, 'anonymous_id', None)
            if not anonymous_id:
                import uuid
                anonymous_id = f"ANON_{uuid.uuid4().hex[:8].upper()}"
                project_data.anonymous_id = anonymous_id
            
            document_id = f"project_{anonymous_id}_{uuid.uuid4().hex[:8]}"
            
            # 5. ChromaDB에 저장
            storage_result = await self._store_in_chromadb(
                document_id=document_id,
                content=document_content,
                embedding=embedding,
                metadata=metadata
            )
            
            return {
                "document_id": document_id,
                "embedding_success": True,
                "stored_in_vectordb": storage_result["success"],
                "storage_message": storage_result["message"]
            }
            
        except Exception as e:
            print(f"프로젝트 처리 실패: {str(e)}")
            return {
                "document_id": "",
                "embedding_success": False,
                "stored_in_vectordb": False,
                "error": str(e)
            }
    
    def _format_project_as_document(self, project_data) -> str:
        """
        프로젝트 데이터를 문서 형태로 포맷팅
        기존 career_history 형식과 유사하게 구성
        개인정보 보호를 위한 익명화 적용
        """
        content_parts = []
        
        # 익명 식별자 생성 (없는 경우)
        anonymous_id = getattr(project_data, 'anonymous_id', None)
        if not anonymous_id:
            import uuid
            anonymous_id = f"ANON_{uuid.uuid4().hex[:8].upper()}"
            project_data.anonymous_id = anonymous_id
        
        # 기본 정보 (개인정보 제외)
        content_parts.append(f"■ 익명 식별자: {anonymous_id}")
        content_parts.append(f"■ 프로젝트명: {project_data.project_name}")
        
        # 프로젝트 기간 정보
        if hasattr(project_data, 'start_year') and project_data.start_year:
            if hasattr(project_data, 'end_year') and project_data.end_year:
                content_parts.append(f"■ 프로젝트 기간: {project_data.start_year}년 ~ {project_data.end_year}년")
                duration = project_data.end_year - project_data.start_year + 1
                content_parts.append(f"■ 총 기간: {duration}년")
            else:
                content_parts.append(f"■ 시작 연도: {project_data.start_year}년")
        
        # 도메인 및 역할
        content_parts.append(f"■ 도메인: {project_data.domain}")
        content_parts.append(f"■ 수행 역할: {project_data.role}")
        
        # 프로젝트 규모
        if hasattr(project_data, 'scale') and project_data.scale:
            content_parts.append(f"■ 프로젝트 규모: {project_data.scale}")
        
        content_parts.append("")  # 빈 줄
        
        # 상세 경력 정보
        content_parts.append("=== 프로젝트 상세 정보 ===")
        content_parts.append("")
        
        # 활용 기술/스킬
        if hasattr(project_data, 'skills') and project_data.skills:
            content_parts.append(f" 활용 기술:")
            content_parts.append(f"  {', '.join(project_data.skills)}")
            content_parts.append("")
        
        # 기존 career_history와 동일한 스타일로 마무리
        content_parts.append("=== 경력 요약 ===")
        content_parts.append(f"• 프로젝트: {project_data.project_name}")
        content_parts.append(f"• 도메인: {project_data.domain}")
        content_parts.append(f"• 역할: {project_data.role}")
        
        if hasattr(project_data, 'skills') and project_data.skills:
            content_parts.append(f"• 핵심 기술: {', '.join(project_data.skills[:5])}")
        
        return "\n".join(content_parts)
    
    async def _create_embedding(self, content: str) -> List[float]:
        """텍스트 콘텐츠의 임베딩 생성"""
        try:
            embedding = self.embeddings.embed_query(content)
            return embedding
        except Exception as e:
            print(f"임베딩 생성 실패: {str(e)}")
            raise
    
    def _create_metadata(self, project_data) -> Dict[str, Any]:
        """
        프로젝트 데이터에서 메타데이터 생성
        기존 career_history 메타데이터 구조와 호환
        개인정보 보호를 위한 익명화 적용
        """
        # 익명 식별자 확인/생성
        anonymous_id = getattr(project_data, 'anonymous_id', None)
        if not anonymous_id:
            import uuid
            anonymous_id = f"ANON_{uuid.uuid4().hex[:8].upper()}"
            project_data.anonymous_id = anonymous_id
        
        metadata = {
            # 기본 식별 정보 (익명화)
            'anonymous_id': anonymous_id,
            'source_type': 'project_api',
            'data_source': 'spring_boot_api',
            
            # 프로젝트 정보
            'project_name': project_data.project_name,
            'primary_domain': project_data.domain,
            'current_position': project_data.role,
            
            # 시간 정보
            'processing_timestamp': datetime.now().isoformat(),
            'processing_method': 'api_real_time_embedding',
        }
        
        # 연도 정보
        if hasattr(project_data, 'start_year') and project_data.start_year:
            metadata['activity_start_year'] = project_data.start_year
            
        if hasattr(project_data, 'end_year') and project_data.end_year:
            metadata['activity_end_year'] = project_data.end_year
        
        if (hasattr(project_data, 'start_year') and project_data.start_year and 
            hasattr(project_data, 'end_year') and project_data.end_year):
            metadata['total_activity_years'] = project_data.end_year - project_data.start_year + 1
            metadata['activity_years_list'] = list(range(project_data.start_year, project_data.end_year + 1))
        
        # 스킬 정보
        if hasattr(project_data, 'skills') and project_data.skills:
            metadata['skill_names'] = project_data.skills[:10]
            metadata['total_skill_count'] = len(project_data.skills)
            metadata['skill_diversity_score'] = min(len(set(project_data.skills)), 5)
        else:
            metadata['skill_names'] = []
            metadata['total_skill_count'] = 0
            metadata['skill_diversity_score'] = 0
        
        # 프로젝트 규모
        if hasattr(project_data, 'scale') and project_data.scale:
            metadata['project_scale'] = project_data.scale
            metadata['has_large_projects'] = '대형' in project_data.scale or '대규모' in project_data.scale
        else:
            metadata['project_scale'] = '정보없음'
            metadata['has_large_projects'] = False
        
        # 개인정보 보호를 위해 기본값으로 설정
        metadata['critical_career_points'] = 0
        
        # 경력 품질 점수 계산 (실제 데이터만 기반)
        quality_score = 50.0  # 기본 점수
        
        # 스킬 다양성 점수
        if hasattr(project_data, 'skills') and project_data.skills:
            quality_score += min(len(project_data.skills) * 5, 20)
        
        # 프로젝트 기간 점수
        if (hasattr(project_data, 'start_year') and project_data.start_year and 
            hasattr(project_data, 'end_year') and project_data.end_year):
            duration = project_data.end_year - project_data.start_year + 1
            quality_score += min(duration * 5, 15)
        
        # 프로젝트 규모 점수
        if hasattr(project_data, 'scale') and project_data.scale:
            if '대형' in project_data.scale or '대규모' in project_data.scale:
                quality_score += 10
            elif '중형' in project_data.scale or '중규모' in project_data.scale:
                quality_score += 5
        
        metadata['career_quality_score'] = min(quality_score, 100.0)
        
        return metadata
    
    async def _store_in_chromadb(self, document_id: str, content: str, 
                               embedding: List[float], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """ChromaDB에 임베딩 데이터 저장"""
        if not self.collection_id:
            return {
                "success": False,
                "message": "ChromaDB 컬렉션 ID를 찾을 수 없습니다"
            }
        
        try:
            # ChromaDB v2 Multi-tenant API 형식에 맞춰 데이터 준비
            store_data = {
                "ids": [document_id],
                "embeddings": [embedding],
                "documents": [content],
                "metadatas": [metadata]
            }
            
            # API 호출
            upload_url = f"{self.collections_url}/{self.collection_id}/add"
            response = requests.post(
                upload_url,
                headers=self.headers,
                json=store_data,
                timeout=60
            )
            
            if response.status_code in [200, 201]:
                print(f" [ProjectEmbeddingService] ChromaDB 저장 성공: {document_id}")
                return {
                    "success": True,
                    "message": "ChromaDB에 성공적으로 저장됨"
                }
            else:
                print(f"- [ProjectEmbeddingService] ChromaDB 저장 실패: {response.status_code}")
                print(f"응답: {response.text}")
                return {
                    "success": False,
                    "message": f"ChromaDB 저장 실패: HTTP {response.status_code}"
                }
                
        except Exception as e:
            print(f"- [ProjectEmbeddingService] ChromaDB 저장 중 오류: {str(e)}")
            return {
                "success": False,
                "message": f"ChromaDB 저장 오류: {str(e)}"
            }
    
    async def remove_project_embedding(self, document_id: str) -> Dict[str, Any]:
        """ChromaDB에서 프로젝트 임베딩 삭제"""
        if not self.collection_id:
            return {
                "success": False,
                "message": "ChromaDB 컬렉션 ID를 찾을 수 없습니다"
            }
        
        try:
            # ChromaDB에서 문서 삭제
            delete_data = {
                "ids": [document_id]
            }
            
            delete_url = f"{self.collections_url}/{self.collection_id}/delete"
            response = requests.post(
                delete_url,
                headers=self.headers,
                json=delete_data,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                print(f" [ProjectEmbeddingService] 문서 삭제 성공: {document_id}")
                return {
                    "success": True,
                    "message": "문서가 성공적으로 삭제됨"
                }
            else:
                print(f"- [ProjectEmbeddingService] 문서 삭제 실패: {response.status_code}")
                print(f"응답: {response.text}")
                return {
                    "success": False,
                    "message": f"문서 삭제 실패: HTTP {response.status_code}"
                }
                
        except Exception as e:
            print(f"- [ProjectEmbeddingService] 문서 삭제 중 오류: {str(e)}")
            return {
                "success": False,
                "message": f"문서 삭제 오류: {str(e)}"
            }
    
    async def update_project_embedding(self, document_id: str, project_data) -> Dict[str, Any]:
        """기존 프로젝트 임베딩 업데이트"""
        try:
            # 기존 문서 삭제
            delete_result = await self.remove_project_embedding(document_id)
            
            if not delete_result["success"]:
                print(f" [ProjectEmbeddingService] 기존 문서 삭제 실패, 새로 추가 진행: {delete_result['message']}")
            
            # 새로운 임베딩으로 저장
            store_result = await self.process_and_store_project(project_data)
            
            return {
                "success": store_result["stored_in_vectordb"],
                "old_document_deleted": delete_result["success"],
                "new_document_id": store_result["document_id"],
                "message": "프로젝트 임베딩이 업데이트되었습니다"
            }
            
        except Exception as e:
            print(f"- [ProjectEmbeddingService] 프로젝트 업데이트 중 오류: {str(e)}")
            return {
                "success": False,
                "message": f"프로젝트 업데이트 오류: {str(e)}"
            }
    
    def get_collection_status(self) -> Dict[str, Any]:
        """컬렉션 상태 정보 반환"""
        return {
            "collection_name": self.collection_name,
            "collection_id": self.collection_id,
            "is_connected": self.collection_id is not None,
            "base_url": self.base_url,
            "tenant": self.tenant,
            "database": self.database
        }