# retriever.py

import os
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from langchain.embeddings import CacheBackedEmbeddings
from langchain.storage import LocalFileStore
import logging
import json
from langchain.schema import Document

from dotenv import load_dotenv
load_dotenv()

class CareerEnsembleRetrieverAgent:
    """career_data Chroma DB에 대해 BM25+LLM 임베딩 앙상블 리트리버만 제공"""
    def __init__(self, persist_directory: str = os.path.join(
            os.path.dirname(__file__), 
            "../../storage/vector_stores/career_data"
        ), cache_directory: str = os.path.join(
            os.path.dirname(__file__), 
            "../../storage/cache/embedding_cache"
        )):

        self.persist_directory = os.path.abspath(persist_directory)
        self.cache_directory = os.path.abspath(cache_directory)
        self.logger = logging.getLogger(__name__)
        os.makedirs(self.persist_directory, exist_ok=True)
        os.makedirs(self.cache_directory, exist_ok=True)

        self.base_embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            dimensions=1536
        )
        self.cached_embeddings = CacheBackedEmbeddings.from_bytes_store(
            self.base_embeddings,
            LocalFileStore(cache_directory),
            namespace="career_embeddings"
        )
        self.vectorstore = None
        self.ensemble_retriever = None
        self._load_vectorstore_and_retriever()

    def _load_vectorstore_and_retriever(self):
        # Chroma 벡터스토어 로드
        self.vectorstore = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.cached_embeddings,
            collection_name="career_history"
        )
        # LLM 임베딩 리트리버
        embedding_retriever = self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 5}
        )
        # BM25용 docs 로드 (storage/docs/career_docs.json)
        docs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../storage/docs/career_history.json'))
        all_docs = []
        try:
            with open(docs_path, 'r', encoding='utf-8') as f:
                json_docs = json.load(f)
                all_docs = [Document(page_content=doc['page_content'], metadata=doc['metadata']) for doc in json_docs]
            self.logger.info(f"BM25용 career_docs.json 로드 완료 (문서 수: {len(all_docs)})")
        except Exception as e:
            self.logger.warning(f"BM25용 career_docs.json 로드 실패: {e}")
        retrievers = [embedding_retriever]
        weights = [1.0]
        if all_docs:
            bm25_retriever = BM25Retriever.from_documents(all_docs)
            bm25_retriever.k = 5
            retrievers.append(bm25_retriever)
            weights = [0.5, 0.5]
        self.ensemble_retriever = EnsembleRetriever(
            retrievers=retrievers,
            weights=weights
        )
        self.logger.info(f"Career 앙상블 리트리버 준비 완료 (문서 수: {len(all_docs)})")

    def retrieve(self, query: str, k: int = 5):
        """앙상블 리트리버로 검색"""
        return self.ensemble_retriever.get_relevant_documents(query) if self.ensemble_retriever else []

    def load_chat_history(self, user_id: str = None, chat_history_path: str = "app/data/json/chat_history.json"):
        """chat_history.json 파일을 불러와 사용자 ID별로 필터링하여 반환"""
        try:
            with open(chat_history_path, "r", encoding="utf-8") as f:
                all_chat_history = json.load(f)
            
            # 사용자 ID가 제공된 경우 해당 사용자의 대화내역만 필터링
            if user_id:
                user_chat_history = [
                    session for session in all_chat_history 
                    if session.get("user_id") == user_id
                ]
                self.logger.info(f"사용자 {user_id}의 chat_history 로드 완료 (세션 수: {len(user_chat_history)})")
                return user_chat_history
            else:
                # 사용자 ID가 없으면 전체 반환 (하위 호환성)
                self.logger.info(f"전체 chat_history 로드 완료 (세션 수: {len(all_chat_history)})")
                return all_chat_history
                
        except Exception as e:
            self.logger.error(f"chat_history.json 로드 실패: {e}")
            return []

    def search_external_trends_with_tavily(self, trend_keywords: list) -> list:
        """Tavily API를 이용한 트렌드 검색 (간단 버전)"""
        import requests
        import os
        tavily_api_key = os.getenv("TAVILY_API_KEY")
        if not tavily_api_key:
            self.logger.warning("Tavily API Key가 설정되어 있지 않습니다.")
            return []
        results = []
        for keyword in trend_keywords[:2]:  # 상위 2개 키워드만
            try:
                response = requests.post(
                    "https://api.tavily.com/search",
                    json={"query": keyword, "num_results": 2},
                    headers={"Authorization": f"Bearer {tavily_api_key}"}
                )
                if response.status_code == 200:
                    data = response.json()
                    for item in data.get("results", []):
                        results.append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "snippet": item.get("snippet", "")
                        })
                else:
                    self.logger.warning(f"Tavily 검색 실패: {response.status_code} {response.text}")
            except Exception as e:
                self.logger.error(f"Tavily 검색 중 오류: {e}")
        return results
