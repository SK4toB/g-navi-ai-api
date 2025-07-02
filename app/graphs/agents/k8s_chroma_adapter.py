# app/graphs/agents/k8s_chroma_adapter.py
import requests
import os
from typing import List, Dict, Any
from langchain.schema import Document
from langchain_openai import OpenAIEmbeddings
from langchain.schema.runnable import Runnable  # Import Runnable interface

class K8sChromaDBAdapter:
    """
    K8s 환경에서 외부 ChromaDB v2 Multi-tenant API를 사용하는 어댑터
    로컬 Chroma vectorstore와 동일한 인터페이스 제공
    """
    
    def __init__(self, collection_name: str, embeddings: OpenAIEmbeddings):
        """
        K8s ChromaDB 어댑터 초기화
        
        Args:
            collection_name: 사용할 컬렉션 이름 (career_history 또는 education_courses)
            embeddings: OpenAI 임베딩 인스턴스
        """
        self.embeddings = embeddings
        self.collection_name = collection_name
        
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
        
        # 실제 사용할 Pod 컬렉션명
        self.pod_collection_name = self.collection_mapping.get(collection_name, collection_name)
        self.collection_id = None
        
        # 헤더 설정
        self.headers = {"Content-Type": "application/json"}
        
        # 컬렉션 ID 조회
        self._get_collection_id()
    
    def _get_collection_id(self):
        """컬렉션 ID 조회"""
        try:
            response = requests.get(self.collections_url, headers=self.headers, timeout=30)
            if response.status_code == 200:
                collections = response.json()
                for collection in collections:
                    if collection.get('name') == self.pod_collection_name:
                        self.collection_id = collection.get('id')
                        print(f"✅ [K8sChromaDB] 컬렉션 연결: {self.pod_collection_name} (ID: {self.collection_id})")
                        return
                print(f"❌ [K8sChromaDB] 컬렉션을 찾을 수 없습니다: {self.pod_collection_name}")
            else:
                print(f"❌ [K8sChromaDB] 컬렉션 목록 조회 실패: {response.status_code}")
        except Exception as e:
            print(f"❌ [K8sChromaDB] 컬렉션 ID 조회 실패: {e}")
    
    def similarity_search(self, query: str, k: int = 3) -> List[Document]:
        """
        유사도 검색 (로컬 Chroma와 동일한 인터페이스)
        
        Args:
            query: 검색 쿼리
            k: 반환할 문서 수
            
        Returns:
            Document 리스트
        """
        if not self.collection_id:
            print(f"❌ [K8sChromaDB] 컬렉션 ID가 없어서 검색할 수 없습니다")
            return []
        
        try:
            # 쿼리를 임베딩으로 변환
            query_embedding = self.embeddings.embed_query(query)
            
            # 검색 요청 데이터
            search_data = {
                "query_embeddings": [query_embedding],
                "n_results": k,
                "include": ["documents", "metadatas"]
            }
            
            # API 호출
            search_url = f"{self.collections_url}/{self.collection_id}/query"
            response = requests.post(search_url, headers=self.headers, json=search_data, timeout=30)
            
            if response.status_code == 200:
                results = response.json()
                documents = results.get('documents', [[]])
                metadatas = results.get('metadatas', [[]])
                
                # Document 객체로 변환
                docs = []
                if documents and len(documents) > 0:
                    for i, doc_text in enumerate(documents[0]):
                        metadata = metadatas[0][i] if metadatas and len(metadatas[0]) > i else {}
                        docs.append(Document(page_content=doc_text, metadata=metadata))
                
                print(f"✅ [K8sChromaDB] 검색 완료: {len(docs)}개 문서 반환")
                return docs
            else:
                print(f"❌ [K8sChromaDB] 검색 실패: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            print(f"❌ [K8sChromaDB] 검색 중 예외: {e}")
            return []
    
    def as_retriever(self, search_type: str = "similarity", search_kwargs: Dict = None):
        """
        리트리버 객체 반환 (로컬 Chroma와 동일한 인터페이스)
        
        Args:
            search_type: 검색 타입 (기본값: "similarity")
            search_kwargs: 검색 파라미터 (k 값 등)
            
        Returns:
            K8sChromaRetriever 인스턴스
        """
        search_kwargs = search_kwargs or {}
        return K8sChromaRetriever(self, search_kwargs.get('k', 3))
    
    def get_collection_info(self) -> Dict:
        """컬렉션 정보 조회"""
        if not self.collection_id:
            return {"status": "error", "message": "컬렉션 ID 없음"}
        
        try:
            # 문서 개수 조회
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


class K8sChromaRetriever(Runnable):  # Inherit from Runnable
    """
    K8s ChromaDB 리트리버 (로컬 Chroma retriever와 동일한 인터페이스)
    """
    
    def __init__(self, adapter: K8sChromaDBAdapter, k: int = 3):
        self.adapter = adapter
        self.k = k
    
    def invoke(self, query: str) -> List[Document]:
        """
        검색 실행 (LangChain retriever와 동일한 인터페이스)
        
        Args:
            query: 검색 쿼리
            
        Returns:
            Document 리스트
        """
        return self.adapter.similarity_search(query, k=self.k)
    
    def get_relevant_documents(self, query: str) -> List[Document]:
        """
        관련 문서 검색 (LangChain retriever와 동일한 인터페이스)
        
        Args:
            query: 검색 쿼리
            
        Returns:
            Document 리스트
        """
        return self.invoke(query)