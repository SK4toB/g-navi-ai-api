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
    model_config = ConfigDict(arbitrary_types_allowed=True)

    collection_name: str = Field(description="컬렉션 이름")
    embeddings: Embeddings = Field(description="임베딩 인스턴스")
    k: int = Field(default=3, description="검색할 문서 수")
    pod_collection_name: str = Field(default=None, description="실제 Pod 컬렉션명")
    collection_id: Optional[str] = Field(default=None, description="컬렉션 ID")

    def __init__(self, collection_name: str, embeddings: Embeddings, k: int = 3, **kwargs):
        super().__init__(
            collection_name=collection_name,
            embeddings=embeddings,
            k=k,
            **kwargs
        )
        self.collection_name = collection_name
        self.embeddings = embeddings
        self.k = k

        # K8s 내부 통신 URL
        self.base_url = "http://chromadb-1.sk-team-04.svc.cluster.local:8000/api/v2"
        self.tenant = "default_tenant"
        self.database = "default_database"
        self.collections_url = f"{self.base_url}/tenants/{self.tenant}/databases/{self.database}/collections"

        # 컬렉션명 매핑 (로컬 → Pod)
        self.collection_mapping = {
            "career_history": "gnavi4_career_history_prod",
            "education_courses": "gnavi4_education_prod"
        }
        self.pod_collection_name = self.collection_mapping.get(collection_name, collection_name)
        self.collection_id = None
        self.headers = {"Content-Type": "application/json"}
        self._get_collection_id()

    def _get_collection_id(self):
        try:
            response = requests.get(self.collections_url, headers=self.headers, timeout=30)
            if response.status_code == 200:
                collections = response.json()
                for collection in collections:
                    if collection.get('name') == self.pod_collection_name:
                        self.collection_id = collection.get('id')
                        print(f"✅ [K8sChromaRetriever] 컬렉션 연결: {self.pod_collection_name} (ID: {self.collection_id})")
                        return
                print(f"❌ [K8sChromaRetriever] 컬렉션을 찾을 수 없습니다: {self.pod_collection_name}")
            else:
                print(f"❌ [K8sChromaRetriever] 컬렉션 목록 조회 실패: {response.status_code}")
        except Exception as e:
            print(f"❌ [K8sChromaRetriever] 컬렉션 ID 조회 실패: {e}")

    def similarity_search(self, query: str, k: int = None) -> List[Document]:
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
        return self.similarity_search(query, k=self.k)

    async def _aget_relevant_documents(self, query: str) -> List[Document]:
        raise NotImplementedError("Async retrieval not implemented yet")