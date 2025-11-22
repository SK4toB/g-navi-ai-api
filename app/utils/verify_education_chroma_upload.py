# app/utils/verify_education_chroma_upload.py
"""
* @className : EducationDataVerifier
* @description : 교육과정 데이터 검증 유틸리티 모듈
*                업로드된 교육과정 데이터의 정합성을 검증하는 유틸리티입니다.
*                ChromaDB에 저장된 교육 데이터의 품질과 완성도를 확인합니다.
*
"""

import os
import requests
import base64
from typing import Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

class EducationChromaUploadVerifier:
    """교육과정 ChromaDB 업로드 검증 전용 클래스"""
    
    def __init__(self):
        # Pod ChromaDB 설정
        self.pod_base_url = "https://chromadb-1.skala25a.project.skala-ai.com/api/v1"
        self.pod_auth_credentials = os.getenv("CHROMA_AUTH_CREDENTIALS")
        self.pod_collection_name = "gnavi4_education_prod"
        
        # OpenAI 임베딩 설정
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        self.headers = self._get_auth_headers()
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Pod ChromaDB 인증 헤더"""
        if not self.pod_auth_credentials:
            raise ValueError("CHROMA_AUTH_CREDENTIALS 환경변수가 설정되지 않았습니다")
        
        encoded_credentials = base64.b64encode(
            self.pod_auth_credentials.encode()
        ).decode()
        
        return {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/json"
        }
    
    def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """OpenAI API로 임베딩 생성"""
        if not self.openai_api_key:
            print("⚠️ OPENAI_API_KEY가 없어서 임베딩 검색을 건너뜁니다")
            return []
        
        try:
            import openai
            
            # OpenAI 클라이언트 초기화
            client = openai.OpenAI(api_key=self.openai_api_key)
            
            # 임베딩 생성
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=texts,
                dimensions=1536
            )
            
            embeddings = [data.embedding for data in response.data]
            return embeddings
            
        except Exception as e:
            print(f"⚠️ 임베딩 생성 실패: {str(e)}")
            return []
    
    def verify_collection_exists(self):
        """교육과정 컬렉션 존재 여부 확인"""
        print(f"📋 교육과정 컬렉션 존재 여부 확인: {self.pod_collection_name}")
        
        try:
            # 모든 컬렉션 목록 조회
            response = requests.get(
                f"{self.pod_base_url}/collections",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                collections = response.json()
                collection_names = [col.get('name', '') for col in collections]
                
                print(f"  📝 전체 컬렉션 수: {len(collections)}")
                print(f"  📝 컬렉션 목록: {collection_names}")
                
                if self.pod_collection_name in collection_names:
                    print(f"  ✅ 교육과정 컬렉션 발견: {self.pod_collection_name}")
                    
                    # 해당 컬렉션 정보 찾기
                    target_collection = next(
                        (col for col in collections if col.get('name') == self.pod_collection_name), 
                        None
                    )
                    
                    if target_collection:
                        print(f"  📊 컬렉션 ID: {target_collection.get('id')}")
                        print(f"  📊 메타데이터: {target_collection.get('metadata', {})}")
                        return target_collection.get('id')
                else:
                    print(f"  ❌ 교육과정 컬렉션이 없습니다: {self.pod_collection_name}")
                    return None
            else:
                print(f"  ❌ 컬렉션 목록 조회 실패: {response.status_code}")
                print(f"  응답: {response.text}")
                return None
                
        except Exception as e:
            print(f"  ❌ 교육과정 컬렉션 확인 중 오류: {str(e)}")
            return None
    
    def test_search_functionality(self, collection_id=None):
        """교육과정 검색 기능 테스트 (임베딩 기반)"""
        print(f"\n🔍 교육과정 검색 기능 테스트")
        
        collection_identifier = collection_id if collection_id else self.pod_collection_name
        
        # 교육과정 데이터 기반 테스트 케이스들
        test_queries = [
            "프로그래밍 교육과정",
            "데이터 분석 과정", 
            "AI 머신러닝 교육",
            "웹 개발 강의"
        ]
        
        print(f"  임베딩 생성 중...")
        embeddings = self._get_embeddings(test_queries)
        
        if not embeddings:
            print("  ⚠️ 임베딩 생성 실패, 대안 검색 방법 시도...")
            return self._test_simple_data_retrieval(collection_identifier)
        
        successful_tests = 0
        total_results = 0
        
        for i, (query, embedding) in enumerate(zip(test_queries, embeddings), 1):
            print(f"  테스트 {i}: '{query}'")
            
            try:
                search_data = {
                    "query_embeddings": [embedding],
                    "n_results": 3,
                    "include": ["documents", "metadatas"]
                }
                
                response = requests.post(
                    f"{self.pod_base_url}/collections/{collection_identifier}/query",
                    headers=self.headers,
                    json=search_data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    search_results = response.json()
                    documents = search_results.get('documents', [[]])
                    result_count = len(documents[0]) if documents and len(documents) > 0 else 0
                    
                    print(f"    ✅ 성공: {result_count}개 결과")
                    total_results += result_count
                    
                    # 첫 번째 테스트에서 상세 미리보기
                    if result_count > 0 and i == 1:
                        first_doc = documents[0][0]
                        lines = first_doc.split('\n')[:3]  # 첫 3줄만
                        preview = '\n       '.join(lines)
                        print(f"    📄 교육과정 결과 미리보기:")
                        print(f"       {preview}")
                    
                    successful_tests += 1
                else:
                    print(f"    ❌ 실패: HTTP {response.status_code}")
                    print(f"       응답: {response.text[:200]}...")
                    
            except Exception as e:
                print(f"    ❌ 오류: {str(e)}")
        
        print(f"\n📊 교육과정 임베딩 검색 테스트 결과:")
        print(f"   성공한 테스트: {successful_tests}/{len(test_queries)}")
        print(f"   총 검색 결과: {total_results}개")
        
        return successful_tests >= len(test_queries) // 2
    
    def _test_simple_data_retrieval(self, collection_identifier):
        """임베딩 없이 단순 교육과정 데이터 조회 테스트"""
        print(f"  📋 단순 교육과정 데이터 조회 테스트 시도...")
        
        try:
            # 처음 5개 교육과정 문서만 가져오기
            response = requests.post(
                f"{self.pod_base_url}/collections/{collection_identifier}/get",
                headers=self.headers,
                json={
                    "limit": 5,
                    "include": ["documents", "metadatas"]
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                doc_count = len(data.get('documents', []))
                print(f"    ✅ 교육과정 데이터 조회 성공: {doc_count}개 문서 확인")
                
                if doc_count > 0:
                    first_doc = data['documents'][0]
                    preview = first_doc[:200] + "..." if len(first_doc) > 200 else first_doc
                    print(f"    📄 첫 번째 교육과정 문서 미리보기:")
                    print(f"       {preview}")
                
                return doc_count > 0
            else:
                print(f"    ❌ 교육과정 데이터 조회 실패: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"    ❌ 교육과정 데이터 조회 오류: {str(e)}")
            return False
    
    def get_collection_statistics(self, collection_id=None):
        """교육과정 컬렉션 통계 정보"""
        print(f"\n📈 교육과정 컬렉션 통계 정보")
        
        collection_identifier = collection_id if collection_id else self.pod_collection_name
        
        try:
            # 컬렉션의 모든 교육과정 문서 개수 확인 (메타데이터만)
            response = requests.post(
                f"{self.pod_base_url}/collections/{collection_identifier}/get",
                headers=self.headers,
                json={"include": ["metadatas"]},  # 메타데이터만 가져와서 빠르게
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                total_docs = len(data.get('ids', []))
                print(f"  📊 총 교육과정 문서 수: {total_docs}")
                
                # 메타데이터 샘플 분석
                metadatas = data.get('metadatas', [])
                if metadatas:
                    sample_metadata = metadatas[0]
                    print(f"  📊 메타데이터 키: {list(sample_metadata.keys())}")
                    
                    # # 교육과정 카테고리 통계
                    # categories = set()
                    # levels = set()
                    # for meta in metadatas[:100]:  # 처음 100개만 체크
                    #     category = meta.get('category')
                    #     level = meta.get('level')
                    #     if category:
                    #         categories.add(category)
                    #     if level:
                    #         levels.add(level)
                    
                    # print(f"  📚 교육 카테고리 (샘플): {list(categories)[:5]}")
                    # print(f"  📊 난이도 레벨 (샘플): {list(levels)[:5]}")
                
                return total_docs
            else:
                print(f"  ❌ 교육과정 통계 조회 실패: {response.status_code}")
                return 0
                
        except Exception as e:
            print(f"  ❌ 교육과정 통계 조회 중 오류: {str(e)}")
            return 0
    
    def run_full_verification(self):
        """전체 교육과정 검증 실행"""
        print("🚀 교육과정 ChromaDB 업로드 검증을 시작합니다...")
        print(f"🎯 타겟 컬렉션: {self.pod_collection_name}")
        print(f"🌐 Pod URL: {self.pod_base_url}")
        print("-" * 60)
        
        # 1. 교육과정 컬렉션 존재 확인
        collection_id = self.verify_collection_exists()
        
        if not collection_id:
            print("\n❌ 검증 실패: 교육과정 컬렉션이 존재하지 않습니다")
            return False
        
        # 2. 교육과정 검색 기능 테스트
        search_success = self.test_search_functionality(collection_id)
        
        # 3. 교육과정 통계 정보
        doc_count = self.get_collection_statistics(collection_id)
        
        # 4. 최종 결과
        print("\n" + "="*60)
        if search_success and doc_count > 0:
            print("🎉 교육과정 검증 성공!")
            print(f"   ✅ 컬렉션 존재: {self.pod_collection_name}")
            print(f"   ✅ 교육과정 문서 수: {doc_count}")
            print(f"   ✅ 검색 기능: 정상 작동")
            print(f"   ✅ Pod ChromaDB 교육과정 업로드 완료 확인됨!")
            return True
        else:
            print("❌ 교육과정 검증 실패!")
            print("   컬렉션은 존재하지만 검색이나 데이터에 문제가 있을 수 있습니다.")
            return False

def main():
    """메인 실행 함수"""
    # 환경변수 확인
    missing_env = []
    if not os.getenv("CHROMA_AUTH_CREDENTIALS"):
        missing_env.append("CHROMA_AUTH_CREDENTIALS")
    if not os.getenv("OPENAI_API_KEY"):
        missing_env.append("OPENAI_API_KEY")
    
    if missing_env:
        print(f"❌ 필수 환경변수가 설정되지 않았습니다: {missing_env}")
        print("   .env 파일에 다음을 추가하세요:")
        for env in missing_env:
            print(f"   {env}=your_value")
        return
    
    # 교육과정 검증 실행
    verifier = EducationChromaUploadVerifier()
    success = verifier.run_full_verification()
    
    if success:
        print("\n✨ 교육과정 ChromaDB Pod 업로드가 성공적으로 완료되었습니다!")
    else:
        print("\n⚠️ 교육과정 검증에서 문제가 발견되었습니다. 로그를 확인해주세요.")

if __name__ == "__main__":
    main()