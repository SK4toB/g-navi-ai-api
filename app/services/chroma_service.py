# app/services/chroma_service.py
"""
* @className : ChromaService
* @description : ChromaDB 서비스 모듈
*                벡터 데이터베이스 관리를 담당하는 서비스입니다.
*                대화 내역을 벡터화하여 저장하고 검색 기능을 제공합니다.
*
* @modification : 2025.07.01(이재원) 최초생성
*
* @author 이재원
* @Date 2025.07.01
* @version 1.0
* @see ChromaDB, VectorStore
*  == 개정이력(Modification Information) ==
*  
*   수정일        수정자        수정내용
*   ----------   --------     ---------------------------
*   2025.07.01   이재원       최초 생성
*  
* Copyright (C) by G-Navi AI System All right reserved.
"""

import requests
from typing import Dict, Any, List, Optional
from langchain_openai import OpenAIEmbeddings

from app.config.settings import settings


class ChromaService:
    """
    ChromaDB v2 Multi-tenant 연동 서비스
    - v2 Multi-tenant API 구조 사용
    - 컬렉션 ID 기반 작업
    """
    
    def __init__(self):
        # ChromaDB v2 Multi-tenant 설정
        self.base_url = "https://sk-gnavi4.skala25a.project.skala-ai.com/vector/api/v2"
        self.tenant = "default_tenant"
        self.database = "default_database"
        self.collections_url = f"{self.base_url}/tenants/{self.tenant}/databases/{self.database}/collections"
        
        # 컬렉션 정보 (운영용)
        self.career_collection_name = "gnavi4_career_history_prod"
        self.education_collection_name = "gnavi4_education_prod"
        self.career_collection_id = None
        self.education_collection_id = None
        
        # 임베딩 설정
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            dimensions=1536
        )
        
        # 헤더 설정 (v2에서는 인증 불필요)
        self.headers = {"Content-Type": "application/json"}
        self.available = False
        
        # 초기화
        self._init_client()
        print("ChromaService v2 Multi-tenant 초기화 완료")
    
    def _init_client(self):
        """ChromaDB v2 연결 설정 초기화"""
        try:
            print(f"ChromaDB v2 Multi-tenant 접속 시도: {self.collections_url}")
            
            # 연결 테스트
            heartbeat_result = self._test_heartbeat()
            if heartbeat_result:
                print(f"ChromaDB 연결 성공: {heartbeat_result}")
                self.available = True
                
                # 컬렉션 ID 조회
                self._load_collection_ids()
            else:
                print("ChromaDB heartbeat 실패")
                self.available = False
            
        except Exception as e:
            print(f"ChromaDB 연결 실패: {e}")
            self.available = False
    
    def _test_heartbeat(self) -> Optional[Dict]:
        """Heartbeat 테스트"""
        try:
            response = requests.get(
                f"{self.base_url}/heartbeat", 
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Heartbeat 실패: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Heartbeat 오류: {e}")
            return None
    
    def _load_collection_ids(self):
        """컬렉션 ID들을 조회하여 저장"""
        try:
            collections = self._get_collections_list()
            if collections:
                for collection in collections:
                    name = collection.get('name')
                    collection_id = collection.get('id')
                    
                    if name == self.career_collection_name:
                        self.career_collection_id = collection_id
                        print(f"경력 컬렉션 ID 로드: {collection_id}")
                    elif name == self.education_collection_name:
                        self.education_collection_id = collection_id
                        print(f"교육과정 컬렉션 ID 로드: {collection_id}")
                        
        except Exception as e:
            print(f"컬렉션 ID 로드 실패: {e}")
    
    def _get_collections_list(self) -> Optional[List[Dict]]:
        """컬렉션 목록 조회"""
        try:
            response = requests.get(
                self.collections_url,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"컬렉션 목록 조회 실패: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"컬렉션 목록 조회 오류: {e}")
            return None
    
    def is_available(self) -> bool:
        """ChromaDB 사용 가능 여부"""
        return self.available
    
    def test_connection(self) -> Dict[str, Any]:
        """연결 테스트"""
        try:
            if not self.collections_url:
                return {
                    "status": "failed",
                    "error": "클라이언트가 초기화되지 않았습니다",
                    "available": False
                }
            
            # Heartbeat 테스트
            heartbeat = self._test_heartbeat()
            
            if heartbeat:
                # 컬렉션 목록도 조회해서 상태 확인
                collections = self._get_collections_list()
                
                return {
                    "status": "success",
                    "heartbeat": heartbeat,
                    "available": True,
                    "base_url": self.base_url,
                    "collections_url": self.collections_url,
                    "collections_count": len(collections) if collections else 0,
                    "career_collection_available": bool(self.career_collection_id),
                    "education_collection_available": bool(self.education_collection_id)
                }
            else:
                return {
                    "status": "failed",
                    "error": "heartbeat 실패",
                    "available": False,
                    "base_url": self.base_url
                }
            
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "available": False
            }
    
    def get_basic_info(self) -> Dict[str, Any]:
        """기본 정보 조회"""
        return {
            "available": self.is_available(),
            "career_collection_name": self.career_collection_name,
            "education_collection_name": self.education_collection_name,
            "career_collection_id": self.career_collection_id,
            "education_collection_id": self.education_collection_id,
            "api_version": "v2_multi_tenant",
            "base_url": self.base_url,
            "collections_url": self.collections_url,
            "auth_configured": False  # v2에서는 인증 불필요
        }
    
    def list_collections(self) -> Dict[str, Any]:
        """컬렉션 목록 조회"""
        try:
            if not self.is_available():
                return {"error": "ChromaDB 사용 불가"}
            
            collections = self._get_collections_list()
            
            if collections is not None:
                return {
                    "status": "success",
                    "collections": collections,
                    "count": len(collections)
                }
            else:
                return {
                    "status": "failed",
                    "error": "컬렉션 목록 조회 실패"
                }
                
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def get_collection_info(self, collection_type: str = "career") -> Dict[str, Any]:
        """컬렉션 정보 조회"""
        try:
            if not self.is_available():
                return {"error": "ChromaDB 사용 불가"}
            
            # 컬렉션 ID 선택
            if collection_type == "career":
                collection_id = self.career_collection_id
                collection_name = self.career_collection_name
            elif collection_type == "education":
                collection_id = self.education_collection_id
                collection_name = self.education_collection_name
            else:
                return {"error": f"지원하지 않는 컬렉션 타입: {collection_type}"}
            
            if not collection_id:
                return {"error": f"{collection_type} 컬렉션을 찾을 수 없습니다"}
            
            # 문서 개수 조회
            count_url = f"{self.collections_url}/{collection_id}/count"
            count_response = requests.get(count_url, headers=self.headers, timeout=10)
            
            if count_response.status_code == 200:
                doc_count = count_response.json()
                return {
                    "status": "success",
                    "collection_name": collection_name,
                    "collection_id": collection_id,
                    "document_count": doc_count,
                    "collection_type": collection_type
                }
            else:
                return {
                    "status": "failed",
                    "error": f"문서 개수 조회 실패: {count_response.status_code}"
                }
                
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def search_documents(self, query: str, collection_type: str = "career", n_results: int = 5) -> Dict[str, Any]:
        """문서 검색"""
        try:
            if not self.is_available():
                return {"error": "ChromaDB 사용 불가"}
            
            # 컬렉션 ID 선택
            if collection_type == "career":
                collection_id = self.career_collection_id
            elif collection_type == "education":
                collection_id = self.education_collection_id
            else:
                return {"error": f"지원하지 않는 컬렉션 타입: {collection_type}"}
            
            if not collection_id:
                return {"error": f"{collection_type} 컬렉션을 찾을 수 없습니다"}
            
            # 임베딩 생성
            query_embedding = self.embeddings.embed_query(query)
            
            # 검색 요청
            search_data = {
                "query_embeddings": [query_embedding],
                "n_results": n_results,
                "include": ["documents", "metadatas"]
            }
            
            search_url = f"{self.collections_url}/{collection_id}/query"
            response = requests.post(search_url, headers=self.headers, json=search_data, timeout=30)
            
            if response.status_code == 200:
                results = response.json()
                documents = results.get('documents', [[]])
                metadatas = results.get('metadatas', [[]])
                
                result_count = len(documents[0]) if documents and len(documents) > 0 else 0
                
                # 결과 정리
                formatted_results = []
                for i in range(result_count):
                    doc = documents[0][i] if documents[0] else ""
                    meta = metadatas[0][i] if metadatas and metadatas[0] else {}
                    
                    formatted_results.append({
                        "document": doc,
                        "metadata": meta,
                        "rank": i + 1
                    })
                
                return {
                    "status": "success",
                    "query": query,
                    "collection_type": collection_type,
                    "results": formatted_results,
                    "result_count": result_count
                }
            else:
                return {
                    "status": "failed",
                    "error": f"검색 실패: {response.status_code} - {response.text}"
                }
                
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def get_sample_documents(self, collection_type: str = "career", limit: int = 3) -> Dict[str, Any]:
        """샘플 문서 조회"""
        try:
            if not self.is_available():
                return {"error": "ChromaDB 사용 불가"}
            
            # 컬렉션 ID 선택
            if collection_type == "career":
                collection_id = self.career_collection_id
            elif collection_type == "education":
                collection_id = self.education_collection_id
            else:
                return {"error": f"지원하지 않는 컬렉션 타입: {collection_type}"}
            
            if not collection_id:
                return {"error": f"{collection_type} 컬렉션을 찾을 수 없습니다"}
            
            # 문서 조회
            get_data = {
                "limit": limit,
                "include": ["documents", "metadatas"]
            }
            
            get_url = f"{self.collections_url}/{collection_id}/get"
            response = requests.post(get_url, headers=self.headers, json=get_data, timeout=30)
            
            if response.status_code == 200:
                results = response.json()
                documents = results.get('documents', [])
                metadatas = results.get('metadatas', [])
                
                # 결과 정리
                formatted_results = []
                for i, doc in enumerate(documents[:limit]):
                    meta = metadatas[i] if i < len(metadatas) else {}
                    formatted_results.append({
                        "document": doc,
                        "metadata": meta,
                        "index": i + 1
                    })
                
                return {
                    "status": "success",
                    "collection_type": collection_type,
                    "sample_documents": formatted_results,
                    "count": len(formatted_results)
                }
            else:
                return {
                    "status": "failed",
                    "error": f"문서 조회 실패: {response.status_code} - {response.text}"
                }
                
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }