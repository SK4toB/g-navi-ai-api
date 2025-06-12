# csv_to_vector_and_docs.py
# csv 파일을 읽어 경력 데이터를 그룹핑하고 docs과 vectordb를 한번에 생성하는 도구

"""
기존 VectorDB의 그룹핑 문제를 진단하고 수정 (통합 생성도구)

이 도구는 경력 데이터를 개인별로 그룹핑하고, 
각 개인의 경력 타임라인을 통합하여 문서로 생성합니다.
이후, 생성된 문서를 ChromaDB에 저장하여 검색 및 분석이 가능하도록 합니다.

이 도구는 다음과 같은 기능을 포함합니다:
1. CSV 파일에서 경력 데이터를 로드하고 개인별로 그룹핑합니다.
2. 각 개인의 경력 데이터를 통합하여 연속적인 타임라인을 생성합니다.
3. 생성된 타임라인을 기반으로 포괄적이고 정확한 메타데이터를 생성합니다.
4. 생성된 문서를 ChromaDB에 저장합니다.

주의 : readonly 오류 발생시, vector_stores/career_data 디렉토리를 삭제하고 다시 실행하세요.
"""

import os
import shutil
import json
import pandas as pd
import logging
from typing import List, Dict, Any, Optional
from langchain.schema import Document
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.embeddings import CacheBackedEmbeddings
from langchain.storage import LocalFileStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()


class VectorDBGroupingFixer:
    """VectorDB 그룹핑 문제 자동 수정 도구"""
    
    def __init__(self, 
                 csv_path: str = "data/csv/career_history.csv",
                 skillset_csv_path: str = "data/csv/skill_set.csv",
                 persist_directory: str = "storage/vector_stores/career_data",
                 cache_directory: str = "storage/cache/embedding_cache",
                 docs_json_path: str = "storage/docs/career_history.json"):
        
        self.csv_path = os.path.abspath(csv_path)
        self.skillset_csv_path = os.path.abspath(skillset_csv_path)
        self.persist_directory = os.path.abspath(persist_directory)
        self.cache_directory = os.path.abspath(cache_directory)
        self.docs_json_path = os.path.abspath(docs_json_path)
        
        # 로깅 설정
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # 임베딩 설정
        self.base_embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            dimensions=1536
        )
        self.cached_embeddings = CacheBackedEmbeddings.from_bytes_store(
            self.base_embeddings,
            LocalFileStore(cache_directory),
            namespace="career_embeddings"
        )
        
        # 텍스트 스플리터
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,
            chunk_overlap=150,
            separators=["\n=== 경력 ", "\n프로젝트:", "\n주요업무:", "\n역할:", "\n\n", "\n", ": ", " "],
            length_function=len
        )
        
        # 스킬셋 매핑
        self.skillset_mapping = {}
        self._load_skillset_mapping()
    
    def _load_skillset_mapping(self):
        """스킬셋 매핑 로드"""
        try:
            if os.path.exists(self.skillset_csv_path):
                skill_df = pd.read_csv(self.skillset_csv_path, encoding='utf-8')
                mapping = {}
                for _, row in skill_df.iterrows():
                    if pd.notna(row.get('코드')):
                        code = str(row['코드']).strip()
                        mapping[code] = {
                            'skill_name': str(row.get('Skill set', '')).strip(),
                            'job_category': str(row.get('Skillset-직무연계', '')).strip(),
                            'description': str(row.get('Skill set', '')).strip()
                        }
                self.skillset_mapping = mapping
                self.logger.info(f"스킬셋 매핑 완료: {len(mapping)}개")
        except Exception as e:
            self.logger.warning(f"스킬셋 매핑 로드 실패: {e}")
    
    def load_and_group_career_data(self) -> Dict[str, pd.DataFrame]:
        """경력 데이터를 로드하고 개인별로 올바르게 그룹핑"""
        try:
            # CSV 로드
            df = pd.read_csv(self.csv_path, encoding='utf-8')
            self.logger.info(f"경력 데이터 로드: {len(df)}행")
            
            # 데이터 정제
            df = df.dropna(subset=['고유번호'])
            df['고유번호'] = df['고유번호'].astype(str)
            
            # 개인별 그룹핑 및 연차순 정렬
            grouped = df.groupby('고유번호')
            employee_groups = {}
            
            for emp_id, group_df in grouped:
                # 연차로 정렬 (NaN 값은 마지막에)
                if '연차' in group_df.columns:
                    # 연차 컬럼을 숫자로 변환
                    group_df = group_df.copy()
                    group_df['연차_numeric'] = pd.to_numeric(group_df['연차'], errors='coerce')
                    group_df = group_df.sort_values('연차_numeric', na_position='last')
                    group_df = group_df.drop('연차_numeric', axis=1)
                
                employee_groups[emp_id] = group_df.reset_index(drop=True)
                
                # 그룹핑 결과 로깅
                if '연차' in group_df.columns:
                    years = group_df['연차'].dropna()
                    if len(years) > 0:
                        self.logger.info(f"  {emp_id}: {len(group_df)}행, {int(years.min())}-{int(years.max())}년차")
            
            self.logger.info(f"개인별 그룹핑 완료: {len(employee_groups)}명")
            return employee_groups
            
        except Exception as e:
            self.logger.error(f"경력 데이터 로딩 실패: {e}")
            raise
    
    def create_integrated_career_timeline(self, emp_df: pd.DataFrame, emp_id: str) -> str:
        """개인의 모든 경력을 통합한 연속적인 타임라인 생성"""
        
        # 헤더 생성
        timeline_text = f"■ 고유번호: {emp_id}\n"
        timeline_text += f"■ 총 경력 기록: {len(emp_df)}개\n"
        
        # 경력 기간 정보 (수정된 로직)
        if '연차' in emp_df.columns:
            years = emp_df['연차'].dropna()
            if not years.empty:
                min_year = int(years.min())
                max_year = int(years.max())
                total_years = max_year - min_year + 1
                timeline_text += f"■ 경력 기간: {min_year}년차 → {max_year}년차 (총 {total_years}년)\n"
                timeline_text += f"■ 경력 연차: {sorted(years.astype(int).tolist())}\n"
        
        # 주요 도메인 요약
        if 'Domain 경험' in emp_df.columns:
            domains = emp_df['Domain 경험'].dropna().unique()
            if len(domains) > 0:
                timeline_text += f"■ 주요 도메인: {', '.join(domains)}\n"
        
        # 주요 역할 요약
        if '역할' in emp_df.columns:
            roles = emp_df['역할'].dropna().unique()
            if len(roles) > 0:
                timeline_text += f"■ 주요 역할: {', '.join(roles)}\n"
        
        timeline_text += "\n"
        
        # 연차별 상세 정보 (시간순)
        timeline_text += "=== 연차별 경력 상세 ===\n\n"
        
        for idx, (_, row) in enumerate(emp_df.iterrows(), 1):
            # 연차 정보
            year_info = f"▣ {int(row['연차'])}년차" if pd.notna(row.get('연차')) else f"▣ 기록 {idx}"
            timeline_text += year_info + "\n"
            
            # 프로젝트/업무 정보
            if pd.notna(row.get('업무')):
                timeline_text += f"  📋 업무: {row['업무']}\n"
            
            # 역할 정보
            if pd.notna(row.get('역할')):
                timeline_text += f"  👤 역할: {row['역할']}\n"
            
            # 도메인 정보
            if pd.notna(row.get('Domain 경험')):
                timeline_text += f"  🏢 도메인: {row['Domain 경험']}\n"
            
            # 프로젝트 규모
            if pd.notna(row.get('프로젝트 규모(M/M)')):
                timeline_text += f"  📊 규모: {row['프로젝트 규모(M/M)']}M/M\n"
            
            # 스킬셋 정보
            skills = self._extract_skills_from_row(row)
            if skills:
                resolved_skills = self._resolve_skill_codes(skills)
                if resolved_skills['skill_names']:
                    timeline_text += f"  🔧 활용 기술: {', '.join(resolved_skills['skill_names'][:5])}\n"
            
            # 중요 경력 포인트
            if self._is_important_career_point(row):
                impact_desc = row.get('큰 영향을 받은 업무/시기에 대한 설명')
                if pd.notna(impact_desc):
                    timeline_text += f"  ⭐ 핵심 경력: {impact_desc}\n"
            
            timeline_text += "\n"
        
        return timeline_text
    
    def _extract_skills_from_row(self, row: pd.Series) -> List[str]:
        """행에서 스킬 코드들 추출"""
        skills = []
        for col in row.index:
            if 'Skill set' in col and pd.notna(row[col]):
                skill_code = str(row[col]).strip()
                if skill_code:
                    skills.append(skill_code)
        return skills
    
    def _resolve_skill_codes(self, skill_codes: List[str]) -> Dict[str, Any]:
        """스킬 코드를 실제 스킬명으로 변환"""
        resolved_skills = {
            'skill_names': [],
            'job_categories': [],
            'technical_skills': [],
            'management_skills': []
        }
        
        for code in skill_codes:
            if code and code in self.skillset_mapping:
                skill_info = self.skillset_mapping[code]
                skill_name = skill_info['skill_name']
                job_category = skill_info['job_category']
                
                resolved_skills['skill_names'].append(skill_name)
                resolved_skills['job_categories'].append(job_category)
                
                # 기술/관리 스킬 분류
                if any(keyword in skill_name.lower() for keyword in 
                      ['dev', 'eng', 'architect', 'database', 'system', 'network']):
                    resolved_skills['technical_skills'].append(skill_name)
                elif any(keyword in skill_name.lower() for keyword in 
                        ['pm', 'management', '관리', 'lead']):
                    resolved_skills['management_skills'].append(skill_name)
        
        # 중복 제거
        for key in resolved_skills:
            resolved_skills[key] = list(set(resolved_skills[key]))
        
        return resolved_skills
    
    def _is_important_career_point(self, row: pd.Series) -> bool:
        """중요한 경력 포인트인지 확인"""
        impact_col = '커리어 형성에 큰 영향을 받은 업무나 시기'
        return pd.notna(row.get(impact_col)) and str(row.get(impact_col)).upper() == 'TRUE'
    
    def create_comprehensive_metadata(self, emp_id: str, emp_df: pd.DataFrame) -> Dict[str, Any]:
        """포괄적이고 정확한 메타데이터 생성"""
        metadata = {
            'employee_id': emp_id,
            'total_career_records': len(emp_df),
            'source_file': self.csv_path,
            'processing_timestamp': datetime.now().isoformat(),
            'processing_method': 'integrated_career_timeline'
        }
        
        # 연차 정보 (정확한 계산)
        if '연차' in emp_df.columns:
            years = emp_df['연차'].dropna()
            if not years.empty:
                min_year = int(years.min())
                max_year = int(years.max())
                metadata.update({
                    'career_start_year': min_year,
                    'career_end_year': max_year,
                    'total_experience_years': max_year - min_year + 1,
                    'experience_level': self._categorize_experience_level(max_year),
                    'year_list': sorted(years.astype(int).tolist())
                })
        
        # 도메인 분석
        if 'Domain 경험' in emp_df.columns:
            domains = emp_df['Domain 경험'].dropna().unique()
            if len(domains) > 0:
                metadata.update({
                    'domains': list(domains),
                    'primary_domain': domains[0],
                    'domain_diversity': len(domains),
                    'is_domain_specialist': len(domains) <= 2
                })
        
        # 역할 분석
        if '역할' in emp_df.columns:
            roles = emp_df['역할'].dropna().unique()
            if len(roles) > 0:
                metadata.update({
                    'roles': list(roles),
                    'role_progression_complexity': len(roles),
                    'is_leadership_track': any('PM' in str(role) or '관리' in str(role) or 'Lead' in str(role) 
                                             for role in roles)
                })
        
        # 스킬셋 종합 분석
        all_skills = []
        for _, row in emp_df.iterrows():
            row_skills = self._extract_skills_from_row(row)
            all_skills.extend(row_skills)
        
        if all_skills:
            resolved_skills = self._resolve_skill_codes(list(set(all_skills)))
            metadata.update({
                'total_skill_codes': len(set(all_skills)),
                'skill_names': resolved_skills['skill_names'][:10],  # 상위 10개만
                'job_categories': list(set(resolved_skills['job_categories'])),
                'technical_skills': resolved_skills['technical_skills'][:5],
                'management_skills': resolved_skills['management_skills'][:5],
                'skill_diversity_score': len(set(resolved_skills['job_categories']))
            })
        
        # 중요 경력 포인트 수
        important_points = sum(1 for _, row in emp_df.iterrows() if self._is_important_career_point(row))
        metadata['critical_career_points'] = important_points
        
        return metadata
    
    def _categorize_experience_level(self, max_year: int) -> str:
        """경력 레벨 분류"""
        if max_year <= 3:
            return "junior"
        elif max_year <= 7:
            return "mid-level"
        elif max_year <= 15:
            return "senior"
        else:
            return "expert"
    
    def create_fixed_documents(self, employee_groups: Dict[str, pd.DataFrame]) -> List[Document]:
        """수정된 그룹핑 로직으로 Document 생성"""
        documents = []
        
        for emp_id, emp_df in employee_groups.items():
            try:
                # 통합된 경력 타임라인 텍스트 생성
                timeline_text = self.create_integrated_career_timeline(emp_df, emp_id)
                
                # 포괄적 메타데이터 생성
                metadata = self.create_comprehensive_metadata(emp_id, emp_df)
                
                # 문서 크기 체크 및 분할
                if len(timeline_text) <= 1500:
                    # 단일 문서
                    doc = Document(
                        page_content=timeline_text,
                        metadata=metadata
                    )
                    documents.append(doc)
                    
                else:
                    # 큰 문서는 분할 (하지만 메타데이터는 유지)
                    split_texts = self.text_splitter.split_text(timeline_text)
                    self.logger.info(f"{emp_id}: {len(split_texts)}개 청크로 분할")
                    
                    for i, split_text in enumerate(split_texts):
                        chunk_metadata = metadata.copy()
                        chunk_metadata.update({
                            'chunk_index': i,
                            'total_chunks': len(split_texts),
                            'chunk_size': len(split_text),
                            'original_document_size': len(timeline_text)
                        })
                        
                        chunk_doc = Document(
                            page_content=split_text,
                            metadata=chunk_metadata
                        )
                        documents.append(chunk_doc)
                
            except Exception as e:
                self.logger.error(f"{emp_id} 처리 중 오류: {e}")
                continue
        
        self.logger.info(f"총 {len(documents)}개 Document 생성 완료")
        return documents
    
    def rebuild_vectorstore_with_fixed_grouping(self) -> Dict[str, Any]:
        """수정된 그룹핑으로 VectorStore 재구축"""
        result = {
            "steps_completed": [],
            "errors": [],
            "success": False,
            "build_summary": {}
        }
        
        try:
            # 1. 기존 VectorStore 및 캐시 삭제
            self.logger.info("기존 VectorStore 삭제 중...")
            if os.path.exists(self.persist_directory):
                shutil.rmtree(self.persist_directory)
            if os.path.exists(self.cache_directory):
                shutil.rmtree(self.cache_directory)
            result["steps_completed"].append("기존 데이터 삭제")
            
            # 2. 디렉토리 재생성
            os.makedirs(self.persist_directory, exist_ok=True)
            os.makedirs(self.cache_directory, exist_ok=True)
            os.makedirs(os.path.dirname(self.docs_json_path), exist_ok=True)
            
            # 3. 수정된 그룹핑으로 데이터 로드
            self.logger.info("수정된 그룹핑으로 데이터 처리 중...")
            employee_groups = self.load_and_group_career_data()
            result["steps_completed"].append("개인별 데이터 그룹핑")
            
            # 4. 수정된 Document 생성
            self.logger.info("통합 Document 생성 중...")
            documents = self.create_fixed_documents(employee_groups)
            result["steps_completed"].append("통합 Document 생성")
            
            # 5. JSON 파일 저장
            self.logger.info("docs JSON 파일 저장 중...")
            with open(self.docs_json_path, 'w', encoding='utf-8') as f:
                json_docs = [
                    {"page_content": doc.page_content, "metadata": doc.metadata}
                    for doc in documents
                ]
                json.dump(json_docs, f, ensure_ascii=False, indent=2)
            result["steps_completed"].append("docs JSON 저장")
            
            # 6. ChromaDB 구축
            self.logger.info("ChromaDB 구축 중...")
            
            # 메타데이터 정제 (ChromaDB 호환성)
            filtered_documents = []
            for doc in documents:
                clean_metadata = {}
                for key, value in doc.metadata.items():
                    if isinstance(value, (str, int, float, bool)):
                        clean_metadata[key] = value
                    elif isinstance(value, list) and all(isinstance(item, str) for item in value):
                        clean_metadata[key] = ", ".join(value[:5])
                    elif value is not None:
                        clean_metadata[key] = str(value)
                
                filtered_doc = Document(
                    page_content=doc.page_content,
                    metadata=clean_metadata
                )
                filtered_documents.append(filtered_doc)
            
            # VectorStore 생성
            vector_store = Chroma.from_documents(
                documents=filtered_documents,
                embedding=self.cached_embeddings,
                persist_directory=self.persist_directory,
                collection_name="career_history"
            )
            
            vector_store.persist()
            result["steps_completed"].append("ChromaDB 구축")
            
            # 7. 구축 정보 요약
            result["build_summary"] = {
                'total_employees': len(employee_groups),
                'total_documents': len(filtered_documents),
                'persist_directory': self.persist_directory,
                'build_timestamp': datetime.now().isoformat(),
                'grouping_fixed': True,
                'employee_sample': {
                    emp_id: {
                        'rows': len(group),
                        'years': f"{int(group['연차'].min())}-{int(group['연차'].max())}" if '연차' in group.columns and not group['연차'].isna().all() else "N/A"
                    } for emp_id, group in list(employee_groups.items())[:3]
                }
            }
            
            result["success"] = True
            self.logger.info("VectorStore 재구축 완료!")
            
        except Exception as e:
            error_msg = f"VectorStore 재구축 실패: {str(e)}"
            result["errors"].append(error_msg)
            self.logger.error(error_msg)
        
        return result
    
    def verify_fix(self, target_user: str = "이재원") -> Dict[str, Any]:
        """수정 결과 검증"""
        verification = {
            "target_user": target_user,
            "vectorstore_test": {},
            "grouping_verification": {},
            "fix_success": False
        }
        
        try:
            # VectorStore 로드 테스트
            if os.path.exists(self.persist_directory):
                vectorstore = Chroma(
                    persist_directory=self.persist_directory,
                    embedding_function=self.cached_embeddings,
                    collection_name="career_history"
                )
                
                # 검색 테스트
                results = vectorstore.similarity_search(target_user, k=2)
                verification["vectorstore_test"] = {
                    "search_successful": True,
                    "results_count": len(results),
                    "results_analysis": []
                }
                
                for i, doc in enumerate(results):
                    # 연차 정보 추출
                    year_mentions = []
                    content = doc.page_content
                    import re
                    year_pattern = r'(\d+)년차'
                    matches = re.findall(year_pattern, content)
                    year_mentions = [int(match) for match in matches if match.isdigit()]
                    
                    analysis = {
                        "document_index": i,
                        "content_length": len(content),
                        "year_mentions": year_mentions,
                        "year_range": f"{min(year_mentions)}-{max(year_mentions)}" if year_mentions else "없음",
                        "total_years": max(year_mentions) - min(year_mentions) + 1 if year_mentions else 0,
                        "appears_integrated": "총 경력 기록:" in content and content.count("▣") > 1,
                        "metadata_quality": {
                            "employee_id": doc.metadata.get("employee_id", "없음"),
                            "total_experience_years": doc.metadata.get("total_experience_years", "없음"),
                            "domains": doc.metadata.get("domains", "없음"),
                            "roles": doc.metadata.get("roles", "없음")
                        }
                    }
                    verification["vectorstore_test"]["results_analysis"].append(analysis)
                
                # 그룹핑 검증
                if results:
                    first_result = verification["vectorstore_test"]["results_analysis"][0]
                    verification["grouping_verification"] = {
                        "single_document_covers_multiple_years": first_result["total_years"] > 1,
                        "metadata_properly_extracted": first_result["metadata_quality"]["employee_id"] != "없음",
                        "content_appears_integrated": first_result["appears_integrated"],
                        "year_range_reasonable": first_result["total_years"] >= 5  # 5년 이상 경력
                    }
                    
                    # 전체적 성공 여부 판단
                    verification["fix_success"] = all([
                        verification["grouping_verification"]["single_document_covers_multiple_years"],
                        verification["grouping_verification"]["metadata_properly_extracted"],
                        verification["grouping_verification"]["content_appears_integrated"]
                    ])
            
        except Exception as e:
            verification["error"] = f"검증 실패: {str(e)}"
        
        return verification

def main():
    """메인 실행 함수"""
    print("🔧 VectorDB 그룹핑 문제 자동 수정을 시작합니다...")
    
    fixer = VectorDBGroupingFixer()
    
    # 1. 현재 상태 확인
    print("\n1️⃣ 현재 VectorDB 상태 확인...")
    current_verification = fixer.verify_fix()
    
    if current_verification.get("fix_success"):
        print("✅ VectorDB가 이미 올바르게 구성되어 있습니다!")
        return
    
    # 2. VectorStore 재구축
    print("\n2️⃣ 수정된 그룹핑으로 VectorStore 재구축 중...")
    rebuild_result = fixer.rebuild_vectorstore_with_fixed_grouping()
    
    # 3. 결과 출력
    print(f"\n📊 재구축 결과:")
    print(f"   - 성공 여부: {'✅' if rebuild_result['success'] else '❌'}")
    print(f"   - 완료된 단계: {len(rebuild_result['steps_completed'])}개")
    
    for step in rebuild_result['steps_completed']:
        print(f"     ✓ {step}")
    
    if rebuild_result['errors']:
        print(f"   - 오류: {len(rebuild_result['errors'])}개")
        for error in rebuild_result['errors']:
            print(f"     ❌ {error}")
    
    if rebuild_result['success']:
        build_summary = rebuild_result['build_summary']
        print(f"\n📈 구축 요약:")
        print(f"   - 처리된 사용자: {build_summary['total_employees']}명")
        print(f"   - 생성된 문서: {build_summary['total_documents']}개")
        print(f"   - 그룹핑 수정: {'예' if build_summary['grouping_fixed'] else '아니오'}")
        
        # 샘플 사용자 정보
        if build_summary['employee_sample']:
            print(f"   - 샘플 사용자:")
            for emp_id, info in build_summary['employee_sample'].items():
                print(f"     • {emp_id}: {info['rows']}행 → {info['years']}년차")
    
    # 4. 수정 결과 검증
    if rebuild_result['success']:
        print(f"\n3️⃣ 수정 결과 검증 중...")
        verification = fixer.verify_fix("EMP-100001")
        
        print(f"🔍 검증 결과:")
        if verification.get("fix_success"):
            print(f"   ✅ 그룹핑 문제가 성공적으로 해결되었습니다!")
            
            # 상세 결과
            if verification["vectorstore_test"]["results_analysis"]:
                result = verification["vectorstore_test"]["results_analysis"][0]
                print(f"   📊 'EMP-100001' 검색 결과:")
                print(f"     - 연차 범위: {result['year_range']}")
                print(f"     - 총 경력 년수: {result['total_years']}년")
                print(f"     - 통합된 문서: {'예' if result['appears_integrated'] else '아니오'}")
                print(f"     - 메타데이터 품질: {result['metadata_quality']['employee_id']}")
        else:
            print(f"   ❌ 일부 문제가 남아있습니다.")
            grouping = verification.get("grouping_verification", {})
            for key, value in grouping.items():
                status = "✅" if value else "❌"
                print(f"     {status} {key}: {value}")

if __name__ == "__main__":
    main()