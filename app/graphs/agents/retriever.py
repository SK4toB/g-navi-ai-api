# app/graphs/agents/retriever.py

import os
import json
import re
import requests
import logging
from typing import Dict, List, Any
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from langchain.embeddings import CacheBackedEmbeddings
from langchain.storage import LocalFileStore
from langchain.schema import Document
from datetime import datetime, timedelta
from .k8s_chroma_adapter import K8sChromaDBAdapter, K8sChromaRetriever

from dotenv import load_dotenv
load_dotenv()


# ==================== 📂 경로 설정 (수정 필요시 여기만 변경) ====================
class PathConfig:
    """
    모든 경로 설정을 한 곳에서 관리하는 클래스
    K8s 환경에서는 PVC 마운트 경로를 우선 사용하고, 로컬 환경에서는 기존 경로를 사용합니다.
    """
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # app 디렉토리
    
    @classmethod
    def _get_k8s_pvc_path(cls) -> str:
        """K8s PVC 마운트 경로 반환"""
        return os.environ.get('APP_STORAGE_PVC_PATH', '/mnt/gnavi')
    
    @classmethod
    def _is_k8s_environment(cls) -> bool:
        """K8s 환경인지 확인"""
        pvc_path = cls._get_k8s_pvc_path()
        return os.path.exists(pvc_path)
    
    @classmethod
    def _get_app_root_dir(cls) -> str:
        """app 루트 디렉토리 반환 (graphs/agents에서 app까지 올라가기)"""
        # 현재 파일이 app/graphs/agents/retriever.py 라면
        # app 디렉토리까지 올라가야 함
        current_dir = os.path.dirname(__file__)  # app/graphs/agents/
        app_dir = os.path.dirname(os.path.dirname(current_dir))  # app/
        return app_dir
    
    @classmethod
    def _get_smart_docs_path(cls, filename: str) -> str:
        """K8s 환경이면 PVC 경로, 아니면 로컬 app/storage/docs 경로 반환"""
        if cls._is_k8s_environment():
            # K8s 환경: /mnt/gnavi/docs/filename
            k8s_path = os.path.join(cls._get_k8s_pvc_path(), 'docs', filename)
            if os.path.exists(k8s_path):
                return k8s_path
            # K8s 환경이지만 PVC에 파일이 없으면 로컬 폴백
            local_fallback = os.path.join(cls._get_app_root_dir(), 'storage', 'docs', filename)
            if os.path.exists(local_fallback):
                return local_fallback
            # 둘 다 없으면 K8s 경로 반환 (원래 의도대로)
            return k8s_path
        else:
            # 로컬 환경: app/storage/docs/filename  
            return os.path.join(cls._get_app_root_dir(), 'storage', 'docs', filename)
    
    # 📊 벡터 스토어 경로 (Chroma DB 저장소) - 기존 방식 유지
    CAREER_VECTOR_STORE = "../../storage/vector_stores/career_data"
    EDUCATION_VECTOR_STORE = "../../storage/vector_stores/education_courses"
    
    # 🗄️ 캐시 경로 (임베딩 캐시) - 기존 방식 유지  
    CAREER_EMBEDDING_CACHE = "../../storage/cache/embedding_cache"
    EDUCATION_EMBEDDING_CACHE = "../../storage/cache/education_embedding_cache"
    
    # 📄 문서 경로 (JSON 데이터 파일들) - 스마트 경로 적용 (기존 속성명 유지)
    @classmethod
    def _init_paths(cls):
        """경로 초기화 - 모듈 로드 시 한 번만 실행"""
        cls.CAREER_DOCS = cls._get_smart_docs_path("career_history.json")
        cls.EDUCATION_DOCS = cls._get_smart_docs_path("education_courses.json") 
        cls.SKILL_MAPPING = cls._get_smart_docs_path("skill_education_mapping.json")
        cls.COURSE_DEDUPLICATION = cls._get_smart_docs_path("course_deduplication_index.json")
        cls.COMPANY_VISION = cls._get_smart_docs_path("company_vision.json")
        cls.MYSUNI_DETAILED = cls._get_smart_docs_path("mysuni_courses_detailed.json")
        cls.COLLEGE_DETAILED = cls._get_smart_docs_path("college_courses_detailed.json")
    
    @classmethod
    def get_abs_path(cls, relative_path: str) -> str:
        """상대 경로를 절대 경로로 변환"""
        return os.path.abspath(os.path.join(os.path.dirname(__file__), relative_path))
    
    @classmethod
    def log_current_environment(cls):
        """현재 환경 정보 로그 출력"""
        env_type = "K8s PVC" if cls._is_k8s_environment() else "로컬"
        print(f"🔍 [PathConfig] 환경 감지: {env_type}")
        print(f"📁 [PathConfig] App 루트 디렉토리: {cls._get_app_root_dir()}")
        if cls._is_k8s_environment():
            print(f"📁 [PathConfig] PVC 경로: {cls._get_k8s_pvc_path()}")
        print(f"📄 [PathConfig] 커리어 문서: {cls.CAREER_DOCS}")
        print(f"📚 [PathConfig] 교육과정 문서: {cls.EDUCATION_DOCS}")
        print(f"🔗 [PathConfig] 스킬 매핑: {cls.SKILL_MAPPING}")
        print(f"🔄 [PathConfig] 중복제거 인덱스: {cls.COURSE_DEDUPLICATION}")
        print(f"🏢 [PathConfig] 회사 비전: {cls.COMPANY_VISION}")
        print(f"🎓 [PathConfig] mySUNI 상세: {cls.MYSUNI_DETAILED}")
        print(f"🏫 [PathConfig] College 상세: {cls.COLLEGE_DETAILED}")
        return env_type
    
    @classmethod
    def check_files_exist(cls):
        """모든 파일이 존재하는지 확인"""
        files_to_check = {
            "커리어 문서": cls.CAREER_DOCS,
            "교육과정 문서": cls.EDUCATION_DOCS,
            "스킬 매핑": cls.SKILL_MAPPING,
            "중복제거 인덱스": cls.COURSE_DEDUPLICATION,
            "회사 비전": cls.COMPANY_VISION,
            "mySUNI 상세": cls.MYSUNI_DETAILED,
            "College 상세": cls.COLLEGE_DETAILED
        }
        
        missing_files = []
        existing_files = []
        
        for name, path in files_to_check.items():
            if os.path.exists(path):
                existing_files.append(f"✅ {name}: {path}")
            else:
                missing_files.append(f"❌ {name}: {path}")
        
        print("📋 [PathConfig] 파일 존재 여부 확인:")
        for file_info in existing_files:
            print(f"  {file_info}")
        for file_info in missing_files:
            print(f"  {file_info}")
        
        return len(missing_files) == 0

# 클래스 로드 시 경로 초기화 실행
PathConfig._init_paths()

# ==================== 📂 경로 설정 끝 ====================

class CareerEnsembleRetrieverAgent:
    """
    🔍 커리어 앙상블 리트리버 에이전트
    
    BM25 + LLM 임베딩 앙상블을 활용하여 커리어 사례와 교육과정을
    효과적으로 검색합니다. ChromaDB와 캐시를 활용한 고성능 검색을 제공합니다.
    
    📊 검색 결과:
    - 커리어 사례: 최대 3개까지 검색
    - 교육과정: 최대 3개까지 검색
    """
    def __init__(self, persist_directory: str = None, cache_directory: str = None):
        """
        CareerEnsembleRetrieverAgent 초기화
        
        Args:
            persist_directory: 커리어 벡터 스토어 경로 (기본값: PathConfig.CAREER_VECTOR_STORE)
            cache_directory: 커리어 임베딩 캐시 경로 (기본값: PathConfig.CAREER_EMBEDDING_CACHE)
        """
        # 로거 초기화
        self.logger = logging.getLogger(__name__)
        
        # 환경 정보 및 파일 존재 여부 확인
        env_type = PathConfig.log_current_environment()
        self.is_k8s = PathConfig._is_k8s_environment()
        print(f"🔍 [CareerRetrieverAgent] 환경: {env_type}, K8s: {self.is_k8s}")
        
        # 경로 설정 (기존 속성 방식 사용)
        self.persist_directory = PathConfig.get_abs_path(
            persist_directory or PathConfig.CAREER_VECTOR_STORE
        )
        self.career_cache_directory = PathConfig.get_abs_path(
            cache_directory or PathConfig.CAREER_EMBEDDING_CACHE
        )
        self.base_dir = PathConfig.BASE_DIR
        
        # 디렉토리 생성 (로컬 환경에서만)
        if not self.is_k8s:
            os.makedirs(self.persist_directory, exist_ok=True)
            os.makedirs(self.career_cache_directory, exist_ok=True)

        # 커리어 전용 임베딩 설정
        self.base_embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            dimensions=1536
        )
        
        # 캐시 설정 (로컬 환경에서만)
        if not self.is_k8s:
            self.career_cached_embeddings = CacheBackedEmbeddings.from_bytes_store(
                self.base_embeddings,
                LocalFileStore(self.career_cache_directory),
                namespace="career_embeddings"
            )
        else:
            # K8s 환경에서는 캐시 없이 직접 임베딩 사용
            self.career_cached_embeddings = self.base_embeddings
        
        # 교육과정 전용 임베딩 설정
        if not self.is_k8s:
            self.education_cache_directory = PathConfig.get_abs_path(PathConfig.EDUCATION_EMBEDDING_CACHE)
            os.makedirs(self.education_cache_directory, exist_ok=True)
            self.education_cached_embeddings = CacheBackedEmbeddings.from_bytes_store(
                self.base_embeddings,
                LocalFileStore(self.education_cache_directory),
                namespace="education_embeddings"
            )
        else:
            # K8s 환경에서는 캐시 없이 직접 임베딩 사용
            self.education_cached_embeddings = self.base_embeddings
        
        self.vectorstore = None
        self.ensemble_retriever = None
        
        # 교육과정 관련 경로 설정 (기존 속성 방식 사용)
        if not self.is_k8s:
            self.education_persist_dir = PathConfig.get_abs_path(PathConfig.EDUCATION_VECTOR_STORE)
        self.education_docs_path = PathConfig.EDUCATION_DOCS
        self.skill_mapping_path = PathConfig.SKILL_MAPPING
        self.deduplication_index_path = PathConfig.COURSE_DEDUPLICATION
        
        # 회사 비전 관련 경로 설정
        self.company_vision_path = PathConfig.COMPANY_VISION
        
        # 지연 로딩 속성
        self.education_vectorstore = None
        self.skill_education_mapping = None
        self.course_deduplication_index = None
        self.company_vision_data = None
        
        self._load_vectorstore_and_retriever()

    def _load_vectorstore_and_retriever(self):
        """벡터스토어와 앙상블 리트리버 로드 (환경별 분기)"""
        if self.is_k8s:
            self._load_k8s_vectorstore_and_retriever()
        else:
            self._load_local_vectorstore_and_retriever()

    def _load_k8s_vectorstore_and_retriever(self):
        """K8s 환경: 외부 ChromaDB 사용"""
        print("🔗 [K8s ChromaDB] 외부 ChromaDB 연결 중...")
        
        # K8s ChromaDB 어댑터 초기화
        self.vectorstore = K8sChromaDBAdapter("career_history", self.career_cached_embeddings)
        
        # 컬렉션 정보 확인
        collection_info = self.vectorstore.get_collection_info()
        if collection_info.get("status") == "success":
            print(f"✅ [K8s ChromaDB] 연결 성공: {collection_info.get('document_count')}개 문서")
        else:
            print(f"❌ [K8s ChromaDB] 연결 실패: {collection_info.get('message')}")
        
        # LLM 임베딩 리트리버 (검색 결과를 3개로 제한)
        embedding_retriever = self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 3}
        )
        
        # BM25용 docs 로드 (JSON 파일은 여전히 사용)
        docs_path = PathConfig.CAREER_DOCS
        all_docs = []
        try:
            with open(docs_path, 'r', encoding='utf-8') as f:
                json_docs = json.load(f)
                all_docs = [Document(page_content=doc['page_content'], metadata=doc['metadata']) for doc in json_docs]
            self.logger.info(f"BM25용 career_docs.json 로드 완료 (문서 수: {len(all_docs)}) - 경로: {docs_path}")
        except Exception as e:
            self.logger.warning(f"BM25용 career_docs.json 로드 실패: {e} - 경로: {docs_path}")
        
        # 앙상블 리트리버 구성
        retrievers = [embedding_retriever]
        weights = [1.0]
        if all_docs:
            bm25_retriever = BM25Retriever.from_documents(all_docs)
            bm25_retriever.k = 3  # BM25도 3개로 제한
            retrievers.append(bm25_retriever)
            weights = [0.3, 0.7]  # K8s ChromaDB: 30%, BM25: 70%
        
        self.ensemble_retriever = EnsembleRetriever(
            retrievers=retrievers,
            weights=weights
        )
        self.logger.info(f"K8s Career 앙상블 리트리버 준비 완료 (JSON 문서 수: {len(all_docs)})")
        print(f"✅ [K8s 커리어 사례 VectorDB] 초기화 완료")
    
    def _load_local_vectorstore_and_retriever(self):
        """로컬 환경: 기존 로컬 ChromaDB 사용"""
        print("💾 [로컬 ChromaDB] 로컬 ChromaDB 로드 중...")
        
        # Chroma 벡터스토어 로드
        self.vectorstore = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.career_cached_embeddings,
            collection_name="career_history"
        )
        # LLM 임베딩 리트리버 (검색 결과를 3개로 제한)
        embedding_retriever = self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 3}
        )
        # BM25용 docs 로드
        docs_path = PathConfig.CAREER_DOCS
        all_docs = []
        try:
            with open(docs_path, 'r', encoding='utf-8') as f:
                json_docs = json.load(f)
                all_docs = [Document(page_content=doc['page_content'], metadata=doc['metadata']) for doc in json_docs]
            self.logger.info(f"BM25용 career_docs.json 로드 완료 (문서 수: {len(all_docs)}) - 경로: {docs_path}")
        except Exception as e:
            self.logger.warning(f"BM25용 career_docs.json 로드 실패: {e} - 경로: {docs_path}")
        
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
        self.logger.info(f"로컬 Career 앙상블 리트리버 준비 완료 (문서 수: {len(all_docs)})")
        print(f"✅ [로컬 커리어 사례 VectorDB] 초기화 완료")

    def retrieve(self, query: str, k: int = 3):
        """앙상블 리트리버로 검색 (기본 3개 결과) + 시간 기반 필터링"""
        print(f"🔍 [커리어 사례 검색] 시작 - '{query}'")
        
        if not self.ensemble_retriever:
            print(f"❌ [커리어 사례 검색] 앙상블 리트리버가 없음")
            return []
        
        # 기본 검색 수행
        # all_docs = self.ensemble_retriever.invoke(query)
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
            final_docs = filtered_docs[:k]
        else:
            final_docs = all_docs[:k]
        
        # 회사 비전 정보를 결과에 추가 (커리어 관련 질문인 경우)
        career_keywords = ['커리어', '진로', '성장', '발전', '목표', '방향', '계획', '비전', '미래', '회사', '조직']
        if any(keyword in query.lower() for keyword in career_keywords):
            company_vision = self._load_company_vision()
            if company_vision:
                # 회사 비전을 Document 형태로 추가
                vision_content = self._format_company_vision_for_context(company_vision)
                vision_doc = Document(
                    page_content=vision_content,
                    metadata={"type": "company_vision", "source": "company_vision.json"}
                )
                final_docs.append(vision_doc)
                self.logger.info("회사 비전 정보가 검색 결과에 추가되었습니다.")
        
        print(f"✅ [커리어 사례 검색] 완료: {len(final_docs)}개 결과 반환")
        return final_docs
    
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

    def _load_education_resources(self):
        """교육과정 리소스 지연 로딩"""
        if self.education_vectorstore is None:
            self._initialize_education_vectorstore()
        if self.skill_education_mapping is None:
            self._load_skill_education_mapping()
        if self.course_deduplication_index is None:
            self._load_deduplication_index()
    
    def _initialize_education_vectorstore(self):
        """교육과정 VectorDB 초기화 (환경별 분기)"""
        if self.is_k8s:
            self._initialize_k8s_education_vectorstore()
        else:
            self._initialize_local_education_vectorstore()
    
    def _initialize_k8s_education_vectorstore(self):
        """K8s 환경: 외부 교육과정 ChromaDB 초기화"""
        try:
            print("🔗 [K8s 교육과정 ChromaDB] 외부 ChromaDB 연결 중...")
            self.education_vectorstore = K8sChromaDBAdapter("education_courses", self.education_cached_embeddings)
            
            # 컬렉션 정보 확인
            collection_info = self.education_vectorstore.get_collection_info()
            if collection_info.get("status") == "success":
                print(f"✅ [K8s 교육과정 ChromaDB] 연결 성공: {collection_info.get('document_count')}개 문서")
            else:
                print(f"❌ [K8s 교육과정 ChromaDB] 연결 실패: {collection_info.get('message')}")
                self.education_vectorstore = None
        except Exception as e:
            self.logger.error(f"K8s 교육과정 VectorDB 로드 실패: {e}")
            print(f"❌ [K8s 교육과정 ChromaDB] 로드 실패: {e}")
            self.education_vectorstore = None
    
    def _initialize_local_education_vectorstore(self):
        """로컬 환경: 기존 로컬 교육과정 ChromaDB 초기화"""
        try:
            if os.path.exists(self.education_persist_dir):
                self.education_vectorstore = Chroma(
                    persist_directory=self.education_persist_dir,
                    embedding_function=self.education_cached_embeddings,
                    collection_name="education_courses"
                )
                self.logger.info("로컬 교육과정 VectorDB 로드 완료")
                print(f"✅ [로컬 교육과정 VectorDB] 초기화 완료")
            else:
                self.logger.warning("로컬 교육과정 VectorDB가 존재하지 않습니다.")
                print(f"⚠️  [로컬 교육과정 VectorDB] 없음 - JSON 파일로 폴백 검색 진행")
        except Exception as e:
            self.logger.error(f"로컬 교육과정 VectorDB 로드 실패: {e}")
            print(f"❌ [로컬 교육과정 VectorDB] 로드 실패: {e}")
            self.education_vectorstore = None
    
    def _load_skill_education_mapping(self):
        """스킬-교육과정 매핑 로드"""
        try:
            if os.path.exists(self.skill_mapping_path):
                with open(self.skill_mapping_path, "r", encoding="utf-8") as f:
                    self.skill_education_mapping = json.load(f)
                self.logger.info(f"스킬-교육과정 매핑 로드 완료: {len(self.skill_education_mapping)}개 스킬")
            else:
                self.skill_education_mapping = {}
                self.logger.warning("스킬-교육과정 매핑 파일이 없습니다.")
        except Exception as e:
            self.logger.error(f"스킬-교육과정 매핑 로드 실패: {e}")
            self.skill_education_mapping = {}
    
    def _load_deduplication_index(self):
        """중복 제거 인덱스 로드"""
        try:
            if os.path.exists(self.deduplication_index_path):
                with open(self.deduplication_index_path, "r", encoding="utf-8") as f:
                    self.course_deduplication_index = json.load(f)
                self.logger.info(f"중복 제거 인덱스 로드 완료: {len(self.course_deduplication_index)}개 그룹")
            else:
                self.course_deduplication_index = {}
                self.logger.warning("중복 제거 인덱스 파일이 없습니다.")
        except Exception as e:
            self.logger.error(f"중복 제거 인덱스 로드 실패: {e}")
            self.course_deduplication_index = {}
    
    def _load_company_vision(self):
        """회사 비전 데이터 로드"""
        if self.company_vision_data is not None:
            return self.company_vision_data
            
        try:
            if os.path.exists(self.company_vision_path):
                with open(self.company_vision_path, "r", encoding="utf-8") as f:
                    self.company_vision_data = json.load(f)
                self.logger.info("회사 비전 데이터 로드 완료")
            else:
                self.company_vision_data = {}
                self.logger.warning("회사 비전 파일이 없습니다.")
        except Exception as e:
            self.logger.error(f"회사 비전 데이터 로드 실패: {e}")
            self.company_vision_data = {}
        
        return self.company_vision_data
    
    def _format_company_vision_for_context(self, vision_data: Dict) -> str:
        """회사 비전 데이터를 컨텍스트용 텍스트로 포맷팅"""
        if not vision_data:
            return ""
        
        sections = []
        
        # 회사 기본 정보
        if vision_data.get('company_name'):
            sections.append(f"회사명: {vision_data['company_name']}")
        
        # 비전
        if vision_data.get('vision'):
            vision = vision_data['vision']
            sections.append(f"비전: {vision.get('title', '')}")
            if vision.get('description'):
                sections.append(f"비전 설명: {vision['description']}")
        
        # 핵심 가치
        if vision_data.get('core_values'):
            values_text = []
            for value in vision_data['core_values']:
                values_text.append(f"- {value.get('name', '')}: {value.get('description', '')}")
            if values_text:
                sections.append("핵심 가치:\n" + "\n".join(values_text))
        
        # 전략 방향
        if vision_data.get('strategic_directions'):
            strategy_text = []
            for direction in vision_data['strategic_directions']:
                strategy_text.append(f"- {direction.get('category', '')}: {direction.get('description', '')}")
            if strategy_text:
                sections.append("전략 방향:\n" + "\n".join(strategy_text))
        
        # 인재 개발
        if vision_data.get('talent_development'):
            talent = vision_data['talent_development']
            sections.append(f"인재 개발 철학: {talent.get('philosophy', '')}")
            if talent.get('focus_areas'):
                focus_text = []
                for area in talent['focus_areas']:
                    focus_text.append(f"- {area.get('area', '')}: {area.get('description', '')}")
                if focus_text:
                    sections.append("역량 개발 중점 영역:\n" + "\n".join(focus_text))
        
        # 커리어 가이드 원칙
        if vision_data.get('career_guidance_principles'):
            principles_text = []
            for principle in vision_data['career_guidance_principles']:
                principles_text.append(f"- {principle.get('principle', '')}: {principle.get('description', '')}")
            if principles_text:
                sections.append("커리어 가이드 원칙:\n" + "\n".join(principles_text))
        
        return "\n\n".join(sections)

    def search_education_courses(self, query: str, user_profile: Dict, intent_analysis: Dict) -> Dict:
        """교육과정 검색 메인 함수 - 최대 3개까지만 검색"""
        print(f"🔍 [교육과정 검색] 시작 - '{query}'")
        self._load_education_resources()
        
        try:
            # 사용자의 교육과정 소스 선호도 확인
            preferred_source = self._get_preferred_education_source(query, user_profile, intent_analysis)
            
            # 1단계: 스킬 기반 빠른 필터링
            skill_based_courses = self._skill_based_course_filter(user_profile, intent_analysis)
            
            # 2단계: VectorDB 의미적 검색 (VectorDB가 없으면 JSON 폴백)
            semantic_matches = self._semantic_course_search(query, skill_based_courses)
            
            # 3단계: 선호도에 따른 소스 필터링
            if preferred_source:
                semantic_matches = self._filter_by_preferred_source(semantic_matches, preferred_source)
            
            # 4단계: 중복 제거 및 정렬
            deduplicated_courses = self._deduplicate_courses(semantic_matches)
            
            # 최종적으로 3개까지만 제한
            deduplicated_courses = deduplicated_courses[:3]
            
            # 5단계: 결과 분석 및 학습 경로 생성
            course_analysis = self._analyze_course_recommendations(deduplicated_courses)
            learning_path = self._generate_learning_path(deduplicated_courses)
            
            self.logger.info(f"교육과정 검색 완료: 최종 {len(deduplicated_courses)}개 과정 반환")
            print(f"✅ [교육과정 검색] 완료: {len(deduplicated_courses)}개 과정 반환")
            
            return {
                "recommended_courses": deduplicated_courses,
                "course_analysis": course_analysis,
                "learning_path": learning_path
            }
        except Exception as e:
            self.logger.error(f"교육과정 검색 중 오류: {e}")
            print(f"❌ [교육과정 검색] 오류 발생: {e}")
            return {
                "recommended_courses": [],
                "course_analysis": {"message": f"교육과정 검색 중 오류가 발생했습니다: {e}"},
                "learning_path": []
            }
    
    def _skill_based_course_filter(self, user_profile: Dict, intent_analysis: Dict) -> List[Dict]:
        """스킬 기반 1차 필터링 - JSON 인덱스 활용"""
        filtered_courses = []
        
        # 사용자 현재 스킬 추출
        current_skills = self._extract_user_skills(user_profile)
        
        # 의도 분석에서 목표 스킬 추출
        target_skills = intent_analysis.get("career_history", [])
        
        # 검색할 스킬 목록 생성
        search_skills = list(set(current_skills + target_skills))
        
        for skill_code in search_skills:
            if skill_code in self.skill_education_mapping:
                skill_courses = self.skill_education_mapping[skill_code]
                
                # College 과정 - 세분화 레벨별 추가
                for course_type in ["specialized", "recommended", "common_required"]:
                    if course_type in skill_courses.get("college", {}):
                        courses = skill_courses["college"][course_type]
                        for course in courses:
                            course_info = course.copy()
                            course_info["source"] = "college"
                            course_info["skill_relevance"] = course_type
                            course_info["target_skill"] = skill_code
                            filtered_courses.append(course_info)
                
                # mySUNI 과정 추가
                if "mysuni" in skill_courses:
                    for course in skill_courses["mysuni"]:
                        course_info = course.copy()
                        course_info["source"] = "mysuni"
                        course_info["skill_relevance"] = "general"
                        course_info["target_skill"] = skill_code
                        filtered_courses.append(course_info)
        
        self.logger.info(f"스킬 기반 필터링 결과: {len(filtered_courses)}개 과정")
        return filtered_courses
    
    def _extract_user_skills(self, user_profile: Dict) -> List[str]:
        """사용자 프로필에서 스킬 추출"""
        skills = []
        
        # 직접적인 스킬 정보가 있는 경우
        if "skills" in user_profile:
            skills.extend(user_profile["skills"])
        
        # 경력 정보에서 스킬 추출
        if "career_history" in user_profile:
            for career in user_profile["career_history"]:
                if "skills" in career:
                    skills.extend(career["skills"])
        
        return list(set(skills))
    
    def _semantic_course_search(self, query: str, filtered_courses: List[Dict]) -> List[Dict]:
        """VectorDB를 활용한 의미적 검색 (VectorDB가 없으면 JSON에서 검색) - 3개까지만 검색"""
        if not self.education_vectorstore:
            # VectorDB가 없으면 JSON 파일에서 직접 검색
            self.logger.info("VectorDB 없음 - JSON 파일에서 검색")
            return self._search_from_json_documents(query, filtered_courses)
            
        if not filtered_courses:
            # 필터링된 과정이 없으면 전체 VectorDB에서 검색 (3개로 제한)
            docs = self.education_vectorstore.similarity_search(query, k=3)
            courses = [self._doc_to_course_dict(doc) for doc in docs]
            # 원본 데이터로 상세 정보 보강
            courses = [self._enrich_course_with_original_data(course) for course in courses]
        else:
            # 필터링된 과정들의 course_id로 VectorDB에서 상세 검색
            course_ids = [course.get("course_id") for course in filtered_courses if course.get("course_id")]
            courses = self._search_by_course_ids(course_ids, query)
            
            # 필터링 정보를 VectorDB 결과에 병합
            for course in courses:
                for filtered_course in filtered_courses:
                    if course.get("course_id") == filtered_course.get("course_id"):
                        course.update(filtered_course)
                        break
            
            # 원본 데이터로 상세 정보 보강
            courses = [self._enrich_course_with_original_data(course) for course in courses]
        
        # 결과를 3개로 제한
        courses = courses[:3]
        self.logger.info(f"의미적 검색 결과: {len(courses)}개 과정 (3개로 제한)")
        return courses
    
    def _search_from_json_documents(self, query: str, filtered_courses: List[Dict]) -> List[Dict]:
        """JSON 문서에서 직접 검색 (VectorDB 대안) - 3개까지만 검색"""
        try:
            with open(self.education_docs_path, "r", encoding="utf-8") as f:
                all_docs = json.load(f)
        except FileNotFoundError:
            self.logger.warning("교육과정 문서 파일이 없습니다.")
            # 필터링된 과정이라도 반환하자 (3개로 제한)
            return filtered_courses[:3] if filtered_courses else []
        
        # 필터링된 과정이 있으면 우선적으로 활용
        if filtered_courses:
            # filtered_courses의 course_id들과 매칭되는 문서들 찾기
            filtered_course_ids = {course.get("course_id") for course in filtered_courses}
            matching_docs = []
            
            for doc in all_docs:
                metadata = doc.get("metadata", {})
                course_id = metadata.get("course_id")
                
                if course_id in filtered_course_ids:
                    course_dict = self._doc_to_course_dict_from_json(doc)
                    # 필터링 정보 병합
                    for filtered_course in filtered_courses:
                        if course_dict.get("course_id") == filtered_course.get("course_id"):
                            course_dict.update(filtered_course)
                            break
                    matching_docs.append(course_dict)
            
            if matching_docs:
                # 3개로 제한
                matching_docs = matching_docs[:3]
                self.logger.info(f"필터링된 과정 기반 검색 결과: {len(matching_docs)}개 (3개로 제한)")
                return matching_docs
        
        # 키워드 기반 검색
        query_keywords = query.lower().split()
        matching_docs = []
        
        for doc in all_docs:
            content = doc.get("page_content", "").lower()
            metadata = doc.get("metadata", {})
            
            # 키워드 매칭 점수 계산
            score = 0
            for keyword in query_keywords:
                if keyword in content:
                    score += 1
            
            if score > 0:
                course_dict = self._doc_to_course_dict_from_json(doc)
                course_dict["match_score"] = score
                matching_docs.append(course_dict)
        
        # 점수순으로 정렬
        matching_docs.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        
        # 3개로 제한
        matching_docs = matching_docs[:3]
        self.logger.info(f"키워드 기반 검색 결과: {len(matching_docs)}개 (3개로 제한)")
        return matching_docs
    
    def _doc_to_course_dict_from_json(self, doc_data: Dict) -> Dict:
        """JSON 문서 데이터를 과정 딕셔너리로 변환"""
        metadata = doc_data.get("metadata", {})
        return {
            "course_id": metadata.get("course_id"),
            "course_name": metadata.get("course_name", metadata.get("card_name")),
            "source": metadata.get("source"),
            "content": doc_data.get("page_content", ""),
            "target_skills": metadata.get("target_skills", []),
            "skill_relevance": metadata.get("skill_relevance"),
            "duration_hours": metadata.get("duration_hours", metadata.get("인정학습시간")),
            "difficulty_level": metadata.get("difficulty_level", metadata.get("난이도")),
            "department": metadata.get("department", metadata.get("학부")),
            "course_type": metadata.get("course_type", metadata.get("교육유형")),
            "평점": metadata.get("평점"),
            "이수자수": metadata.get("이수자수"),
            "카테고리명": metadata.get("카테고리명"),
            "채널명": metadata.get("채널명"),
            "표준과정": metadata.get("표준과정"),
            "url": metadata.get("url")  # URL 필드 추가
        }
    
    def _search_by_course_ids(self, course_ids: List[str], query: str) -> List[Dict]:
        """특정 과정 ID들에 대한 VectorDB 검색 - 3개까지만 검색"""
        if not course_ids:
            return []
        
        # 각 course_id에 대해 검색하고 결과 통합
        all_docs = []
        for course_id in course_ids[:10]:  # 검색할 course_id는 최대 10개로 제한
            try:
                # 메타데이터 필터를 사용한 검색
                docs = self.education_vectorstore.similarity_search(
                    query, 
                    k=1,  # 각 과정당 1개씩만 가져와서 전체적으로 3개 제한 유지
                    filter={"course_id": course_id}
                )
                all_docs.extend(docs)
                # 이미 3개가 되면 중단
                if len(all_docs) >= 3:
                    break
            except Exception as e:
                self.logger.warning(f"Course ID {course_id} 검색 실패: {e}")
        
        # 일반 검색도 수행 (백업) - 3개로 제한
        if not all_docs:
            all_docs = self.education_vectorstore.similarity_search(query, k=3)
        
        # 결과를 3개로 제한
        all_docs = all_docs[:3]
        return [self._doc_to_course_dict(doc) for doc in all_docs]
    
    def _doc_to_course_dict(self, doc: Document) -> Dict:
        """VectorDB Document를 과정 딕셔너리로 변환"""
        metadata = doc.metadata or {}
        return {
            "course_id": metadata.get("course_id"),
            "course_name": metadata.get("course_name", metadata.get("card_name")),
            "source": metadata.get("source"),
            "content": doc.page_content,
            "target_skills": metadata.get("target_skills", []),
            "skill_relevance": metadata.get("skill_relevance"),
            "duration_hours": metadata.get("duration_hours", metadata.get("인정학습시간")),
            "difficulty_level": metadata.get("difficulty_level", metadata.get("난이도")),
            "department": metadata.get("department", metadata.get("학부")),
            "course_type": metadata.get("course_type", metadata.get("교육유형")),
            "평점": metadata.get("평점"),
            "이수자수": metadata.get("이수자수"),
            "카테고리명": metadata.get("카테고리명"),
            "채널명": metadata.get("채널명"),
            "표준과정": metadata.get("표준과정"),
            "url": metadata.get("url")  # URL 필드 추가
        }
    
    def _deduplicate_courses(self, courses: List[Dict]) -> List[Dict]:
        """College와 mySUNI 간 중복 과정 제거 (mySUNI 메타데이터 보존)"""
        if not courses:
            return []
        
        deduplicated = []
        seen_courses = set()
        
        # 우선순위: College > mySUNI (College가 더 상세한 정보 제공)
        def sort_priority(course):
            source_priority = 0 if course.get("source") == "college" else 1
            
            if course.get("source") == "college":
                relevance = course.get("skill_relevance", "")
                if relevance == "specialized":
                    relevance_priority = 0
                elif relevance == "recommended":
                    relevance_priority = 1
                else:  # common_required
                    relevance_priority = 2
            else:
                # mySUNI는 평점 기준 정렬
                rating = course.get("평점", 0)
                try:
                    rating = float(rating) if rating else 0
                except:
                    rating = 0
                relevance_priority = 5 - rating  # 평점이 높을수록 우선순위 높음
            
            return (source_priority, relevance_priority)
        
        sorted_courses = sorted(courses, key=sort_priority)
        
        for course in sorted_courses:
            course_signature = self._generate_course_signature(course)
            
            if course_signature not in seen_courses:
                # 중복 과정이 있는 경우 mySUNI 데이터를 College 과정에 통합
                if course_signature in self.course_deduplication_index:
                    duplicate_info = self.course_deduplication_index[course_signature]
                    
                    # College 과정이 우선이므로 mySUNI 데이터를 추가 정보로 병합
                    if course.get("source") == "college":
                        mysuni_data = self._find_mysuni_duplicate(duplicate_info, courses)
                        if mysuni_data:
                            course["mysuni_alternative"] = {
                                "available": True,
                                "card_name": mysuni_data.get("card_name"),
                                "평점": mysuni_data.get("평점"),
                                "이수자수": mysuni_data.get("이수자수"),
                                "난이도": mysuni_data.get("난이도"),
                                "인정학습시간": mysuni_data.get("인정학습시간"),
                                "카테고리명": mysuni_data.get("카테고리명"),
                                "채널명": mysuni_data.get("채널명")
                            }
                        else:
                            course["mysuni_alternative"] = {"available": False}
                    else:
                        # mySUNI 과정인 경우 원본 데이터 유지
                        course["mysuni_alternative"] = {"available": False}
                    
                    course["alternative_platforms"] = duplicate_info.get("platforms", [])
                else:
                    # 중복이 없는 과정인 경우
                    if course.get("source") == "mysuni":
                        course["mysuni_alternative"] = {"available": False}
                
                deduplicated.append(course)
                seen_courses.add(course_signature)
        
        self.logger.info(f"중복 제거 완료: {len(courses)}개 → {len(deduplicated)}개")
        return deduplicated
    
    def _generate_course_signature(self, course: Dict) -> str:
        """과정 중복 판별을 위한 시그니처 생성"""
        name = course.get("course_name", course.get("card_name", "")).lower().strip()
        skills = sorted(course.get("target_skills", []))
        
        # 유사한 과정명 정규화
        normalized_name = re.sub(r'[^\w\s]', '', name)
        normalized_name = re.sub(r'\s+', ' ', normalized_name)
        
        return f"{normalized_name}_{','.join(skills)}"
    
    def _find_mysuni_duplicate(self, duplicate_info: Dict, all_courses: List[Dict]) -> Dict:
        """중복 정보에서 mySUNI 과정 찾기"""
        mysuni_course_info = None
        for course_info in duplicate_info.get("courses", []):
            if course_info.get("platform") == "mySUNI":
                course_id = course_info.get("course_id")
                # 전체 과정 리스트에서 해당 mySUNI 과정 찾기
                for course in all_courses:
                    if (course.get("source") == "mysuni" and 
                        course.get("course_id") == course_id):
                        mysuni_course_info = course
                        break
                break
        
        return mysuni_course_info
    
    def _analyze_course_recommendations(self, courses: List[Dict]) -> Dict:
        """추천 과정 분석 결과 생성 (mySUNI 데이터 포함)"""
        if not courses:
            return {"message": "추천할 교육과정이 없습니다."}
        
        college_courses = [c for c in courses if c.get("source") == "college"]
        mysuni_courses = [c for c in courses if c.get("source") == "mysuni"]
        
        # College 과정 세분화 분석
        specialized_count = len([c for c in college_courses if c.get("skill_relevance") == "specialized"])
        recommended_count = len([c for c in college_courses if c.get("skill_relevance") == "recommended"])
        required_count = len([c for c in college_courses if c.get("skill_relevance") == "common_required"])
        
        # mySUNI 대안 정보 분석
        college_with_mysuni_alt = len([c for c in college_courses 
                                      if c.get("mysuni_alternative", {}).get("available")])
        
        # mySUNI 과정 평점 분석
        mysuni_ratings = []
        for c in mysuni_courses:
            rating = c.get("평점", 0)
            try:
                rating = float(rating) if rating else 0
                if rating > 0:
                    mysuni_ratings.append(rating)
            except:
                continue
        
        avg_mysuni_rating = sum(mysuni_ratings) / len(mysuni_ratings) if mysuni_ratings else 0
        
        # 이수자 수 합계
        total_enrollments = 0
        for course in mysuni_courses:
            enrollments_str = str(course.get("이수자수", "0"))
            try:
                enrollments = int(enrollments_str.replace(",", "")) if enrollments_str.replace(",", "").isdigit() else 0
                total_enrollments += enrollments
            except:
                continue
        
        return {
            "total_courses": len(courses),
            "college_courses": len(college_courses),
            "mysuni_courses": len(mysuni_courses),
            "skill_depth_analysis": {
                "specialized": specialized_count,
                "recommended": recommended_count, 
                "common_required": required_count
            },
            "learning_platforms": {
                "college_available": len(college_courses) > 0,
                "mysuni_available": len(mysuni_courses) > 0,
                "college_with_mysuni_alternatives": college_with_mysuni_alt
            },
            "mysuni_quality_metrics": {
                "average_rating": round(avg_mysuni_rating, 1),
                "total_enrollments": total_enrollments,
                "high_rated_courses": len([r for r in mysuni_ratings if r >= 4.5])
            }
        }
    
    def _generate_learning_path(self, courses: List[Dict]) -> List[Dict]:
        """학습 경로 제안 생성"""
        if not courses:
            return []
        
        path = []
        
        # 1단계: 공통 필수 과정
        required_courses = [c for c in courses if c.get("skill_relevance") == "common_required"]
        if required_courses:
            path.append({
                "step": 1,
                "level": "기초/필수",
                "courses": required_courses[:2],  # 최대 2개
                "description": "기본 지식 습득을 위한 필수 과정"
            })
        
        # 2단계: 추천 과정
        recommended_courses = [c for c in courses if c.get("skill_relevance") == "recommended"]
        if recommended_courses:
            path.append({
                "step": 2,
                "level": "확장/응용",
                "courses": recommended_courses[:3],  # 최대 3개
                "description": "관련 기술 확장을 위한 추천 과정"
            })
        
        # 3단계: 전문화 과정
        specialized_courses = [c for c in courses if c.get("skill_relevance") == "specialized"]
        if specialized_courses:
            path.append({
                "step": 3,
                "level": "전문/심화",
                "courses": specialized_courses[:2],  # 최대 2개
                "description": "전문성 강화를 위한 특화 과정"
            })
        
        # mySUNI 과정은 보완/대안으로 제시
        mysuni_courses = [c for c in courses if c.get("source") == "mysuni"]
        if mysuni_courses:
            path.append({
                "step": "보완",
                "level": "온라인/자율",
                "courses": mysuni_courses[:3],  # 최대 3개
                "description": "온라인으로 학습 가능한 보완 과정"
            })
        
        return path

    def _load_original_course_data(self):
        """원본 교육과정 상세 데이터 로드 (기존 속성 방식 사용)"""
        if not hasattr(self, 'original_mysuni_data'):
            try:
                mysuni_path = PathConfig.MYSUNI_DETAILED
                with open(mysuni_path, "r", encoding="utf-8") as f:
                    self.original_mysuni_data = json.load(f)
                self.logger.info(f"mySUNI 원본 데이터 로드 완료: {len(self.original_mysuni_data)}개 - 경로: {mysuni_path}")
            except FileNotFoundError:
                self.logger.warning(f"mySUNI 원본 데이터 파일을 찾을 수 없습니다. - 경로: {PathConfig.MYSUNI_DETAILED}")
                self.original_mysuni_data = []
                
        if not hasattr(self, 'original_college_data'):
            try:
                college_path = PathConfig.COLLEGE_DETAILED
                with open(college_path, "r", encoding="utf-8") as f:
                    self.original_college_data = json.load(f)
                self.logger.info(f"College 원본 데이터 로드 완료: {len(self.original_college_data)}개 - 경로: {college_path}")
            except FileNotFoundError:
                self.logger.warning(f"College 원본 데이터 파일을 찾을 수 없습니다. - 경로: {PathConfig.COLLEGE_DETAILED}")
                self.original_college_data = []

    def _enrich_course_with_original_data(self, course: Dict) -> Dict:
        """VectorDB 검색 결과를 원본 데이터의 상세 정보로 보강"""
        self._load_original_course_data()
        
        course_id = course.get("course_id")
        source = course.get("source")
        
        if not course_id:
            return course
            
        # mySUNI 과정인 경우
        if source == "mysuni":
            for original in self.original_mysuni_data:
                if original.get("course_id") == course_id:
                    # 원본 데이터의 상세 정보로 업데이트
                    course.update({
                        "카테고리명": original.get("카테고리명"),
                        "채널명": original.get("채널명"),
                        "태그명": original.get("태그명"),
                        "난이도": original.get("난이도"),
                        "평점": original.get("평점"),
                        "이수자수": original.get("이수자수"),
                        "직무": original.get("직무", []),
                        "skillset": original.get("skillset", []),
                        "url": original.get("url")
                    })
                    break
                    
        # College 과정인 경우
        elif source == "college":
            for original in self.original_college_data:
                if original.get("course_id") == course_id:
                    # 원본 데이터의 상세 정보로 업데이트
                    course.update({
                        "학부": original.get("학부"),
                        "표준과정": original.get("표준과정"),
                        "사업별교육체계": original.get("사업별교육체계"),
                        "교육유형": original.get("교육유형"),
                        "학습유형": original.get("학습유형"),
                        "공개여부": original.get("공개여부"),
                        "특화직무": original.get("특화직무", []),
                        "추천직무": original.get("추천직무", []),
                        "공통필수직무": original.get("공통필수직무", []),
                        "url": original.get("url")
                    })
                    break
        
        return course
    
    def _get_preferred_education_source(self, query: str, user_profile: Dict, intent_analysis: Dict) -> str:
        """사용자의 교육과정 소스 선호도 감지"""
        # 1. 사용자 질문에서 명시적 언급 확인
        query_lower = query.lower()
        if 'mysuni' in query_lower or 'my suni' in query_lower:
            return 'mysuni'
        elif 'college' in query_lower or '컬리지' in query_lower:
            return 'college'
        
        # 2. 사용자 프로필에서 선호도 확인
        preferred_source = user_profile.get('preferred_education_source', '')
        if preferred_source in ['mysuni', 'college']:
            return preferred_source
        
        # 3. 의도 분석에서 선호도 확인
        intent_preferred = intent_analysis.get('preferred_source', '')
        if intent_preferred in ['mysuni', 'college']:
            return intent_preferred
        
        # 기본값: 선호도 없음
        return ''
    
    def _filter_by_preferred_source(self, courses: List[Dict], preferred_source: str) -> List[Dict]:
        """선호하는 교육과정 소스로 필터링"""
        if not preferred_source or not courses:
            return courses
        
        # 선호 소스의 과정들 먼저 추출
        preferred_courses = [course for course in courses if course.get('source') == preferred_source]
        
        # 선호 소스의 과정이 충분히 있으면 그것만 반환 (최소 3개)
        if len(preferred_courses) >= 3:
            self.logger.info(f"{preferred_source} 과정 {len(preferred_courses)}개로 필터링")
            return preferred_courses
        
        # 선호 소스의 과정이 부족하면 다른 소스도 포함하되 선호 소스 우선 정렬
        other_courses = [course for course in courses if course.get('source') != preferred_source]
        result = preferred_courses + other_courses[:7-len(preferred_courses)]  # 최대 7개까지
        
        self.logger.info(f"{preferred_source} 우선 필터링: {len(preferred_courses)}개 + 기타 {len(result)-len(preferred_courses)}개")
        return result