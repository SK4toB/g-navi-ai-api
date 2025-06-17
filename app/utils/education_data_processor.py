"""
교육과정 데이터 처리 및 벡터 데이터베이스 구축
College, mySUNI 데이터를 통합하여 VectorDB와 매핑 인덱스 생성
"""

import os
import json
import pandas as pd
import hashlib
import re
from typing import Dict, List, Any
from langchain.schema import Document
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.embeddings import CacheBackedEmbeddings
from langchain.storage import LocalFileStore
import logging

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EducationDataProcessor:
    """교육과정 데이터 처리 및 VectorDB 구축"""
    
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(__file__))  # app 디렉토리
        self.data_dir = os.path.join(self.base_dir, "data", "csv")
        self.storage_dir = os.path.join(self.base_dir, "storage")
        self.docs_dir = os.path.join(self.storage_dir, "docs")
        self.vector_stores_dir = os.path.join(self.storage_dir, "vector_stores")
        self.cache_dir = os.path.join(self.storage_dir, "cache")
        
        # 디렉토리 생성
        os.makedirs(self.docs_dir, exist_ok=True)
        os.makedirs(self.vector_stores_dir, exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # 임베딩 설정
        self.base_embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            dimensions=1536
        )
        self.cached_embeddings = CacheBackedEmbeddings.from_bytes_store(
            self.base_embeddings,
            LocalFileStore(os.path.join(self.cache_dir, "education_embedding_cache")),
            namespace="education_embeddings"
        )
        
    def process_all_education_data(self):
        """모든 교육과정 데이터 처리 및 VectorDB 구축"""
        logger.info("=== 교육과정 데이터 처리 시작 ===")
        
        # 1. 스킬 데이터 로드
        skill_data = self._load_skill_data()
        
        # 2. College 데이터 처리
        college_courses = self._process_college_data(skill_data)
        
        # 3. mySUNI 데이터 처리
        mysuni_courses = self._process_mysuni_data(skill_data)
        
        # 4. 스킬-교육과정 매핑 생성
        skill_mapping = self._create_skill_education_mapping(college_courses, mysuni_courses)
        
        # 5. 중복 과정 인덱스 생성
        deduplication_index = self._create_deduplication_index(college_courses, mysuni_courses)
        
        # 6. VectorDB용 문서 생성
        all_documents = self._create_vector_documents(college_courses, mysuni_courses)
        
        # 7. VectorDB 구축
        self._build_vector_database(all_documents)
        
        # 8. JSON 파일들 저장
        self._save_processed_data(
            college_courses, mysuni_courses, skill_mapping, 
            deduplication_index, all_documents
        )
        
        logger.info("=== 교육과정 데이터 처리 완료 ===")
        
    def _load_skill_data(self) -> pd.DataFrame:
        """스킬 데이터 로드"""
        skill_path = os.path.join(self.data_dir, "skill_set.csv")
        skill_df = pd.read_csv(skill_path, encoding='utf-8')
        logger.info(f"스킬 데이터 로드 완료: {len(skill_df)}개")
        return skill_df
        
    def _process_college_data(self, skill_data: pd.DataFrame) -> List[Dict]:
        """College 데이터 처리"""
        college_path = os.path.join(self.data_dir, "college.csv")
        college_df = pd.read_csv(college_path, encoding='utf-8')
        
        courses = []
        for idx, row in college_df.iterrows():
            course = {
                "course_id": f"COL-{idx:04d}",
                "course_name": row.get("교육과정명", ""),
                "source": "college",
                "학부": row.get("학부", ""),
                "표준과정": row.get("표준과정", ""),
                "사업별교육체계": row.get("사업별 교육체계", ""),
                "교육유형": row.get("교육유형", ""),
                "학습유형": row.get("학습유형", ""),
                "공개여부": row.get("공개여부", ""),
                "학습시간": self._parse_numeric(row.get("학습시간", 0)),
                "특화직무": self._parse_skill_list(row.get("특화 직무 및 Skill set", "")),
                "추천직무": self._parse_skill_list(row.get("추천 직무 및 Skill set", "")),
                "공통필수직무": self._parse_skill_list(row.get("공통 필수 직무 및 Skill set", "")),
            }
            
            # 스킬 매핑
            course["target_skills"] = self._map_skills_to_codes(
                course["특화직무"] + course["추천직무"] + course["공통필수직무"], 
                skill_data
            )
            
            courses.append(course)
            
        logger.info(f"College 데이터 처리 완료: {len(courses)}개")
        return courses
        
    def _process_mysuni_data(self, skill_data: pd.DataFrame) -> List[Dict]:
        """mySUNI 데이터 처리"""
        mysuni_path = os.path.join(self.data_dir, "mysuni.csv")
        mysuni_df = pd.read_csv(mysuni_path, encoding='utf-8')
        
        courses = []
        for idx, row in mysuni_df.iterrows():
            course = {
                "course_id": f"SUN-{idx:04d}",
                "card_name": row.get("카드명", ""),
                "source": "mysuni",
                "카테고리명": row.get("카테고리명", ""),
                "채널명": row.get("채널명", ""),
                "태그명": row.get("태그명", ""),
                "난이도": row.get("난이도", ""),
                "인정학습시간": self._parse_numeric(row.get("인정학습시간", 0)),
                "평점": self._parse_numeric(row.get("평점", 0)),
                "이수자수": str(row.get("이수자수", "0")),
                "직무": self._parse_skill_list(row.get("직무", "")),
                "skillset": self._parse_skill_list(row.get("Skill set", "")),
            }
            
            # 스킬 매핑
            course["target_skills"] = self._map_skills_to_codes(
                course["직무"] + course["skillset"], 
                skill_data
            )
            
            courses.append(course)
            
        logger.info(f"mySUNI 데이터 처리 완료: {len(courses)}개")
        return courses
        
    def _parse_skill_list(self, skill_string: str) -> List[str]:
        """스킬 문자열을 리스트로 파싱"""
        if pd.isna(skill_string) or not skill_string:
            return []
        
        # 세미콜론 또는 쉼표로 분리
        skills = re.split(r'[;,]', str(skill_string))
        return [skill.strip() for skill in skills if skill.strip()]
        
    def _parse_numeric(self, value) -> float:
        """숫자 값 파싱"""
        if pd.isna(value):
            return 0.0
        try:
            return float(value)
        except:
            return 0.0
            
    def _map_skills_to_codes(self, skill_names: List[str], skill_data: pd.DataFrame) -> List[str]:
        """스킬명을 스킬 코드로 매핑"""
        skill_codes = []
        
        for skill_name in skill_names:
            # 정확히 일치하는 스킬 찾기
            matches = skill_data[skill_data['Skill set'].str.contains(skill_name, na=False, case=False)]
            if not matches.empty:
                skill_code = matches.iloc[0]['코드']
                if skill_code not in skill_codes:
                    skill_codes.append(skill_code)
            else:
                # 부분 매칭 시도
                for _, row in skill_data.iterrows():
                    if skill_name.lower() in str(row['Skill set']).lower():
                        skill_code = row['코드']
                        if skill_code not in skill_codes:
                            skill_codes.append(skill_code)
                        break
                        
        return skill_codes
        
    def _create_skill_education_mapping(self, college_courses: List[Dict], mysuni_courses: List[Dict]) -> Dict:
        """스킬-교육과정 매핑 생성"""
        skill_mapping = {}
        
        # College 과정들을 스킬별로 분류
        for course in college_courses:
            for skill_code in course["target_skills"]:
                if skill_code not in skill_mapping:
                    skill_mapping[skill_code] = {
                        "skill_name": skill_code,
                        "college": {"specialized": [], "recommended": [], "common_required": []},
                        "mysuni": []
                    }
                
                # College 과정의 세분화 레벨 결정
                if course["특화직무"]:
                    category = "specialized"
                elif course["추천직무"]:
                    category = "recommended"
                else:
                    category = "common_required"
                    
                college_info = {
                    "course_id": course["course_id"],
                    "course_name": course["course_name"],
                    "학부": course["학부"],
                    "표준과정": course["표준과정"],
                    "학습시간": course["학습시간"]
                }
                
                skill_mapping[skill_code]["college"][category].append(college_info)
        
        # mySUNI 과정들을 스킬별로 분류
        for course in mysuni_courses:
            for skill_code in course["target_skills"]:
                if skill_code not in skill_mapping:
                    skill_mapping[skill_code] = {
                        "skill_name": skill_code,
                        "college": {"specialized": [], "recommended": [], "common_required": []},
                        "mysuni": []
                    }
                
                mysuni_info = {
                    "course_id": course["course_id"],
                    "card_name": course["card_name"],
                    "카테고리명": course["카테고리명"],
                    "채널명": course["채널명"],
                    "난이도": course["난이도"],
                    "인정학습시간": course["인정학습시간"],
                    "평점": course["평점"],
                    "이수자수": course["이수자수"]
                }
                
                skill_mapping[skill_code]["mysuni"].append(mysuni_info)
        
        logger.info(f"스킬-교육과정 매핑 생성 완료: {len(skill_mapping)}개 스킬")
        return skill_mapping
        
    def _create_deduplication_index(self, college_courses: List[Dict], mysuni_courses: List[Dict]) -> Dict:
        """중복 과정 인덱스 생성"""
        deduplication_index = {}
        
        # 과정명 정규화 함수
        def normalize_course_name(name: str) -> str:
            normalized = re.sub(r'[^\w\s]', '', name.lower())
            normalized = re.sub(r'\s+', ' ', normalized).strip()
            return normalized
        
        # 모든 과정의 정규화된 이름으로 그룹화
        course_groups = {}
        
        for course in college_courses + mysuni_courses:
            name = course.get("course_name", course.get("card_name", ""))
            normalized_name = normalize_course_name(name)
            
            if normalized_name not in course_groups:
                course_groups[normalized_name] = []
            course_groups[normalized_name].append(course)
        
        # 중복이 있는 과정들만 인덱스에 추가
        for normalized_name, courses in course_groups.items():
            if len(courses) > 1:
                platforms = list(set([course["source"] for course in courses]))
                
                course_info = []
                ratings = {}
                
                for course in courses:
                    if course["source"] == "college":
                        course_data = {
                            "platform": "College",
                            "course_id": course["course_id"],
                            "name": course["course_name"],
                            "primary": True,
                            "metadata": {
                                "학부": course["학부"],
                                "표준과정": course["표준과정"],
                                "학습시간": course["학습시간"]
                            }
                        }
                    else:  # mysuni
                        course_data = {
                            "platform": "mySUNI",
                            "course_id": course["course_id"],
                            "name": course["card_name"],
                            "primary": False,
                            "metadata": {
                                "평점": course["평점"],
                                "이수자수": course["이수자수"],
                                "난이도": course["난이도"],
                                "인정학습시간": course["인정학습시간"],
                                "카테고리명": course["카테고리명"],
                                "채널명": course["채널명"]
                            }
                        }
                        ratings["mysuni_rating"] = course["평점"]
                        ratings["mysuni_enrollments"] = course["이수자수"]
                    
                    course_info.append(course_data)
                
                deduplication_index[normalized_name] = {
                    "platforms": platforms,
                    "courses": course_info,
                    "ratings": ratings
                }
        
        logger.info(f"중복 과정 인덱스 생성 완료: {len(deduplication_index)}개 중복 그룹")
        return deduplication_index
        
    def _create_vector_documents(self, college_courses: List[Dict], mysuni_courses: List[Dict]) -> List[Document]:
        """VectorDB용 문서 생성"""
        documents = []
        
        # College 과정 문서 생성
        for course in college_courses:
            content = self._format_college_course_content(course)
            
            metadata = {
                "course_id": course["course_id"],
                "source": "college",
                "course_name": course["course_name"],
                "target_skills": course["target_skills"],
                "duration_hours": course["학습시간"],
                "department": course["학부"],
                "course_type": course["교육유형"],
                "학부": course["학부"],
                "표준과정": course["표준과정"]
            }
            
            # 스킬 관련성 결정
            if course["특화직무"]:
                metadata["skill_relevance"] = "specialized"
            elif course["추천직무"]:
                metadata["skill_relevance"] = "recommended"
            else:
                metadata["skill_relevance"] = "common_required"
            
            documents.append(Document(page_content=content, metadata=metadata))
        
        # mySUNI 과정 문서 생성
        for course in mysuni_courses:
            content = self._format_mysuni_course_content(course)
            
            metadata = {
                "course_id": course["course_id"],
                "source": "mysuni",
                "card_name": course["card_name"],
                "target_skills": course["target_skills"],
                "카테고리명": course["카테고리명"],
                "채널명": course["채널명"],
                "난이도": course["난이도"],
                "인정학습시간": course["인정학습시간"],
                "평점": course["평점"],
                "이수자수": course["이수자수"],
                "skill_relevance": "general"
            }
            
            documents.append(Document(page_content=content, metadata=metadata))
        
        logger.info(f"VectorDB 문서 생성 완료: {len(documents)}개")
        return documents
        
    def _format_college_course_content(self, course: Dict) -> str:
        """College 과정 내용 포맷팅"""
        content = f"""
교육과정명: {course['course_name']}
학부: {course['학부']}
표준과정: {course['표준과정']}
교육유형: {course['교육유형']}
학습유형: {course['학습유형']}
학습시간: {course['학습시간']}시간
공개여부: {course['공개여부']}

특화 직무: {'; '.join(course['특화직무'])}
추천 직무: {'; '.join(course['추천직무'])}
공통 필수 직무: {'; '.join(course['공통필수직무'])}

대상 스킬: {'; '.join(course['target_skills'])}
        """.strip()
        
        return content
        
    def _format_mysuni_course_content(self, course: Dict) -> str:
        """mySUNI 과정 내용 포맷팅"""
        content = f"""
카드명: {course['card_name']}
카테고리: {course['카테고리명']}
채널명: {course['채널명']}
난이도: {course['난이도']}
인정학습시간: {course['인정학습시간']}시간
평점: {course['평점']}/5.0
이수자수: {course['이수자수']}명

직무: {'; '.join(course['직무'])}
스킬셋: {'; '.join(course['skillset'])}

대상 스킬: {'; '.join(course['target_skills'])}

온라인 자율학습 과정
언제든 수강 가능
        """.strip()
        
        return content
        
    def _build_vector_database(self, documents: List[Document]):
        """VectorDB 구축"""
        education_vector_dir = os.path.join(self.vector_stores_dir, "education_courses")
        
        # 기존 VectorDB 제거
        if os.path.exists(education_vector_dir):
            import shutil
            shutil.rmtree(education_vector_dir)
        
        try:
            from langchain_community.vectorstores.utils import filter_complex_metadata
            
            # 복잡한 메타데이터 필터링
            filtered_documents = filter_complex_metadata(documents)
            logger.info(f"메타데이터 필터링 완료: {len(filtered_documents)}개 문서")
            
            # 새 VectorDB 생성
            vectorstore = Chroma.from_documents(
                documents=filtered_documents,
                embedding=self.cached_embeddings,
                persist_directory=education_vector_dir,
                collection_name="education_courses"
            )
            
            logger.info(f"VectorDB 구축 완료: {education_vector_dir}")
            
        except Exception as e:
            logger.error(f"VectorDB 구축 실패: {e}")
            logger.info("VectorDB 없이도 JSON 기반 검색이 가능합니다.")
            # VectorDB 생성에 실패해도 나머지 처리는 계속 진행
        
    def _save_processed_data(self, college_courses: List[Dict], mysuni_courses: List[Dict], 
                           skill_mapping: Dict, deduplication_index: Dict, documents: List[Document]):
        """처리된 데이터를 JSON 파일로 저장"""
        
        # 1. 교육과정 통합 문서
        education_docs = []
        for doc in documents:
            education_docs.append({
                "page_content": doc.page_content,
                "metadata": doc.metadata
            })
        
        with open(os.path.join(self.docs_dir, "education_courses.json"), "w", encoding="utf-8") as f:
            json.dump(education_docs, f, ensure_ascii=False, indent=2)
        
        # 2. 스킬-교육과정 매핑
        with open(os.path.join(self.docs_dir, "skill_education_mapping.json"), "w", encoding="utf-8") as f:
            json.dump(skill_mapping, f, ensure_ascii=False, indent=2)
        
        # 3. College 상세 정보
        with open(os.path.join(self.docs_dir, "college_courses_detailed.json"), "w", encoding="utf-8") as f:
            json.dump(college_courses, f, ensure_ascii=False, indent=2)
        
        # 4. mySUNI 상세 정보
        with open(os.path.join(self.docs_dir, "mysuni_courses_detailed.json"), "w", encoding="utf-8") as f:
            json.dump(mysuni_courses, f, ensure_ascii=False, indent=2)
        
        # 5. 중복 과정 인덱스
        with open(os.path.join(self.docs_dir, "course_deduplication_index.json"), "w", encoding="utf-8") as f:
            json.dump(deduplication_index, f, ensure_ascii=False, indent=2)
        
        logger.info("처리된 데이터 저장 완료")
    
    def _create_vectordb(self, documents: List[Document]):
        """OpenAI 임베딩을 사용하여 VectorDB 생성"""
        try:
            from langchain_openai import OpenAIEmbeddings
            from langchain_chroma import Chroma
            from langchain_community.vectorstores.utils import filter_complex_metadata
            import shutil
            
            logger.info("OpenAI 임베딩을 사용하여 VectorDB 생성 중...")
            
            # OpenAI 임베딩 설정
            embeddings = OpenAIEmbeddings(
                model="text-embedding-3-small",
                openai_api_key=os.getenv("OPENAI_API_KEY")
            )
            
            # VectorDB 저장 경로
            persist_directory = os.path.join(self.vector_stores_dir, "education_courses")
            
            # 기존 VectorDB 디렉토리가 있다면 삭제
            if os.path.exists(persist_directory):
                shutil.rmtree(persist_directory)
                logger.info("기존 VectorDB 디렉토리 삭제됨")
            
            # LangChain의 내장 필터를 사용하여 복잡한 메타데이터 제거
            filtered_documents = filter_complex_metadata(documents)
            
            logger.info(f"메타데이터 필터링 완료: {len(filtered_documents)}개 문서")
            
            # VectorDB 생성
            vectorstore = Chroma.from_documents(
                documents=filtered_documents,
                embedding=embeddings,
                persist_directory=persist_directory,
                collection_name="education_courses"
            )
            
            logger.info(f"VectorDB 생성 완료: {persist_directory}")
            logger.info(f"총 {len(filtered_documents)}개의 문서가 저장되었습니다.")
            
            # 테스트 검색
            test_results = vectorstore.similarity_search("AI 교육", k=3)
            logger.info(f"테스트 검색 결과: {len(test_results)}개 문서 반환")
            
        except ImportError as e:
            logger.warning(f"VectorDB 생성을 위한 라이브러리가 없습니다: {e}")
        except Exception as e:
            if "api_key" in str(e).lower():
                logger.warning("OpenAI API 키가 설정되지 않았습니다. VectorDB 생성을 건너뜁니다.")
                logger.info("환경변수 OPENAI_API_KEY를 설정하고 다시 실행하면 VectorDB가 생성됩니다.")
            else:
                logger.error(f"VectorDB 생성 중 오류: {e}")

def main():
    """메인 실행 함수"""
    processor = EducationDataProcessor()
    processor.process_all_education_data()

if __name__ == "__main__":
    main()
