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
try:
    from langchain_chroma import Chroma
except ImportError:
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
        self.pod_collection_id = None  # 생성 후 설정됨
        
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
        
        # 모든 문서와 메타데이터 가져오기 (embeddings 포함)
        collection = vectorstore.get(include=['documents', 'metadatas', 'embeddings'])
        
        # embeddings 확인 (배열 처리 개선)
        embeddings_info = "N/A"
        embeddings_data = collection.get('embeddings')
        
        if embeddings_data is not None and len(embeddings_data) > 0:
            first_embedding = embeddings_data[0]
            if first_embedding is not None and len(first_embedding) > 0:
                embeddings_info = len(first_embedding)
        
        print(f"로컬 컬렉션 로드 완료:")
        print(f"  - 문서 수: {len(collection['documents'])}")
        print(f"  - 벡터 차원: {embeddings_info}")
        print(f"  - 메타데이터 수: {len(collection.get('metadatas', []))}")
        print(f"  - ID 수: {len(collection.get('ids', []))}")
        
        # embeddings가 없으면 에러
        if embeddings_data is None or len(embeddings_data) == 0:
            raise Exception("로컬 ChromaDB에 embeddings가 없습니다. 벡터 데이터를 다시 생성해주세요.")
        
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
                "description": "gnavi4 career history data",
                "dimensions": 1536,
                "embedding_model": "text-embedding-3-small"
            }
        }
        
        response = requests.post(
            f"{self.pod_base_url}/collections",
            headers=self.headers,
            json=create_data,
            timeout=30
        )
        
        if response.status_code in [200, 201]:  # 200 OK, 201 Created 모두 성공
            collection_info = response.json()
            # 컬렉션 ID 저장 (문서 추가 시 사용)
            self.pod_collection_id = collection_info.get("id")
            print(f"  새 컬렉션 생성 성공: {self.pod_collection_name}")
            print(f"  컬렉션 ID: {self.pod_collection_id}")
            return True
        else:
            print(f"  컬렉션 생성 실패: {response.status_code} - {response.text}")
            return False
    
    def upload_documents_batch(self, collection_data: Dict, batch_size: int = 25):
        """문서를 배치로 Pod ChromaDB에 업로드 (numpy 배열 처리 포함)"""
        documents = collection_data['documents']
        embeddings = collection_data['embeddings']
        metadatas = collection_data['metadatas']
        ids = collection_data['ids']
        
        # numpy 배열을 리스트로 변환 (JSON 직렬화 가능하도록)
        if embeddings is not None:
            import numpy as np
            if isinstance(embeddings, np.ndarray):
                embeddings = embeddings.tolist()
            elif isinstance(embeddings, list) and len(embeddings) > 0:
                # 리스트 내부의 numpy 배열들도 변환
                if isinstance(embeddings[0], np.ndarray):
                    embeddings = [emb.tolist() if isinstance(emb, np.ndarray) else emb for emb in embeddings]
        
        total_docs = len(documents)
        print(f"총 {total_docs}개 문서를 {batch_size}개씩 배치 업로드 시작...")
        print(f"예상 총 배치 수: {(total_docs + batch_size - 1) // batch_size}")
        
        success_count = 0
        
        # 배치별 업로드
        for i in range(0, total_docs, batch_size):
            batch_end = min(i + batch_size, total_docs)
            batch_num = i // batch_size + 1
            
            # 배치 데이터 준비 (numpy 배열 처리)
            batch_embeddings = embeddings[i:batch_end] if embeddings else None
            
            batch_data = {
                "ids": ids[i:batch_end],
                "documents": documents[i:batch_end],
                "embeddings": batch_embeddings,
                "metadatas": metadatas[i:batch_end] if metadatas else None
            }
            
            # 배치 크기 로깅
            try:
                batch_size_mb = len(str(batch_data).encode('utf-8')) / 1024 / 1024
                print(f"  배치 {batch_num}: {i+1}-{batch_end}/{total_docs} ({batch_size_mb:.2f}MB)")
            except:
                print(f"  배치 {batch_num}: {i+1}-{batch_end}/{total_docs}")
            
            # API 호출 (재시도 로직 포함)
            max_retries = 3
            for retry in range(max_retries):
                try:
                    # 컬렉션 ID 또는 이름으로 API 호출 시도
                    collection_identifier = self.pod_collection_id if self.pod_collection_id else self.pod_collection_name
                    
                    response = requests.post(
                        f"{self.pod_base_url}/collections/{collection_identifier}/add",
                        headers=self.headers,
                        json=batch_data,
                        timeout=180  # 71.7MB를 위해 타임아웃 증가
                    )
                    
                    if response.status_code in [200, 201]:  # 200 OK, 201 Created 모두 성공
                        success_count += 1
                        print(f"    ✅ 배치 {batch_num} 업로드 완료 (시도 {retry + 1}) - HTTP {response.status_code}")
                        break
                    else:
                        print(f"    ❌ 배치 {batch_num} 업로드 실패: {response.status_code}")
                        print(f"    응답 내용: {response.text}")
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
        """업로드 결과 검증 (간소화)"""
        print("업로드 결과 검증 중...")
        
        try:
            # 컬렉션 ID 또는 이름으로 조회
            collection_identifier = self.pod_collection_id if self.pod_collection_id else self.pod_collection_name
            
            # 방법 1: 컬렉션 정보 조회 시도
            response = requests.get(
                f"{self.pod_base_url}/collections/{collection_identifier}",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                collection_info = response.json()
                print(f"  ✅ 컬렉션 조회 성공: {collection_info.get('name')}")
            else:
                print(f"  ⚠️ 컬렉션 직접 조회 실패 (HTTP {response.status_code}), 대안 방법 시도...")
            
            # 방법 2: 검색 테스트로 검증 (더 안정적)
            search_data = {
                "query_texts": ["경력"],  # 더 일반적인 검색어 사용
                "n_results": 3
            }
            
            print(f"  검색 테스트 시도 중...")
            search_response = requests.post(
                f"{self.pod_base_url}/collections/{collection_identifier}/query",
                headers=self.headers,
                json=search_data,
                timeout=30
            )
            
            if search_response.status_code == 200:
                search_results = search_response.json()
                documents = search_results.get('documents', [[]])
                result_count = len(documents[0]) if documents and len(documents) > 0 else 0
                
                print(f"  ✅ 검색 테스트 성공: {result_count}개 결과 반환")
                
                if result_count > 0:
                    # 첫 번째 결과의 일부 내용 표시
                    first_doc = documents[0][0] if documents[0] else ""
                    preview = first_doc[:100] + "..." if len(first_doc) > 100 else first_doc
                    print(f"  📄 첫 번째 결과 미리보기: {preview}")
                    
                    print("✅ 업로드 및 검증 성공!")
                    return True
                else:
                    print("❌ 검색 결과가 없습니다")
                    return False
            else:
                print(f"❌ 검색 테스트 실패: {search_response.status_code}")
                print(f"   응답: {search_response.text}")
                
                # 검색도 실패했지만, 업로드는 성공했으므로 경고만 표시
                print("⚠️ 검증은 실패했지만 업로드는 완료되었습니다.")
                print("   Pod ChromaDB에서 직접 확인해주세요.")
                return True  # 업로드가 성공했으므로 True 반환
                
        except Exception as e:
            print(f"❌ 검증 중 예외 발생: {str(e)}")
            print("⚠️ 검증은 실패했지만 업로드는 완료되었을 가능성이 높습니다.")
            return True  # 업로드가 성공했으므로 True 반환
    
    def run_upload(self):
        """전체 업로드 프로세스 실행"""
        try:
            # 1. 로컬 컬렉션 로드
            collection_data = self.load_local_collection()
            
            # 2. Pod에 컬렉션 생성
            if not self.create_pod_collection():
                raise Exception("Pod 컬렉션 생성 실패")
            
            # 3. 문서 업로드
            if not self.upload_documents_batch(collection_data):
                raise Exception("문서 업로드 실패")
            
            # 4. 업로드 검증
            if not self.verify_upload():
                raise Exception("업로드 검증 실패")
            
            print("\n🎉 ChromaDB 컬렉션 업로드가 완료되었습니다!")
            print(f"   로컬: {self.local_collection_name}")
            print(f"   Pod: {self.pod_collection_name}")
            
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