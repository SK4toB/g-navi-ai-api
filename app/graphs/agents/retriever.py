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
from datetime import datetime, timedelta
import re

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
        # LLM 임베딩 리트리버 (검색 결과를 3개로 제한)
        embedding_retriever = self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 3}
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
            bm25_retriever.k = 3  # BM25도 3개로 제한
            retrievers.append(bm25_retriever)
            weights = [0.3, 0.7]
        self.ensemble_retriever = EnsembleRetriever(
            retrievers=retrievers,
            weights=weights
        )
        self.logger.info(f"Career 앙상블 리트리버 준비 완료 (문서 수: {len(all_docs)})")

    def retrieve(self, query: str, k: int = 3):
        """앙상블 리트리버로 검색 (기본 3개 결과) + 시간 기반 필터링"""
        if not self.ensemble_retriever:
            return []
        
        # 기본 검색 수행
        all_docs = self.ensemble_retriever.get_relevant_documents(query)
        
        # 최근 키워드 감지 및 연도 추출
        recent_keywords = ['최근', '최신', 'recent', '요즘', '지금', '현재', '새로운', '신규', '트렌드']
        is_recent_query = any(keyword in query.lower() for keyword in recent_keywords)
        
        # 쿼리에서 연도 정보 추출
        years_info = self._extract_years_from_query(query)
        
        # "신입" 또는 "입사" 키워드가 있으면 시작 연도 기준으로 필터링
        new_hire_keywords = ['신입', '입사', '새로', '신규', '시작', '처음']
        focus_on_start_year = any(keyword in query.lower() for keyword in new_hire_keywords)
        
        if is_recent_query or years_info.get('n_years') or years_info.get('specific_year'):
            current_year = datetime.now().year
            
            # 연도 정보가 있으면 우선 사용, 없으면 기본 3년
            if years_info.get('n_years'):
                min_year = current_year - years_info['n_years']
                self.logger.info(f"쿼리에서 추출된 연도: 최근 {years_info['n_years']}년 ({min_year}년 이후)")
            elif years_info.get('specific_year'):
                min_year = years_info['specific_year']
                self.logger.info(f"쿼리에서 추출된 특정 연도: {min_year}년 이후")
            else:
                min_year = current_year - 3  # 기본값: 최근 3년
                self.logger.info(f"기본 설정: 최근 3년 ({min_year}년 이후)")
            
            if focus_on_start_year:
                # 신입/입사 관련 쿼리인 경우: 시작 연도 기준
                self.logger.info(f"신입/입사 관련 쿼리 감지됨. {min_year}년 이후 **시작된** 활동 데이터 필터링 시작...")
                filtered_docs = []
                for doc in all_docs:
                    try:
                        metadata = doc.metadata or {}
                        start_year = metadata.get('activity_start_year')
                        
                        if start_year and isinstance(start_year, int) and start_year >= min_year:
                            filtered_docs.append(doc)
                            self.logger.debug(f"포함: {start_year}년 시작 활동 (Employee: {doc.metadata.get('employee_id', 'Unknown')})")
                        else:
                            self.logger.debug(f"제외: {start_year}년 시작 활동 (최소 기준: {min_year}년 이후 시작) (Employee: {doc.metadata.get('employee_id', 'Unknown')})")
                    except Exception as e:
                        self.logger.warning(f"문서 연도 추출 실패: {e}")
                        continue
            else:
                # 일반 최근 쿼리인 경우: 최근 활동이 있었던 직원들 중에서
                self.logger.info(f"시간 기반 필터링 시작: {min_year}년 이후 **활동이 있었던** 데이터 검색...")
                filtered_docs = []
                for doc in all_docs:
                    try:
                        metadata = doc.metadata or {}
                        
                        # 활동 연도 리스트에서 지정된 기간 내 활동이 있는지 확인
                        activity_years = metadata.get('activity_years_list', [])
                        if activity_years and isinstance(activity_years, list):
                            recent_activity_years = [year for year in activity_years 
                                                   if isinstance(year, int) and year >= min_year]
                            if recent_activity_years:
                                filtered_docs.append(doc)
                                self.logger.debug(f"포함: 최근 활동 연도 {recent_activity_years} (Employee: {doc.metadata.get('employee_id', 'Unknown')})")
                                continue
                        
                        # 폴백: 종료 연도가 최근인지 확인
                        end_year = metadata.get('activity_end_year')
                        if end_year and isinstance(end_year, int) and end_year >= min_year:
                            filtered_docs.append(doc)
                            self.logger.debug(f"포함: {end_year}년 종료 활동 (Employee: {doc.metadata.get('employee_id', 'Unknown')})")
                        else:
                            self.logger.debug(f"제외: 최근 활동 없음 (Employee: {doc.metadata.get('employee_id', 'Unknown')})")
                    except Exception as e:
                        self.logger.warning(f"문서 연도 추출 실패: {e}")
                        continue
            
            self.logger.info(f"시간 필터링 완료: 전체 {len(all_docs)}개 → 필터링된 {len(filtered_docs)}개 문서")
            return filtered_docs[:k]
        
        return all_docs[:k]
    
    def _extract_years_from_query(self, query: str) -> dict:
        """쿼리에서 연도 관련 정보 추출"""
        years_info = {'n_years': None, 'specific_year': None}
        
        # "최근 N년" 패턴 매칭
        year_patterns = [
            r'최근\s*(\d+)\s*년',  # 최근 5년
            r'지난\s*(\d+)\s*년',  # 지난 5년
            r'과거\s*(\d+)\s*년',  # 과거 5년
            r'(\d+)\s*년\s*동안',  # 5년 동안
            r'(\d+)\s*년\s*간',    # 5년간
            r'(\d+)\s*년\s*이내',  # 5년 이내
            r'(\d+)\s*년\s*사이',  # 5년 사이
        ]
        
        for pattern in year_patterns:
            match = re.search(pattern, query)
            if match:
                try:
                    n_years = int(match.group(1))
                    if 1 <= n_years <= 50:  # 유효한 범위
                        years_info['n_years'] = n_years
                        break
                except ValueError:
                    continue
        
        # 특정 연도 패턴 매칭 (예: "2020년 이후", "2023년부터")
        specific_year_patterns = [
            r'(\d{4})\s*년\s*이후',  # 2020년 이후
            r'(\d{4})\s*년\s*부터',  # 2020년부터
            r'(\d{4})\s*년\s*이상',  # 2020년 이상
            r'(\d{4})\s*이후',      # 2020 이후
            r'(\d{4})\s*부터',      # 2020 부터
        ]
        
        for pattern in specific_year_patterns:
            match = re.search(pattern, query)
            if match:
                try:
                    year = int(match.group(1))
                    if 2000 <= year <= datetime.now().year:  # 유효한 연도 범위
                        years_info['specific_year'] = year
                        break
                except ValueError:
                    continue
        
        return years_info
    
    def _get_latest_year_from_doc(self, doc: Document) -> int:
        """문서에서 가장 최신 연도 정보 추출 (개선된 버전)"""
        metadata = doc.metadata or {}
        
        # 1. 활동 종료 연도 우선 확인 (가장 신뢰할 만한 정보)
        end_year = metadata.get('activity_end_year')
        if end_year and isinstance(end_year, int) and 2000 <= end_year <= 2030:
            return end_year
        
        # 2. 활동 연도 리스트에서 최신 연도 확인
        activity_years = metadata.get('activity_years_list', [])
        if activity_years and isinstance(activity_years, list):
            try:
                valid_years = [year for year in activity_years if isinstance(year, int) and 2000 <= year <= 2030]
                if valid_years:
                    return max(valid_years)
            except:
                pass
        
        # 3. 활동 시작 연도 확인 (종료 연도가 없는 경우)
        start_year = metadata.get('activity_start_year')
        if start_year and isinstance(start_year, int) and 2000 <= start_year <= 2030:
            return start_year
        
        # 4. 기존 방식으로 폴백
        return self._extract_year_from_doc(doc)
    
    def _extract_year_from_doc(self, doc: Document) -> int:
        """문서에서 연도 정보 추출"""
        # 메타데이터에서 연도 정보 찾기
        metadata = doc.metadata or {}
        
        # 직접적인 연도 필드들 확인
        year_fields = ['year', 'start_year', 'end_year', 'graduation_year', 'project_year']
        for field in year_fields:
            if field in metadata and metadata[field]:
                try:
                    year = int(metadata[field])
                    if 1980 <= year <= 2030:  # 유효한 연도 범위
                        return year
                except:
                    continue
        
        # 날짜 형식에서 연도 추출
        date_fields = ['date', 'start_date', 'end_date', 'created_at', 'updated_at']
        for field in date_fields:
            if field in metadata and metadata[field]:
                try:
                    date_str = str(metadata[field])
                    # YYYY-MM-DD, YYYY/MM/DD, YYYY.MM.DD 형식 처리
                    year_match = re.search(r'(\d{4})', date_str)
                    if year_match:
                        year = int(year_match.group(1))
                        if 1980 <= year <= 2030:
                            return year
                except:
                    continue
        
        # 문서 내용에서 연도 추출 (마지막 수단)
        content = doc.page_content or ""
        # "2023년", "2024년" 등의 패턴 찾기
        year_patterns = [
            r'(\d{4})년',  # 2023년
            r'(\d{4})\s*-\s*(\d{4})',  # 2022-2024
            r'(\d{4})/(\d{1,2})',  # 2023/12
            r'(\d{4})\.(\d{1,2})'   # 2023.12
        ]
        
        years = []
        for pattern in year_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                try:
                    if isinstance(match, tuple):
                        # 여러 그룹이 있는 경우 모든 연도 수집
                        for group in match:
                            year = int(group)
                            if 1980 <= year <= 2030:
                                years.append(year)
                    else:
                        year = int(match)
                        if 1980 <= year <= 2030:
                            years.append(year)
                except:
                    continue
        
        # 가장 최근 연도 반환
        return max(years) if years else None

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
