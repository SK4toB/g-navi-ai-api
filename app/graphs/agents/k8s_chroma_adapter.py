# app/graphs/agents/k8s_chroma_adapter.py
import requests
import os
from typing import List, Dict, Any, Optional
from langchain.schema import Document, BaseRetriever
from langchain.embeddings.base import Embeddings
from langchain_openai import OpenAIEmbeddings
from pydantic import Field, ConfigDict

class K8sChromaRetriever(BaseRetriever):
    """
    K8s 환경에서 외부 ChromaDB v2 Multi-tenant API를 사용하는 통합 리트리버
    (컬렉션 관리, 임베딩, 검색 등 모든 기능 포함)
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, extra='allow')

    collection_name: str = Field(description="컬렉션 이름")
    embeddings: Embeddings = Field(description="임베딩 인스턴스")
    k: int = Field(default=3, description="검색할 문서 수")
    
    # 추가된 필드들을 Pydantic 필드로 정의
    base_url: str = Field(default="http://chromadb-1.sk-team-04.svc.cluster.local:8000/api/v2", description="ChromaDB 기본 URL")
    tenant: str = Field(default="default_tenant", description="ChromaDB 테넌트")
    database: str = Field(default="default_database", description="ChromaDB 데이터베이스")
    pod_collection_name: Optional[str] = Field(default=None, description="실제 Pod 컬렉션명")
    collection_id: Optional[str] = Field(default=None, description="컬렉션 ID")
    headers: Dict[str, str] = Field(default_factory=lambda: {"Content-Type": "application/json"}, description="HTTP 헤더")
    collection_mapping: Dict[str, str] = Field(
        default_factory=lambda: {
            "career_history": "gnavi4_career_history_prod",
            "education_courses": "gnavi4_education_prod",
            "news_data":"gnavi4_news_prod",
        },
        description="컬렉션명 매핑"
    )

    def __init__(self, collection_name: str, embeddings: Embeddings, k: int = 3, **kwargs):
        # pod_collection_name 계산 (collection_mapping 사용)
        pod_collection_name = {
            "career_history": "gnavi4_career_history_prod",
            "education_courses": "gnavi4_education_prod",
            "news_data":"gnavi4_news_prod"
        }.get(collection_name, collection_name)
        
        # 먼저 Pydantic 초기화 (모든 필드를 명시적으로 전달)
        super().__init__(
            collection_name=collection_name,
            embeddings=embeddings,
            k=k,
            pod_collection_name=pod_collection_name,
            **kwargs
        )
        
        # 컬렉션 ID 조회
        self._get_collection_id()

    def _get_collection_id(self):
        """컬렉션 ID를 조회하여 설정"""
        try:
            response = requests.get(self.collections_url, headers=self.headers, timeout=30)
            if response.status_code == 200:
                collections = response.json()
                for collection in collections:
                    if collection.get('name') == self.pod_collection_name:
                        # Pydantic 모델의 필드 업데이트 방법
                        object.__setattr__(self, 'collection_id', collection.get('id'))
                        print(f"✅ [K8sChromaRetriever] 컬렉션 연결: {self.pod_collection_name} (ID: {self.collection_id})")
                        return
                print(f"❌ [K8sChromaRetriever] 컬렉션을 찾을 수 없습니다: {self.pod_collection_name}")
            else:
                print(f"❌ [K8sChromaRetriever] 컬렉션 목록 조회 실패: {response.status_code}")
        except Exception as e:
            print(f"❌ [K8sChromaRetriever] 컬렉션 ID 조회 실패: {e}")

    @property
    def collections_url(self) -> str:
        """컬렉션 URL을 동적으로 계산"""
        return f"{self.base_url}/tenants/{self.tenant}/databases/{self.database}/collections"

    def similarity_search(self, query: str, k: int = None) -> List[Document]:
        """유사도 검색 수행"""
        if not self.collection_id:
            print(f"❌ [K8sChromaRetriever] 컬렉션 ID가 없어서 검색할 수 없습니다")
            return []
        
        try:
            query_embedding = self.embeddings.embed_query(query)
            search_data = {
                "query_embeddings": [query_embedding],
                "n_results": k or self.k,
                "include": ["documents", "metadatas"]
            }
            
            search_url = f"{self.collections_url}/{self.collection_id}/query"
            response = requests.post(search_url, headers=self.headers, json=search_data, timeout=30)
            
            if response.status_code == 200:
                results = response.json()
                documents = results.get('documents', [[]])
                metadatas = results.get('metadatas', [[]])
                docs = []
                
                if documents and len(documents) > 0:
                    for i, doc_text in enumerate(documents[0]):
                        metadata = metadatas[0][i] if metadatas and len(metadatas[0]) > i else {}
                        docs.append(Document(page_content=doc_text, metadata=metadata))
                
                print(f"✅ [K8sChromaRetriever] 검색 완료: {len(docs)}개 문서 반환")
                return docs
            else:
                print(f"❌ [K8sChromaRetriever] 검색 실패: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            print(f"❌ [K8sChromaRetriever] 검색 중 예외: {e}")
            return []

    def get_collection_info(self) -> Dict:
        """컬렉션 정보 조회"""
        if not self.collection_id:
            return {"status": "error", "message": "컬렉션 ID 없음"}
        
        try:
            count_url = f"{self.collections_url}/{self.collection_id}/count"
            count_response = requests.get(count_url, headers=self.headers, timeout=30)
            
            if count_response.status_code == 200:
                doc_count = count_response.json()
                return {
                    "status": "success",
                    "collection_name": self.pod_collection_name,
                    "collection_id": self.collection_id,
                    "document_count": doc_count
                }
            else:
                return {"status": "error", "message": f"카운트 조회 실패: {count_response.status_code}"}
                
        except Exception as e:
            return {"status": "error", "message": f"예외 발생: {e}"}

    def get_relevant_documents(self, query: str, *, run_manager=None) -> List[Document]:
        """BaseRetriever 인터페이스 구현"""
        return self.similarity_search(query, k=self.k)

    async def _aget_relevant_documents(self, query: str) -> List[Document]:
        """비동기 검색 (미구현)"""
        raise NotImplementedError("Async retrieval not implemented yet")