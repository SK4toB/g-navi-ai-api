# careerhistory_data_processor.py
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
                 csv_path: str = "app/data/csv/career_history_v2.csv",
                 skillset_csv_path: str = "app/data/csv/skill_set.csv",
                 persist_directory: str = "app/storage/vector_stores/career_data",
                 cache_directory: str = "app/storage/cache/embedding_cache",
                 docs_json_path: str = "app/storage/docs/career_history.json"):
        
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
        try:  # 스킬셋 매핑 로드 시작
            if os.path.exists(self.skillset_csv_path):  # 스킬셋 파일이 존재하는 경우
                skill_df = pd.read_csv(self.skillset_csv_path, encoding='utf-8')  # CSV 파일 로드
                mapping = {}
                for _, row in skill_df.iterrows():  # 스킬셋 데이터 순회
                    if pd.notna(row.get('코드')):  # 코드가 존재하는 경우
                        code = str(row['코드']).strip()  # 코드 정리
                        mapping[code] = {
                            'skill_name': str(row.get('Skill set', '')).strip(),
                            'job_category': str(row.get('Skillset-직무연계', '')).strip(),
                            'description': str(row.get('Skill set', '')).strip()
                        }
                # end for (스킬셋 데이터 순회)
                self.skillset_mapping = mapping
                self.logger.info(f"스킬셋 매핑 완료: {len(mapping)}개")
        except Exception as e:  # 예외 처리
            self.logger.warning(f"스킬셋 매핑 로드 실패: {e}")
    
    def load_and_group_career_data(self) -> Dict[str, pd.DataFrame]:
        """경력 데이터를 로드하고 개인별로 올바르게 그룹핑"""
        try:  # 경력 데이터 로드 시작
            # CSV 로드
            df = pd.read_csv(self.csv_path, encoding='utf-8')  # CSV 파일 로드
            self.logger.info(f"경력 데이터 로드: {len(df)}행")
            
            # 데이터 정제
            df = df.dropna(subset=['고유번호']) 
            df['고유번호'] = df['고유번호'].astype(str)
            
            # 연도 및 연차 데이터 정제
            if '연도' in df.columns:  # 연도 컬럼이 존재하는 경우
                df['연도_numeric'] = pd.to_numeric(df['연도'], errors='coerce')
            if '연차' in df.columns:  # 연차 컬럼이 존재하는 경우
                df['연차_numeric'] = pd.to_numeric(df['연차'], errors='coerce')
            # 개인별 그룹핑 및 연도-연차순 정렬
            grouped = df.groupby('고유번호')
            employee_groups = {}
            
            for emp_id, group_df in grouped:  # 직원별 그룹 순회
                group_df = group_df.copy()
                
                # 연도와 연차를 기준으로 정렬 (연도 우선, 연차 보조)
                if '연도_numeric' in group_df.columns and '연차_numeric' in group_df.columns:  # 연도와 연차 모두 존재하는 경우
                    group_df = group_df.sort_values(['연도_numeric', '연차_numeric'], na_position='last')  # 연도-연차 순 정렬
                elif '연차_numeric' in group_df.columns:  # 연차만 존재하는 경우
                    group_df = group_df.sort_values('연차_numeric', na_position='last')  # 연차순 정렬
                
                employee_groups[emp_id] = group_df.reset_index(drop=True)
                
                # 그룹핑 결과 로깅 (연도 범위 포함)
                if '연도_numeric' in group_df.columns:  # 연도 컬럼이 존재하는 경우
                    years = group_df['연도_numeric'].dropna()  # 연도 데이터 추출
                    career_years = group_df['연차_numeric'].dropna()  # 연차 데이터 추출
                    
                    year_info = ""
                    if len(years) > 0:  # 연도 데이터가 있는 경우
                        year_info += f"{int(years.min())}-{int(years.max())}년"
                    if len(career_years) > 0:  # 연차 데이터가 있는 경우
                        year_info += f" ({int(career_years.min())}-{int(career_years.max())}년차)"
                    
                    self.logger.info(f"  {emp_id}: {len(group_df)}행, {year_info}")
            # end for (직원별 그룹 순회)
            
            self.logger.info(f"개인별 그룹핑 완료: {len(employee_groups)}명")
            return employee_groups
            
        except Exception as e:  # 예외 처리
            self.logger.error(f"경력 데이터 로딩 실패: {e}")
            raise
    
    def _find_column_by_keyword(self, df: pd.DataFrame, keywords: List[str]) -> Optional[str]:
        """키워드를 기반으로 컬럼명을 찾는 헬퍼 함수"""
        for col in df.columns:
            col_clean = col.replace('\n', ' ').strip()
            for keyword in keywords:
                if keyword in col_clean:
                    return col
        return None
    
    def create_integrated_career_timeline(self, emp_df: pd.DataFrame, emp_id: str) -> str:
        """개인의 모든 경력을 통합한 연속적인 타임라인 생성 (연도 정보 포함)"""
        
        # 헤더 생성
        timeline_text = f"고유번호: {emp_id}\n"
        timeline_text += f"총 경력 기록: {len(emp_df)}개\n"
        
        # 연도 및 경력 기간 정보
        year_info = self._extract_year_career_info(emp_df)
        if year_info:
            timeline_text += f"활동 연도: {year_info['year_range']}\n"
            timeline_text += f"경력 기간: {year_info['career_range']}\n"
            timeline_text += f"총 활동 기간: {year_info['total_active_years']}년\n"
            timeline_text += f"경력 발전: {year_info['career_progression']}\n"
        
        # 컬럼명 동적 찾기
        project_col = self._find_column_by_keyword(emp_df, ['주요 업무', '프로젝트'])
        role_col = self._find_column_by_keyword(emp_df, ['수행역할', '역할'])
        domain_col = self._find_column_by_keyword(emp_df, ['Industry', 'Domain'])
        scale_col = self._find_column_by_keyword(emp_df, ['프로젝트 규모'])
        
        # 주요 도메인 요약
        if domain_col and domain_col in emp_df.columns:
            domains = emp_df[domain_col].dropna().unique()
            if len(domains) > 0:
                timeline_text += f"주요 도메인: {', '.join(domains)}\n"
        
        # 주요 역할 요약
        if role_col and role_col in emp_df.columns:
            roles = emp_df[role_col].dropna().unique()
            if len(roles) > 0:
                timeline_text += f"주요 역할: {', '.join(roles)}\n"
        
        timeline_text += "\n"
        
        # 연도-연차별 상세 정보 (시간순)
        timeline_text += "연도별 경력 상세\n\n"
        
        for idx, (_, row) in enumerate(emp_df.iterrows(), 1):
            # 연도 및 연차 정보 통합 표시
            year_career_info = self._format_year_career_info(row)
            timeline_text += f"▣ {year_career_info}\n"
            
            # 프로젝트/업무 정보
            if project_col and pd.notna(row.get(project_col)):
                timeline_text += f" 업무: {row[project_col]}\n"
            
            # 역할 정보
            if role_col and pd.notna(row.get(role_col)):
                timeline_text += f"역할: {row[role_col]}\n"
            
            # 도메인 정보
            if domain_col and pd.notna(row.get(domain_col)):
                timeline_text += f"도메인: {row[domain_col]}\n"
            
            # 프로젝트 규모
            if scale_col and pd.notna(row.get(scale_col)):
                timeline_text += f"규모: {row[scale_col]}\n"
            
            # 스킬셋 정보
            skills = self._extract_skills_from_row(row)
            if skills:
                resolved_skills = self._resolve_skill_codes(skills)
                if resolved_skills['skill_names']:
                    timeline_text += f" 활용 기술: {', '.join(resolved_skills['skill_names'][:5])}\n"
            
            # 중요 경력 포인트
            if self._is_important_career_point(row):
                impact_desc = row.get('큰 영향을 받은 업무/시기에 대한 설명')
                if pd.notna(impact_desc):
                    timeline_text += f"핵심 경력: {impact_desc}\n"
            
            timeline_text += "\n"
        
        return timeline_text
    
    def _extract_year_career_info(self, emp_df: pd.DataFrame) -> Dict[str, Any]:
        """연도 및 경력 정보 추출 및 분석"""
        info = {}
        
        # 연도 정보 처리
        if '연도' in emp_df.columns:
            years = pd.to_numeric(emp_df['연도'], errors='coerce').dropna()
            if not years.empty:
                min_year = int(years.min())
                max_year = int(years.max())
                info['year_range'] = f"{min_year}년 ~ {max_year}년"
                info['total_active_years'] = max_year - min_year + 1
                info['year_list'] = sorted(years.astype(int).tolist())
        
        # 경력 연차 정보 처리
        if '연차' in emp_df.columns:
            career_years = pd.to_numeric(emp_df['연차'], errors='coerce').dropna()
            if not career_years.empty:
                min_career = int(career_years.min())
                max_career = int(career_years.max())
                info['career_range'] = f"{min_career}년차 ~ {max_career}년차"
                info['career_progression'] = f"{max_career - min_career + 1}년간 발전"
                info['career_list'] = sorted(career_years.astype(int).tolist())
        
        # 연도와 경력의 일관성 확인
        if 'year_list' in info and 'career_list' in info:
            # 연도 범위와 경력 발전의 연관성 분석
            year_span = info['total_active_years']
            career_span = len(set(info['career_list']))
            
            if year_span > 0 and career_span > 0:
                info['consistency_ratio'] = career_span / year_span
                if info['consistency_ratio'] > 0.8:
                    info['career_consistency'] = "연속적 경력 발전"
                elif info['consistency_ratio'] > 0.5:
                    info['career_consistency'] = "중간 수준 경력 발전"
                else:
                    info['career_consistency'] = "단편적 경력 기록"
        
        return info
    
    def _format_year_career_info(self, row: pd.Series) -> str:
        """개별 행의 연도-연차 정보를 포맷팅"""
        year = row.get('연도')
        career_year = row.get('연차')
        
        parts = []
        
        if pd.notna(year):
            parts.append(f"{int(year)}년")
        
        if pd.notna(career_year):
            parts.append(f"{int(career_year)}년차")
        
        if not parts:
            # 연도/연차 정보가 없는 경우 다른 식별 정보 사용
            if pd.notna(row.get('시작연차')) and pd.notna(row.get('종료연차')):
                start_year = int(row['시작연차'])
                end_year = int(row['종료연차'])
                parts.append(f"{start_year}-{end_year}년차 기간")
            else:
                parts.append("기록")
        
        return " ".join(parts)
    
    def _extract_skills_from_row(self, row: pd.Series) -> List[str]:
        """행에서 스킬 코드들 추출 (새로운 컬럼명 지원)"""
        skills = []
        
        # 새로운 v2 형식의 스킬 컬럼들
        skill_columns = [
            '활용 Skill set 1', '활용 Skill set 2', '활용 Skill set 3', '활용 Skill set 4'
        ]
        
        for col in skill_columns:
            if col in row.index and pd.notna(row[col]):
                skill_code = str(row[col]).strip()
                if skill_code:
                    skills.append(skill_code)
                    
        for col in row.index:
            if 'Skill set' in col and col not in skill_columns and pd.notna(row[col]):
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
        """중요한 경력 포인트인지 확인 (새로운 컬럼명 지원)"""
        # 새로운 v2 형식
        impact_col_v2 = '커리어 형성에 큰 영향을 받은 업무나 시기'
        if impact_col_v2 in row.index:
            return pd.notna(row.get(impact_col_v2)) and str(row.get(impact_col_v2)).upper() == 'TRUE'
        
        # 기존 형식 (하위 호환성)
        impact_col_v1 = '커리어 형성에 큰 영향을 받은 업무나 시기'
        return pd.notna(row.get(impact_col_v1)) and str(row.get(impact_col_v1)).upper() == 'TRUE'
    
    def create_comprehensive_metadata(self, emp_id: str, emp_df: pd.DataFrame) -> Dict[str, Any]:
        """메타데이터 생성 (연도 정보 포함)"""
        metadata = {
            'employee_id': emp_id,
            'total_career_records': len(emp_df),
            'source_file': self.csv_path,
            'processing_timestamp': datetime.now().isoformat(),
            'processing_method': 'integrated_career_timeline_with_year_data'
        }
        
        # 연도 정보 추가
        if '연도' in emp_df.columns:
            years = pd.to_numeric(emp_df['연도']).dropna()
            if not years.empty:
                min_year = int(years.min())
                max_year = int(years.max())
                metadata.update({
                    'activity_start_year': min_year,
                    'activity_end_year': max_year,
                    'total_activity_years': max_year - min_year + 1,
                    'activity_years_list': sorted(years.astype(int).tolist()),
                    'activity_decade': f"{min_year//10*10}s-{max_year//10*10}s"
                })
        
        # 연차 정보
        if '연차' in emp_df.columns:
            career_years = pd.to_numeric(emp_df['연차']).dropna()
            if not career_years.empty:
                min_career = int(career_years.min())
                max_career = int(career_years.max())
                metadata.update({
                    'career_start_year': min_career,
                    'career_end_year': max_career,
                    'total_experience_years': max_career - min_career + 1,
                    'experience_level': self._categorize_experience_level(max_career),
                    'career_years_list': sorted(career_years.astype(int).tolist()),
                    'career_progression_span': max_career - min_career + 1
                })
        
        # 도메인 분석 (컬럼명 업데이트)
        domain_columns = ['Industry/Domain', 'Domain 경험']
        for col in domain_columns:
            if col in emp_df.columns:
                domains = emp_df[col].dropna().unique()
                if len(domains) > 0:
                    metadata.update({
                        'domains': list(domains),
                        'primary_domain': domains[0],
                        'domain_diversity': len(domains),
                        'is_domain_specialist': len(domains) <= 2
                    })
                break
        
        # 역할 분석
        role_columns = ['수행역할', '역할']
        for col in role_columns:
            if col in emp_df.columns:
                roles = emp_df[col].dropna().unique()
                if len(roles) > 0:
                    metadata.update({
                        'roles': list(roles),
                        'role_progression_complexity': len(roles),
                        'is_leadership_track': any('PM' in str(role) or '관리' in str(role) or 'Lead' in str(role) 
                                                 for role in roles)
                    })
                break
        
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
        
        # 프로젝트 규모 분석 (신규)
        scale_columns = ['프로젝트 규모 (대략)', '프로젝트 규모(M/M)']
        for col in scale_columns:
            if col in emp_df.columns:
                scales = emp_df[col].dropna()
                if not scales.empty:
                    metadata.update({
                        'project_scales': list(scales.unique()),
                        'project_scale_diversity': len(scales.unique()),
                        'has_large_projects': any('대형' in str(scale) or '50억 이상' in str(scale) 
                                                for scale in scales)
                    })
                break
        
        # 중요 경력 포인트 수
        important_points = sum(1 for _, row in emp_df.iterrows() if self._is_important_career_point(row))
        metadata['critical_career_points'] = important_points
        
        # 경력 품질 점수 계산 (신규)
        metadata['career_quality_score'] = self._calculate_career_quality_score(metadata)
        
        return metadata
    
    def _analyze_career_continuity(self, activity_years: List[int], career_years: List[int]) -> str:
        """경력 연속성 분석"""
        if not activity_years or not career_years:
            return "insufficient_data"
        
        # 활동 연도의 연속성 확인
        activity_gaps = []
        for i in range(1, len(activity_years)):
            gap = activity_years[i] - activity_years[i-1]
            if gap > 1:
                activity_gaps.append(gap)
        
        # 경력 연차의 연속성 확인
        career_gaps = []
        for i in range(1, len(career_years)):
            gap = career_years[i] - career_years[i-1]
            if gap > 1:
                career_gaps.append(gap)
        
        if not activity_gaps and not career_gaps:
            return "continuous"
        elif len(activity_gaps) <= 1 and len(career_gaps) <= 1:
            return "mostly_continuous"
        else:
            return "fragmented"
    
    def _calculate_career_quality_score(self, metadata: Dict[str, Any]) -> float:
        """경력 품질 점수 계산 (0-100점)"""
        score = 0.0
        
        # 경력 기간 점수 (30점)
        total_years = metadata.get('total_experience_years', 0)
        if total_years >= 10:
            score += 30
        elif total_years >= 5:
            score += 20
        elif total_years >= 2:
            score += 10
        
        # 도메인 전문성 점수 (20점)
        domain_diversity = metadata.get('domain_diversity', 0)
        if domain_diversity >= 3:
            score += 20
        elif domain_diversity >= 2:
            score += 15
        elif domain_diversity >= 1:
            score += 10
        
        # 스킬 다양성 점수 (20점)
        skill_diversity = metadata.get('skill_diversity_score', 0)
        if skill_diversity >= 5:
            score += 20
        elif skill_diversity >= 3:
            score += 15
        elif skill_diversity >= 1:
            score += 10
        
        # 리더십 경험 점수 (15점)
        if metadata.get('is_leadership_track', False):
            score += 15
        
        # 경력 연속성 점수 (15점)
        continuity = metadata.get('career_continuity', 'insufficient_data')
        if continuity == 'continuous':
            score += 15
        elif continuity == 'mostly_continuous':
            score += 10
        elif continuity == 'fragmented':
            score += 5
        
        return min(score, 100.0)
    
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
        """VectorStore 구축"""
        result = {
            "steps_completed": [],
            "errors": [],
            "success": False,
            "build_summary": {}
        }
        
        try:
            # 수정된 그룹핑으로 데이터 로드
            self.logger.info("데이터 처리")
            employee_groups = self.load_and_group_career_data()
            result["steps_completed"].append("개인별 데이터 그룹핑")
            
            # 수정된 Document 생성
            self.logger.info("통합 Document 생성 중...")
            documents = self.create_fixed_documents(employee_groups)
            result["steps_completed"].append("통합 Document 생성")
            
            # JSON 파일 저장
            self.logger.info("docs JSON 파일 저장 중...")
            with open(self.docs_json_path, 'w', encoding='utf-8') as f:
                json_docs = [
                    {"page_content": doc.page_content, "metadata": doc.metadata}
                    for doc in documents
                ]
                json.dump(json_docs, f, ensure_ascii=False, indent=2)
            result["steps_completed"].append("docs JSON 저장")
            
            # ChromaDB
            self.logger.info("ChromaDB")
            
            # VectorStore 생성
            vector_store = Chroma.from_documents(
                documents=documents,
                embedding=self.cached_embeddings,
                persist_directory=self.persist_directory,
                collection_name="career_history"
            )
            
            vector_store.persist()
            result["steps_completed"].append("ChromaDB 구축")
            
            # 구축 정보 요약
            result["build_summary"] = {
                'total_employees': len(employee_groups),
                'total_documents': len(documents),
                'persist_directory': self.persist_directory,
                'build_timestamp': datetime.now().isoformat(),
                'grouping_fixed': True,
                'employee': {
                    emp_id: {
                        'rows': len(group),
                        'years': f"{int(group['연차'].min())}-{int(group['연차'].max())}" if '연차' in group.columns and not group['연차'].isna().all() else "N/A"
                    } for emp_id, group in list(employee_groups.items())[:3]
                }
            }
            
            result["success"] = True
            self.logger.info("VectorStore 구축 완료")
            
        except Exception as e:
            error_msg = f"VectorStore 구축 실패: {str(e)}"
            result["errors"].append(error_msg)
            self.logger.error(error_msg)
        
        return result
    
    def verify_fix(self, target_user: str) -> Dict[str, Any]:
        """수정 결과 검증 (연도 정보 포함)"""
        verification = {
            "target_user": target_user,
            "vectorstore_test": {},
            "grouping_verification": {},
            "year_analysis_verification": {},
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
                    # 기본 문서 분석
                    content = doc.page_content
                    
                    analysis = {
                        "document_index": i,
                        "content_length": len(content),
                        "appears_integrated": "총 경력 기록:" in content and content.count("▣") > 1,
                        "has_year_info": "활동 연도:" in content,
                        "has_career_progression": "경력 발전:" in content,
                        "metadata_quality": {
                            "employee_id": doc.metadata.get("employee_id", "없음"),
                            "activity_start_year": doc.metadata.get("activity_start_year", "없음"),
                            "activity_end_year": doc.metadata.get("activity_end_year", "없음"),
                            "total_experience_years": doc.metadata.get("total_experience_years", "없음"),
                            "career_quality_score": doc.metadata.get("career_quality_score", "없음"),
                            "domains": doc.metadata.get("domains", "없음"),
                            "roles": doc.metadata.get("roles", "없음")
                        }
                    }
                    verification["vectorstore_test"]["results_analysis"].append(analysis)
                
                # 그룹핑 검증
                if results:
                    first_result = verification["vectorstore_test"]["results_analysis"][0]
                    verification["grouping_verification"] = {
                        "metadata_properly_extracted": first_result["metadata_quality"]["employee_id"] != "없음",
                        "content_appears_integrated": first_result["appears_integrated"],
                        "has_reasonable_content": first_result["content_length"] > 100
                    }
                    
                    # 연도 분석 검증 (신규)
                    verification["year_analysis_verification"] = {
                        "year_info_present": first_result["has_year_info"],
                        "career_progression_analyzed": first_result["has_career_progression"],
                        "activity_year_metadata": first_result["metadata_quality"]["activity_start_year"] != "없음",
                        "career_quality_calculated": first_result["metadata_quality"]["career_quality_score"] != "없음"
                    }
                    
                    # 전체적 성공 여부 판단
                    basic_success = all([
                        verification["grouping_verification"]["metadata_properly_extracted"],
                        verification["grouping_verification"]["content_appears_integrated"],
                        verification["grouping_verification"]["has_reasonable_content"]
                    ])
                    
                    year_analysis_success = any([
                        verification["year_analysis_verification"]["year_info_present"],
                        verification["year_analysis_verification"]["activity_year_metadata"],
                        verification["year_analysis_verification"]["career_quality_calculated"]
                    ])
                    
                    verification["fix_success"] = basic_success and year_analysis_success
            
        except Exception as e:
            verification["error"] = f"검증 실패: {str(e)}"
        
        return verification

def main():
    """메인 실행 함수"""
    
    fixer = VectorDBGroupingFixer()
    
    # 현재 상태 확인
    current_verification = fixer.verify_fix()
    
    if current_verification.get("fix_success"):
        # 연도 분석 결과 출력
        if "year_analysis_verification" in current_verification:
            year_analysis = current_verification["year_analysis_verification"]
            print("연도 분석 상태:")
            for key, value in year_analysis.items():
                status = "o" if value else "x"
                print(f"  {status} {key}: {value}")
        return
    
    # VectorStore 재구축
    rebuild_result = fixer.rebuild_vectorstore_with_fixed_grouping()

    
    if rebuild_result['success']:
        build_summary = rebuild_result['build_summary']
        print(f"   - 처리된 사용자: {build_summary['total_employees']}명")
        print(f"   - 생성된 문서: {build_summary['total_documents']}개")
        print(f"   - 그룹핑 수정: {'예' if build_summary['grouping_fixed'] else '아니오'}")

if __name__ == "__main__":
    main()