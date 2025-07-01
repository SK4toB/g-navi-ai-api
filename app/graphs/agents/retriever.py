# app/graphs/agents/retriever.py

import os
import json
import re
import requests
import logging
from typing import Dict, List, Any, Optional
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document
from datetime import datetime, timedelta

from dotenv import load_dotenv
load_dotenv()

# ==================== 📂 경로 설정 (수정 필요시 여기만 변경) ====================
class PathConfig:
    """
    모든 경로 설정을 한 곳에서 관리하는 클래스
    경로 변경이 필요할 때는 이 부분만 수정하면 됩니다.
    """
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # app 디렉토리
    
    # 📄 문서 경로 (JSON 데이터 파일들) - 폴백용
    CAREER_DOCS = "../../storage/docs/career_history.json"                    # 커리어 히스토리 원본 데이터
    EDUCATION_DOCS = "../../storage/docs/education_courses.json"              # 교육과정 문서 데이터
    SKILL_MAPPING = "../../storage/docs/skill_education_mapping.json"         # 스킬-교육과정 매핑 테이블
    COURSE_DEDUPLICATION = "../../storage/docs/course_deduplication_index.json"  # 과정 중복 제거 인덱스
    COMPANY_VISION = "../../storage/docs/company_vision.json"                 # 회사 비전 및 가치 데이터
    MYSUNI_DETAILED = "../../storage/docs/mysuni_courses_detailed.json"       # mySUNI 과정 상세 정보
    COLLEGE_DETAILED = "../../storage/docs/college_courses_detailed.json"     # College 과정 상세 정보
    
    @classmethod
    def get_abs_path(cls, relative_path: str) -> str:
        """상대 경로를 절대 경로로 변환"""
        return os.path.abspath(os.path.join(os.path.dirname(__file__), relative_path))

# ==================== 📂 경로 설정 끝 ====================

class ChromaK8sClient:
    """K8s 내부 ChromaDB 클라이언트"""
    
    def __init__(self, use_external: bool = False):
        """
        ChromaDB 클라이언트 초기화
        
        Args:
            use_external: True면 외부 접속, False면 k8s 내부 접속
        """
        self.use_external = use_external
        
        if use_external:
            # 외부 접속 (개발환경)
            self.base_url = "https://sk-gnavi4.skala25a.project.skala-ai.com/vector/api/v2"
        else:
            # k8s 내부 접속 (운영환경)
            self.base_url = "http://chromadb-1.sk-team-04.svc.cluster.local:8000/api/v2"
        
        self.tenant = "default_tenant"
        self.database = "default_database"
        self.collections_url = f"{self.base_url}/tenants/{self.tenant}/databases/{self.database}/collections"
        
        # 컬렉션 정보
        self.career_collection_name = "gnavi4_career_history_prod"
        self.education_collection_name = "gnavi4_education_prod"
        self.career_collection_id = None
        self.education_collection_id = None
        
        # 임베딩 설정
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            dimensions=1536
        )
        
        # 헤더 설정
        self.headers = {"Content-Type": "application/json"}
        self.logger = logging.getLogger(__name__)
        
        # 초기화
        self._init_collections()
    
    def _init_collections(self):
        """컬렉션 ID 초기화"""
        try:
            collections = self._get_collections_list()
            if collections:
                for collection in collections:
                    name = collection.get('name')
                    collection_id = collection.get('id')
                    
                    if name == self.career_collection_name:
                        self.career_collection_id = collection_id
                        self.logger.info(f"경력 컬렉션 ID 로드: {collection_id}")
                    elif name == self.education_collection_name:
                        self.education_collection_id = collection_id
                        self.logger.info(f"교육과정 컬렉션 ID 로드: {collection_id}")
            
            connection_mode = "외부" if self.use_external else "k8s 내부"
            print(f"✅ [ChromaDB {connection_mode} 접속] 초기화 완료")
            
        except Exception as e:
            self.logger.error(f"ChromaDB 컬렉션 초기화 실패: {e}")
            print(f"❌ [ChromaDB 초기화 실패] {e}")
    
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
                self.logger.error(f"컬렉션 목록 조회 실패: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"컬렉션 목록 조회 오류: {e}")
            return None
    
    def search_career_documents(self, query: str, k: int = 3) -> List[Document]:
        """경력 문서 검색"""
        if not self.career_collection_id:
            self.logger.warning("경력 컬렉션을 찾을 수 없습니다")
            return []
        
        try:
            # 임베딩 생성
            query_embedding = self.embeddings.embed_query(query)
            
            # 검색 요청
            search_data = {
                "query_embeddings": [query_embedding],
                "n_results": k,
                "include": ["documents", "metadatas"]
            }
            
            search_url = f"{self.collections_url}/{self.career_collection_id}/query"
            response = requests.post(search_url, headers=self.headers, json=search_data, timeout=30)
            
            if response.status_code == 200:
                results = response.json()
                documents = results.get('documents', [[]])
                metadatas = results.get('metadatas', [[]])
                
                # Document 객체로 변환
                docs = []
                for i, doc_content in enumerate(documents[0] if documents else []):
                    metadata = metadatas[0][i] if metadatas and metadatas[0] and i < len(metadatas[0]) else {}
                    docs.append(Document(page_content=doc_content, metadata=metadata))
                
                return docs
            else:
                self.logger.error(f"경력 검색 실패: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            self.logger.error(f"경력 검색 중 오류: {e}")
            return []
    
    def search_education_documents(self, query: str, k: int = 3) -> List[Document]:
        """교육과정 문서 검색"""
        if not self.education_collection_id:
            self.logger.warning("교육과정 컬렉션을 찾을 수 없습니다")
            return []
        
        try:
            # 임베딩 생성
            query_embedding = self.embeddings.embed_query(query)
            
            # 검색 요청
            search_data = {
                "query_embeddings": [query_embedding],
                "n_results": k,
                "include": ["documents", "metadatas"]
            }
            
            search_url = f"{self.collections_url}/{self.education_collection_id}/query"
            response = requests.post(search_url, headers=self.headers, json=search_data, timeout=30)
            
            if response.status_code == 200:
                results = response.json()
                documents = results.get('documents', [[]])
                metadatas = results.get('metadatas', [[]])
                
                # Document 객체로 변환
                docs = []
                for i, doc_content in enumerate(documents[0] if documents else []):
                    metadata = metadatas[0][i] if metadatas and metadatas[0] and i < len(metadatas[0]) else {}
                    docs.append(Document(page_content=doc_content, metadata=metadata))
                
                return docs
            else:
                self.logger.error(f"교육과정 검색 실패: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            self.logger.error(f"교육과정 검색 중 오류: {e}")
            return []
    
    def get_collection_count(self, collection_type: str = "career") -> Optional[int]:
        """컬렉션 문서 개수 조회"""
        if collection_type == "career":
            collection_id = self.career_collection_id
        elif collection_type == "education":
            collection_id = self.education_collection_id
        else:
            return None
        
        if not collection_id:
            return None
        
        try:
            count_url = f"{self.collections_url}/{collection_id}/count"
            response = requests.get(count_url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"{collection_type} 컬렉션 카운트 조회 실패: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"{collection_type} 컬렉션 카운트 조회 중 오류: {e}")
            return None

class CareerEnsembleRetrieverAgent:
    """
    🔍 커리어 앙상블 리트리버 에이전트 (K8s ChromaDB 연동)
    
    K8s 내부 또는 외부 ChromaDB에 연결하여 커리어 사례와 교육과정을
    효과적으로 검색합니다.
    
    📊 검색 결과:
    - 커리어 사례: 최대 3개까지 검색
    - 교육과정: 최대 3개까지 검색
    """
    def __init__(self, use_external_chroma: bool = None):
        """
        CareerEnsembleRetrieverAgent 초기화
        
        Args:
            use_external_chroma: True면 외부 접속, False면 k8s 내부 접속, None이면 환경변수 확인
        """
        # 환경변수로 접속 방식 결정
        if use_external_chroma is None:
            use_external_chroma = os.getenv("CHROMA_USE_EXTERNAL", "false").lower() == "true"
        
        self.logger = logging.getLogger(__name__)
        
        # ChromaDB 클라이언트 초기화
        self.chroma_client = ChromaK8sClient(use_external=use_external_chroma)
        
        # 문서 경로 설정 (폴백용)
        self.education_docs_path = PathConfig.get_abs_path(PathConfig.EDUCATION_DOCS)
        self.skill_mapping_path = PathConfig.get_abs_path(PathConfig.SKILL_MAPPING)
        self.deduplication_index_path = PathConfig.get_abs_path(PathConfig.COURSE_DEDUPLICATION)
        self.company_vision_path = PathConfig.get_abs_path(PathConfig.COMPANY_VISION)
        
        # 지연 로딩 속성
        self.skill_education_mapping = None
        self.course_deduplication_index = None
        self.company_vision_data = None
        self.original_mysuni_data = None
        self.original_college_data = None
        
        connection_mode = "외부" if use_external_chroma else "k8s 내부"
        print(f"✅ [Retriever Agent {connection_mode} 모드] 초기화 완료")

    def retrieve(self, query: str, k: int = 3):
        """ChromaDB에서 경력 사례 검색 + 시간 기반 필터링"""
        print(f"🔍 [커리어 사례 검색] 시작 - '{query}'")
        
        # ChromaDB에서 검색
        docs = self.chroma_client.search_career_documents(query, k=k*2)  # 필터링을 위해 더 많이 가져옴
        
        if not docs:
            print(f"❌ [커리어 사례 검색] 결과 없음")
            return self._fallback_career_search(query, k)
        
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
            
            # 시간 기반 필터링
            filtered_docs = self._filter_docs_by_time(docs, min_year, focus_on_start_year)
            final_docs = filtered_docs[:k]
        else:
            final_docs = docs[:k]
        
        # 회사 비전 정보를 결과에 추가 (커리어 관련 질문인 경우)
        career_keywords = ['커리어', '진로', '성장', '발전', '목표', '방향', '계획', '비전', '미래', '회사', '조직']
        if any(keyword in query.lower() for keyword in career_keywords):
            company_vision = self._load_company_vision()
            if company_vision:
                vision_content = self._format_company_vision_for_context(company_vision)
                vision_doc = Document(
                    page_content=vision_content,
                    metadata={"type": "company_vision", "source": "company_vision.json"}
                )
                final_docs.append(vision_doc)
                self.logger.info("회사 비전 정보가 검색 결과에 추가되었습니다.")
        
        print(f"✅ [커리어 사례 검색] 완료: {len(final_docs)}개 결과 반환")
        return final_docs
    
    def _filter_docs_by_time(self, docs: List[Document], min_year: int, focus_on_start_year: bool) -> List[Document]:
        """시간 기반 문서 필터링"""
        filtered_docs = []
        
        for doc in docs:
            try:
                metadata = doc.metadata or {}
                
                if focus_on_start_year:
                    # 신입/입사 관련 쿼리인 경우: 시작 연도 기준
                    start_year = metadata.get('activity_start_year')
                    if start_year and isinstance(start_year, int) and start_year >= min_year:
                        filtered_docs.append(doc)
                        self.logger.debug(f"포함: {start_year}년 시작 활동")
                else:
                    # 일반 최근 쿼리인 경우: 최근 활동이 있었던 직원들 중에서
                    activity_years = metadata.get('activity_years_list', [])
                    if activity_years and isinstance(activity_years, list):
                        recent_activity_years = [year for year in activity_years 
                                               if isinstance(year, int) and year >= min_year]
                        if recent_activity_years:
                            filtered_docs.append(doc)
                            self.logger.debug(f"포함: 최근 활동 연도 {recent_activity_years}")
                            continue
                    
                    # 폴백: 종료 연도가 최근인지 확인
                    end_year = metadata.get('activity_end_year')
                    if end_year and isinstance(end_year, int) and end_year >= min_year:
                        filtered_docs.append(doc)
                        self.logger.debug(f"포함: {end_year}년 종료 활동")
                        
            except Exception as e:
                self.logger.warning(f"문서 연도 추출 실패: {e}")
                continue
        
        self.logger.info(f"시간 필터링 완료: 전체 {len(docs)}개 → 필터링된 {len(filtered_docs)}개 문서")
        return filtered_docs
    
    def _fallback_career_search(self, query: str, k: int = 3) -> List[Document]:
        """ChromaDB 검색 실패 시 폴백 검색"""
        self.logger.warning("ChromaDB 검색 실패, JSON 파일 폴백 검색 시도")
        
        try:
            career_docs_path = PathConfig.get_abs_path(PathConfig.CAREER_DOCS)
            with open(career_docs_path, 'r', encoding='utf-8') as f:
                json_docs = json.load(f)
            
            # 간단한 키워드 매칭
            query_keywords = query.lower().split()
            matching_docs = []
            
            for doc_data in json_docs:
                content = doc_data.get('page_content', '').lower()
                score = sum(1 for keyword in query_keywords if keyword in content)
                
                if score > 0:
                    doc = Document(
                        page_content=doc_data['page_content'],
                        metadata=doc_data.get('metadata', {})
                    )
                    matching_docs.append((doc, score))
            
            # 점수순 정렬 후 k개 반환
            matching_docs.sort(key=lambda x: x[1], reverse=True)
            return [doc for doc, _ in matching_docs[:k]]
            
        except Exception as e:
            self.logger.error(f"폴백 검색도 실패: {e}")
            return []
    
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
        
        # 특정 연도 패턴 매칭
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

    def search_education_courses(self, query: str, user_profile: Dict, intent_analysis: Dict) -> Dict:
        """교육과정 검색 메인 함수 - ChromaDB 우선, 폴백으로 JSON 검색"""
        print(f"🔍 [교육과정 검색] 시작 - '{query}'")
        
        try:
            # ChromaDB에서 검색 시도
            docs = self.chroma_client.search_education_documents(query, k=6)  # 더 많이 가져와서 필터링
            
            if docs:
                # ChromaDB 결과를 Dict 형태로 변환
                courses = [self._doc_to_course_dict(doc) for doc in docs]
                
                # 원본 데이터로 상세 정보 보강
                courses = [self._enrich_course_with_original_data(course) for course in courses]
                
                # 사용자 선호도 적용
                preferred_source = self._get_preferred_education_source(query, user_profile, intent_analysis)
                if preferred_source:
                    courses = self._filter_by_preferred_source(courses, preferred_source)
                
                # 중복 제거
                courses = self._deduplicate_courses(courses)
                
                # 최종 3개로 제한
                courses = courses[:3]
                
                print(f"✅ [교육과정 검색] ChromaDB 검색 완료: {len(courses)}개 과정 반환")
                
            else:
                # ChromaDB 검색 실패 시 폴백
                print(f"⚠️ [교육과정 검색] ChromaDB 검색 실패, JSON 폴백 검색")
                courses = self._fallback_education_search(query, user_profile, intent_analysis)
            
            # 결과 분석 및 학습 경로 생성
            course_analysis = self._analyze_course_recommendations(courses)
            learning_path = self._generate_learning_path(courses)
            
            return {
                "recommended_courses": courses,
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
    
    def _fallback_education_search(self, query: str, user_profile: Dict, intent_analysis: Dict) -> List[Dict]:
        """ChromaDB 검색 실패 시 JSON 폴백 검색"""
        try:
            # 기존 로직과 동일하게 리소스 로드
            self._load_education_resources()
            
            # 스킬 기반 필터링
            skill_based_courses = self._skill_based_course_filter(user_profile, intent_analysis)
            
            # JSON에서 의미적 검색
            semantic_matches = self._search_from_json_documents(query, skill_based_courses)
            
            # 선호도 필터링
            preferred_source = self._get_preferred_education_source(query, user_profile, intent_analysis)
            if preferred_source:
                semantic_matches = self._filter_by_preferred_source(semantic_matches, preferred_source)
            
            # 중복 제거 및 3개로 제한
            deduplicated_courses = self._deduplicate_courses(semantic_matches)[:3]
            
            return deduplicated_courses
            
        except Exception as e:
            self.logger.error(f"폴백 교육과정 검색 실패: {e}")
            return []
    
    def _doc_to_course_dict(self, doc: Document) -> Dict:
        """ChromaDB Document를 과정 딕셔너리로 변환"""
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
            "url": metadata.get("url")
        }
    
    # 기존 메소드들 유지 (스킬 기반 필터링, 중복 제거 등)
    def _load_education_resources(self):
        """교육과정 리소스 지연 로딩"""
        if self.skill_education_mapping is None:
            self._load_skill_education_mapping()
        if self.course_deduplication_index is None:
            self._load_deduplication_index()
    
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
    
    def _skill_based_course_filter(self, user_profile: Dict, intent_analysis: Dict) -> List[Dict]:
        """스킬 기반 1차 필터링"""
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
                
                # College 과정 추가
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
        
        if "skills" in user_profile:
            skills.extend(user_profile["skills"])
        
        if "career_history" in user_profile:
            for career in user_profile["career_history"]:
                if "skills" in career:
                    skills.extend(career["skills"])
        
        return list(set(skills))
    
    def _search_from_json_documents(self, query: str, filtered_courses: List[Dict]) -> List[Dict]:
        """JSON 문서에서 직접 검색"""
        try:
            with open(self.education_docs_path, "r", encoding="utf-8") as f:
                all_docs = json.load(f)
        except FileNotFoundError:
            self.logger.warning("교육과정 문서 파일이 없습니다.")
            return filtered_courses[:3] if filtered_courses else []
        
        # 필터링된 과정이 있으면 우선 활용
        if filtered_courses:
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
                return matching_docs[:3]
        
        # 키워드 기반 검색
        query_keywords = query.lower().split()
        matching_docs = []
        
        for doc in all_docs:
            content = doc.get("page_content", "").lower()
            score = sum(1 for keyword in query_keywords if keyword in content)
            
            if score > 0:
                course_dict = self._doc_to_course_dict_from_json(doc)
                course_dict["match_score"] = score
                matching_docs.append(course_dict)
        
        matching_docs.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        return matching_docs[:3]
    
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
            "url": metadata.get("url")
        }
    
    def _get_preferred_education_source(self, query: str, user_profile: Dict, intent_analysis: Dict) -> str:
        """사용자의 교육과정 소스 선호도 감지"""
        query_lower = query.lower()
        if 'mysuni' in query_lower or 'my suni' in query_lower:
            return 'mysuni'
        elif 'college' in query_lower or '컬리지' in query_lower:
            return 'college'
        
        preferred_source = user_profile.get('preferred_education_source', '')
        if preferred_source in ['mysuni', 'college']:
            return preferred_source
        
        intent_preferred = intent_analysis.get('preferred_source', '')
        if intent_preferred in ['mysuni', 'college']:
            return intent_preferred
        
        return ''
    
    def _filter_by_preferred_source(self, courses: List[Dict], preferred_source: str) -> List[Dict]:
        """선호하는 교육과정 소스로 필터링"""
        if not preferred_source or not courses:
            return courses
        
        preferred_courses = [course for course in courses if course.get('source') == preferred_source]
        
        if len(preferred_courses) >= 3:
            self.logger.info(f"{preferred_source} 과정 {len(preferred_courses)}개로 필터링")
            return preferred_courses
        
        other_courses = [course for course in courses if course.get('source') != preferred_source]
        result = preferred_courses + other_courses[:7-len(preferred_courses)]
        
        self.logger.info(f"{preferred_source} 우선 필터링: {len(preferred_courses)}개 + 기타 {len(result)-len(preferred_courses)}개")
        return result
    
    def _deduplicate_courses(self, courses: List[Dict]) -> List[Dict]:
        """중복 과정 제거"""
        if not courses:
            return []
        
        deduplicated = []
        seen_courses = set()
        
        def sort_priority(course):
            source_priority = 0 if course.get("source") == "college" else 1
            
            if course.get("source") == "college":
                relevance = course.get("skill_relevance", "")
                if relevance == "specialized":
                    relevance_priority = 0
                elif relevance == "recommended":
                    relevance_priority = 1
                else:
                    relevance_priority = 2
            else:
                rating = course.get("평점", 0)
                try:
                    rating = float(rating) if rating else 0
                except:
                    rating = 0
                relevance_priority = 5 - rating
            
            return (source_priority, relevance_priority)
        
        sorted_courses = sorted(courses, key=sort_priority)
        
        for course in sorted_courses:
            course_signature = self._generate_course_signature(course)
            
            if course_signature not in seen_courses:
                if course_signature in self.course_deduplication_index:
                    duplicate_info = self.course_deduplication_index[course_signature]
                    
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
                        course["mysuni_alternative"] = {"available": False}
                    
                    course["alternative_platforms"] = duplicate_info.get("platforms", [])
                else:
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
        
        normalized_name = re.sub(r'[^\w\s]', '', name)
        normalized_name = re.sub(r'\s+', ' ', normalized_name)
        
        return f"{normalized_name}_{','.join(skills)}"
    
    def _find_mysuni_duplicate(self, duplicate_info: Dict, all_courses: List[Dict]) -> Dict:
        """중복 정보에서 mySUNI 과정 찾기"""
        mysuni_course_info = None
        for course_info in duplicate_info.get("courses", []):
            if course_info.get("platform") == "mySUNI":
                course_id = course_info.get("course_id")
                for course in all_courses:
                    if (course.get("source") == "mysuni" and 
                        course.get("course_id") == course_id):
                        mysuni_course_info = course
                        break
                break
        
        return mysuni_course_info
    
    def _analyze_course_recommendations(self, courses: List[Dict]) -> Dict:
        """추천 과정 분석 결과 생성"""
        if not courses:
            return {"message": "추천할 교육과정이 없습니다."}
        
        college_courses = [c for c in courses if c.get("source") == "college"]
        mysuni_courses = [c for c in courses if c.get("source") == "mysuni"]
        
        specialized_count = len([c for c in college_courses if c.get("skill_relevance") == "specialized"])
        recommended_count = len([c for c in college_courses if c.get("skill_relevance") == "recommended"])
        required_count = len([c for c in college_courses if c.get("skill_relevance") == "common_required"])
        
        college_with_mysuni_alt = len([c for c in college_courses 
                                      if c.get("mysuni_alternative", {}).get("available")])
        
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
        
        required_courses = [c for c in courses if c.get("skill_relevance") == "common_required"]
        if required_courses:
            path.append({
                "step": 1,
                "level": "기초/필수",
                "courses": required_courses[:2],
                "description": "기본 지식 습득을 위한 필수 과정"
            })
        
        recommended_courses = [c for c in courses if c.get("skill_relevance") == "recommended"]
        if recommended_courses:
            path.append({
                "step": 2,
                "level": "확장/응용",
                "courses": recommended_courses[:3],
                "description": "관련 기술 확장을 위한 추천 과정"
            })
        
        specialized_courses = [c for c in courses if c.get("skill_relevance") == "specialized"]
        if specialized_courses:
            path.append({
                "step": 3,
                "level": "전문/심화",
                "courses": specialized_courses[:2],
                "description": "전문성 강화를 위한 특화 과정"
            })
        
        mysuni_courses = [c for c in courses if c.get("source") == "mysuni"]
        if mysuni_courses:
            path.append({
                "step": "보완",
                "level": "온라인/자율",
                "courses": mysuni_courses[:3],
                "description": "온라인으로 학습 가능한 보완 과정"
            })
        
        return path
    
    def _load_original_course_data(self):
        """원본 교육과정 상세 데이터 로드"""
        if not hasattr(self, 'original_mysuni_data'):
            try:
                mysuni_path = PathConfig.get_abs_path(PathConfig.MYSUNI_DETAILED)
                with open(mysuni_path, "r", encoding="utf-8") as f:
                    self.original_mysuni_data = json.load(f)
                self.logger.info(f"mySUNI 원본 데이터 로드 완료: {len(self.original_mysuni_data)}개")
            except FileNotFoundError:
                self.logger.warning("mySUNI 원본 데이터 파일을 찾을 수 없습니다.")
                self.original_mysuni_data = []
                
        if not hasattr(self, 'original_college_data'):
            try:
                college_path = PathConfig.get_abs_path(PathConfig.COLLEGE_DETAILED)
                with open(college_path, "r", encoding="utf-8") as f:
                    self.original_college_data = json.load(f)
                self.logger.info(f"College 원본 데이터 로드 완료: {len(self.original_college_data)}개")
            except FileNotFoundError:
                self.logger.warning("College 원본 데이터 파일을 찾을 수 없습니다.")
                self.original_college_data = []

    def _enrich_course_with_original_data(self, course: Dict) -> Dict:
        """원본 데이터로 과정 정보 보강"""
        self._load_original_course_data()
        
        course_id = course.get("course_id")
        source = course.get("source")
        
        if not course_id:
            return course
            
        if source == "mysuni":
            for original in self.original_mysuni_data:
                if original.get("course_id") == course_id:
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
                    
        elif source == "college":
            for original in self.original_college_data:
                if original.get("course_id") == course_id:
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