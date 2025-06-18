# upload_to_pod_chroma.py
"""
로컬 ChromaDB 컬렉션을 Pod ChromaDB로 업로드하는 스크립트
"""

import os
import requests
import base64
import json
import pandas as pd
from typing import List, Dict, Any
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.storage import LocalFileStore
from langchain.embeddings import CacheBackedEmbeddings
from dotenv import load_dotenv

load_dotenv()

class ChromaPodUploader:
    """로컬 ChromaDB를 Pod ChromaDB로 업로드"""
    
    def __init__(self):
        # 로컬 ChromaDB 설정
        self.local_persist_dir = "app/storage/vector_stores/career_data"
        self.local_cache_dir = "app/storage/cache/embedding_cache"
        
        # Pod ChromaDB 설정
        self.pod_base_url = "https://chromadb-1.skala25a.project.skala-ai.com/api/v1"
        self.pod_auth_credentials = os.getenv("CHROMA_AUTH_CREDENTIALS")
        
        # 컬렉션 이름 설정
        self.local_collection_name = "career_history"
        self.pod_collection_name = "gnavi4_career_history_prod"  # 운영용
        
        # 임베딩 설정
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            dimensions=1536
        )
        
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
    
    def load_local_collection(self):
        """로컬 ChromaDB 컬렉션 로드"""
        print("로컬 ChromaDB 컬렉션 로드 중...")
        
        if not os.path.exists(self.local_persist_dir):
            raise FileNotFoundError(f"로컬 ChromaDB 디렉토리가 없습니다: {self.local_persist_dir}")
        
        # 캐시된 임베딩 설정
        cached_embeddings = CacheBackedEmbeddings.from_bytes_store(
            self.embeddings,
            LocalFileStore(self.local_cache_dir),
            namespace="career_embeddings"
        )
        
        # 로컬 vectorstore 로드
        vectorstore = Chroma(
            persist_directory=self.local_persist_dir,
            embedding_function=cached_embeddings,
            collection_name=self.local_collection_name
        )
        
        # 모든 문서와 메타데이터 가져오기
        collection = vectorstore.get()
        
        print(f"로컬 컬렉션 로드 완료:")
        print(f"  - 문서 수: {len(collection['documents'])}")
        print(f"  - 벡터 차원: {len(collection['embeddings'][0]) if collection['embeddings'] else 'N/A'}")
        
        return collection
    
    def create_pod_collection(self):
        """Pod ChromaDB에 새 컬렉션 생성"""
        print(f"Pod ChromaDB에 컬렉션 생성 중: {self.pod_collection_name}")
        
        # 기존 컬렉션 삭제 (있다면)
        try:
            delete_url = f"{self.pod_base_url}/collections/{self.pod_collection_name}"
            response = requests.delete(delete_url, headers=self.headers, timeout=30)
            if response.status_code == 200:
                print(f"  기존 컬렉션 삭제됨: {self.pod_collection_name}")
        except:
            pass  # 없어도 상관없음
        
        # 새 컬렉션 생성
        create_data = {
            "name": self.pod_collection_name,
            "metadata": {
                "description": "G.Navi 경력 데이터 프로덕션 컬렉션",
                "created_from": "local_upload",
                "embedding_model": "text-embedding-3-small",
                "dimensions": 1536
            }
        }
        
        response = requests.post(
            f"{self.pod_base_url}/collections",
            headers=self.headers,
            json=create_data,
            timeout=30
        )
        
        if response.status_code == 200:
            print(f"  새 컬렉션 생성 성공: {self.pod_collection_name}")
            return True
        else:
            print(f"  컬렉션 생성 실패: {response.status_code} - {response.text}")
            return False
    
    def upload_documents_batch(self, collection_data: Dict, batch_size: int = 25):
        """문서를 배치로 Pod ChromaDB에 업로드 (71.7MB 최적화)"""
        documents = collection_data['documents']
        embeddings = collection_data['embeddings']
        metadatas = collection_data['metadatas']
        ids = collection_data['ids']
        
        total_docs = len(documents)
        print(f"총 {total_docs}개 문서를 {batch_size}개씩 배치 업로드 시작...")
        print(f"예상 총 배치 수: {(total_docs + batch_size - 1) // batch_size}")
        
        success_count = 0
        
        # 배치별 업로드
        for i in range(0, total_docs, batch_size):
            batch_end = min(i + batch_size, total_docs)
            batch_num = i // batch_size + 1
            
            batch_data = {
                "ids": ids[i:batch_end],
                "documents": documents[i:batch_end],
                "embeddings": embeddings[i:batch_end],
                "metadatas": metadatas[i:batch_end] if metadatas else None
            }
            
            # 배치 크기 로깅
            batch_size_mb = len(str(batch_data).encode('utf-8')) / 1024 / 1024
            print(f"  배치 {batch_num}: {i+1}-{batch_end}/{total_docs} ({batch_size_mb:.2f}MB)")
            
            # API 호출 (재시도 로직 포함)
            max_retries = 3
            for retry in range(max_retries):
                try:
                    response = requests.post(
                        f"{self.pod_base_url}/collections/{self.pod_collection_name}/add",
                        headers=self.headers,
                        json=batch_data,
                        timeout=180  # 71.7MB를 위해 타임아웃 증가
                    )
                    
                    if response.status_code == 200:
                        success_count += 1
                        print(f"    ✅ 배치 {batch_num} 업로드 완료 (시도 {retry + 1})")
                        break
                    else:
                        print(f"    ❌ 배치 {batch_num} 업로드 실패: {response.status_code}")
                        if retry < max_retries - 1:
                            print(f"    🔄 재시도 {retry + 2}/{max_retries}")
                            continue
                        else:
                            print(f"    💥 최대 재시도 초과. 오류: {response.text}")
                            return False
                            
                except requests.exceptions.Timeout:
                    print(f"    ⏰ 배치 {batch_num} 타임아웃 (시도 {retry + 1})")
                    if retry < max_retries - 1:
                        print(f"    🔄 재시도 {retry + 2}/{max_retries}")
                        continue
                    else:
                        print(f"    💥 최대 재시도 초과 (타임아웃)")
                        return False
                        
                except Exception as e:
                    print(f"    ❌ 배치 {batch_num} 예외 발생: {str(e)}")
                    if retry < max_retries - 1:
                        print(f"    🔄 재시도 {retry + 2}/{max_retries}")
                        continue
                    else:
                        print(f"    💥 최대 재시도 초과")
                        return False
        
        print(f"\n🎉 모든 문서 업로드 완료!")
        print(f"   성공한 배치: {success_count}/{(total_docs + batch_size - 1) // batch_size}")
        return True
    
    def verify_upload(self):
        """업로드 결과 검증"""
        print("업로드 결과 검증 중...")
        
        # 컬렉션 정보 조회
        response = requests.get(
            f"{self.pod_base_url}/collections/{self.pod_collection_name}",
            headers=self.headers,
            timeout=30
        )
        
        if response.status_code == 200:
            collection_info = response.json()
            print(f"  컬렉션 이름: {collection_info.get('name')}")
            print(f"  문서 수: {collection_info.get('metadata', {}).get('count', 'N/A')}")
            
            # 샘플 검색 테스트
            search_data = {
                "query_texts": ["EMP-525170"],
                "n_results": 2
            }
            
            search_response = requests.post(
                f"{self.pod_base_url}/collections/{self.pod_collection_name}/query",
                headers=self.headers,
                json=search_data,
                timeout=30
            )
            
            if search_response.status_code == 200:
                search_results = search_response.json()
                result_count = len(search_results.get('documents', [[]])[0])
                print(f"  검색 테스트: {result_count}개 결과 반환")
                
                if result_count > 0:
                    print("✅ 업로드 및 검증 성공!")
                    return True
                else:
                    print("❌ 검색 결과가 없습니다")
                    return False
            else:
                print(f"❌ 검색 테스트 실패: {search_response.status_code}")
                return False
        else:
            print(f"❌ 컬렉션 정보 조회 실패: {response.status_code}")
            return False
    
    def run_upload(self):
        """전체 업로드 프로세스 실행"""
        try:
            # 1. 로컬 컬렉션 로드
            collection_data = self.load_local_collection()
            
            # # 2. Pod에 컬렉션 생성
            # if not self.create_pod_collection():
            #     raise Exception("Pod 컬렉션 생성 실패")
            
            # # 3. 문서 업로드
            # if not self.upload_documents_batch(collection_data):
            #     raise Exception("문서 업로드 실패")
            
            # # 4. 업로드 검증
            # if not self.verify_upload():
            #     raise Exception("업로드 검증 실패")
            
            # print("\n🎉 ChromaDB 컬렉션 업로드가 완료되었습니다!")
            # print(f"   로컬: {self.local_collection_name}")
            # print(f"   Pod: {self.pod_collection_name}")
            
        except Exception as e:
            print(f"\n❌ 업로드 실패: {str(e)}")
            raise

def main():
    """메인 실행 함수"""
    print("🚀 ChromaDB 컬렉션 Pod 업로드를 시작합니다...")
    
    # 환경변수 확인
    required_env = ["OPENAI_API_KEY", "CHROMA_AUTH_CREDENTIALS"]
    missing_env = [env for env in required_env if not os.getenv(env)]
    
    if missing_env:
        print(f"❌ 필수 환경변수가 없습니다: {missing_env}")
        print("   .env 파일에 다음을 추가하세요:")
        for env in missing_env:
            print(f"   {env}=your_value_here")
        return
    
    # 업로드 실행
    uploader = ChromaPodUploader()
    uploader.run_upload()

if __name__ == "__main__":
    main()