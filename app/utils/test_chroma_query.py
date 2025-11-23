# test_chroma_query_simple.py
"""
ChromaDB v2 Multi-tenant 간단 조회 테스트
"""

import requests
import json
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
import os

load_dotenv()

class ChromaQueryTestSimple:
    """ChromaDB v2 Multi-tenant 간단 조회 테스트"""
    
    def __init__(self):
        # Pod ChromaDB v2 Multi-tenant 설정
        self.base_url = "https://sk-gnavi4.skala25a.project.skala-ai.com/vector/api/v2"
        self.tenant = "default_tenant"
        self.database = "default_database"
        self.collections_url = f"{self.base_url}/tenants/{self.tenant}/databases/{self.database}/collections"
        
        # 컬렉션 정보 (업로드에서 확인된 값들)
        self.pod_collection_name = "gnavi4_career_history_prod"
        self.pod_collection_id = "ed42e97e-12ec-44cf-92e0-96988885b997"
        
        # 임베딩 설정
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            dimensions=1536
        )
        
        # 헤더 설정
        self.headers = {"Content-Type": "application/json"}
    
    def get_collection_count(self):
        """문서 개수 조회"""
        print(" 문서 개수 조회 중...")
        
        try:
            count_url = f"{self.collections_url}/{self.pod_collection_id}/count"
            response = requests.get(count_url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                count = response.json()
                print(f" 문서 개수: {count}개")
                return count
            else:
                print(f" 문서 개수 조회 실패: {response.status_code}")
                return None
                
        except Exception as e:
            print(f" 예외 발생: {str(e)}")
            return None
    
    def search_documents(self, query_text="경력", n_results=3):
        """문서 검색"""
        print(f" 문서 검색 중: '{query_text}'")
        
        try:
            # 임베딩 생성
            query_embedding = self.embeddings.embed_query(query_text)
            
            # 검색 요청
            query_data = {
                "query_embeddings": [query_embedding],
                "n_results": n_results,
                "include": ["documents", "metadatas"]
            }
            
            search_url = f"{self.collections_url}/{self.pod_collection_id}/query"
            response = requests.post(search_url, headers=self.headers, json=query_data, timeout=30)
            
            if response.status_code == 200:
                results = response.json()
                documents = results.get('documents', [[]])
                metadatas = results.get('metadatas', [[]])
                
                result_count = len(documents[0]) if documents and len(documents) > 0 else 0
                print(f" 검색 성공: {result_count}개 결과")
                
                # 결과 출력
                for i in range(result_count):
                    doc = documents[0][i] if documents[0] else ""
                    meta = metadatas[0][i] if metadatas and metadatas[0] else {}
                    
                    print(f"\n 결과 {i+1}:")
                    print(f"   내용: {doc[:150]}...")
                    print(f"   메타데이터: {meta}")
                
                return results
            else:
                print(f" 검색 실패: {response.status_code}")
                print(f"   응답: {response.text}")
                return None
                
        except Exception as e:
            print(f" 예외 발생: {str(e)}")
            return None
    
    def get_all_documents(self, limit=5):
        """모든 문서 조회 (제한)"""
        print(f" 문서 조회 중 (최대 {limit}개)...")
        
        try:
            get_data = {
                "limit": limit,
                "include": ["documents", "metadatas"]
            }
            
            get_url = f"{self.collections_url}/{self.pod_collection_id}/get"
            response = requests.post(get_url, headers=self.headers, json=get_data, timeout=30)
            
            if response.status_code == 200:
                results = response.json()
                documents = results.get('documents', [])
                metadatas = results.get('metadatas', [])
                
                print(f" 문서 조회 성공: {len(documents)}개")
                
                # 결과 출력
                for i, doc in enumerate(documents[:3]):  # 처음 3개만 출력
                    meta = metadatas[i] if i < len(metadatas) else {}
                    print(f"\n 문서 {i+1}:")
                    print(f"   내용: {doc[:150]}...")
                    print(f"   메타데이터: {meta}")
                
                return results
            else:
                print(f" 문서 조회 실패: {response.status_code}")
                print(f"   응답: {response.text}")
                return None
                
        except Exception as e:
            print(f" 예외 발생: {str(e)}")
            return None
    
    def run_tests(self):
        """간단한 테스트 실행"""
        print(" ChromaDB 간단 테스트 시작")
        print("=" * 50)
        
        # 1. 문서 개수 확인
        count = self.get_collection_count()
        
        print("\n" + "=" * 50)
        
        # 2. 검색 테스트
        search_results = self.search_documents("경력")
        
        print("\n" + "=" * 50)
        
        # 3. 문서 직접 조회
        get_results = self.get_all_documents(3)
        
        print("\n" + "=" * 50)
        print(" 테스트 결과:")
        print(f"  문서 개수: {'' if count else ''}")
        print(f"  검색 기능: {'' if search_results else ''}")
        print(f"  문서 조회: {'' if get_results else ''}")

def main():
    """메인 실행 함수"""
    if not os.getenv("OPENAI_API_KEY"):
        print(" OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        return
    
    tester = ChromaQueryTestSimple()
    tester.run_tests()

if __name__ == "__main__":
    main()