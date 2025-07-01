# upload_to_pod_chroma.py
"""
로컬 ChromaDB 컬렉션을 K8s Pod ChromaDB로 업로드하는 스크립트 (내부 네트워크용)
"""

import os
import requests
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
    """로컬 ChromaDB를 K8s Pod ChromaDB로 업로드"""
    
    def __init__(self):
        # 로컬 ChromaDB 설정
        self.local_persist_dir = "app/storage/vector_stores/career_data"
        self.local_cache_dir = "app/storage/cache/embedding_cache"
        
        # K8s 내부 ChromaDB 설정
        self.pod_base_url = self._get_chromadb_url()
        
        # 컬렉션 이름 설정
        self.local_collection_name = "career_history"
        self.pod_collection_name = "gnavi4_career_history_prod"  # 운영용
        
        # 임베딩 설정
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            dimensions=1536
        )
        
        # K8s 내부에서는 인증 불필요
        self.headers = {"Content-Type": "application/json"}
        
    def _get_chromadb_url(self) -> str:
        """ChromaDB URL 결정 (환경 감지)"""
        
        # K8s 환경 감지
        if os.path.exists('/var/run/secrets/kubernetes.io/serviceaccount'):
            # K8s Pod 내부 - 서비스명 사용
            base_url = "http://chromadb-1:8000/api/v1"
            print("🎯 K8s 환경: 내부 서비스 연결")
        else:
            # 로컬 환경 - 포트포워딩 사용
            base_url = "http://localhost:8000/api/v1"
            print("💻 로컬 환경: 포트포워딩 연결")
            print("   포트포워딩 필요: kubectl port-forward svc/chromadb-1 8000:8000 -n sk-team-04")
        
        print(f"   ChromaDB URL: {base_url}")
        return base_url
    
    def test_connection(self):
        """ChromaDB 연결 테스트"""
        print("🔍 ChromaDB 연결 테스트...")
        
        try:
            # v1 heartbeat 시도
            response = requests.get(f"{self.pod_base_url}/heartbeat", timeout=10)
            
            if response.status_code == 200:
                print("   ✅ v1 API 연결 성공")
                return True
            else:
                print(f"   ❌ v1 API 연결 실패: {response.status_code}")
                
                # v2 API로 시도
                v2_url = self.pod_base_url.replace('/api/v1', '/api/v2')
                response = requests.get(f"{v2_url}/heartbeat", timeout=10)
                
                if response.status_code == 200:
                    print("   ✅ v2 API 연결 성공, URL 업데이트")
                    self.pod_base_url = v2_url
                    return True
                else:
                    print(f"   ❌ v2 API도 연결 실패: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"   ❌ 연결 테스트 실패: {e}")
            return False
    
    def load_local_collection(self):
        """로컬 ChromaDB 컬렉션 로드"""
        print("📚 로컬 ChromaDB 컬렉션 로드 중...")
        
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
        
        # embeddings 확인
        embeddings_info = "N/A"
        embeddings_data = collection.get('embeddings')
        
        if embeddings_data is not None and len(embeddings_data) > 0:
            first_embedding = embeddings_data[0]
            if first_embedding is not None and len(first_embedding) > 0:
                embeddings_info = len(first_embedding)
        
        print(f"   로컬 컬렉션 로드 완료:")
        print(f"   - 문서 수: {len(collection['documents'])}")
        print(f"   - 벡터 차원: {embeddings_info}")
        print(f"   - 메타데이터 수: {len(collection.get('metadatas', []))}")
        print(f"   - ID 수: {len(collection.get('ids', []))}")
        
        # embeddings가 없으면 에러
        if embeddings_data is None or len(embeddings_data) == 0:
            raise Exception("로컬 ChromaDB에 embeddings가 없습니다. 벡터 데이터를 다시 생성해주세요.")
        
        return collection
    
    def create_pod_collection(self):
        """Pod ChromaDB에 새 컬렉션 생성"""
        print(f"🏗️  Pod ChromaDB에 컬렉션 생성: {self.pod_collection_name}")
        
        # 기존 컬렉션 삭제 (있다면)
        try:
            delete_url = f"{self.pod_base_url}/collections/{self.pod_collection_name}"
            response = requests.delete(delete_url, headers=self.headers, timeout=30)
            if response.status_code == 200:
                print(f"   🗑️  기존 컬렉션 삭제됨: {self.pod_collection_name}")
        except:
            pass  # 없어도 상관없음
        
        # 새 컬렉션 생성
        create_data = {
            "name": self.pod_collection_name,
            "metadata": {
                "description": "gnavi4 career history data - internal upload",
                "dimensions": 1536,
                "embedding_model": "text-embedding-3-small",
                "upload_method": "k8s_internal"
            }
        }
        
        response = requests.post(
            f"{self.pod_base_url}/collections",
            headers=self.headers,
            json=create_data,
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            collection_info = response.json()
            print(f"   ✅ 새 컬렉션 생성 성공: {self.pod_collection_name}")
            return True
        else:
            print(f"   ❌ 컬렉션 생성 실패: {response.status_code} - {response.text}")
            
            # v1 API가 실패하면 v2로 시도
            if 'api/v1' in self.pod_base_url:
                print("   🔄 v2 API로 재시도...")
                self.pod_base_url = self.pod_base_url.replace('/api/v1', '/api/v2')
                
                response = requests.post(
                    f"{self.pod_base_url}/collections",
                    headers=self.headers,
                    json=create_data,
                    timeout=30
                )
                
                if response.status_code in [200, 201]:
                    print(f"   ✅ v2 API로 컬렉션 생성 성공")
                    return True
                else:
                    print(f"   ❌ v2 API도 실패: {response.status_code}")
            
            return False
    
    def upload_documents_batch(self, collection_data: Dict, batch_size: int = 25):
        """문서를 배치로 Pod ChromaDB에 업로드"""
        documents = collection_data['documents']
        embeddings = collection_data['embeddings']
        metadatas = collection_data['metadatas']
        ids = collection_data['ids']
        
        # numpy 배열을 리스트로 변환
        if embeddings is not None:
            import numpy as np
            if isinstance(embeddings, np.ndarray):
                embeddings = embeddings.tolist()
            elif isinstance(embeddings, list) and len(embeddings) > 0:
                if isinstance(embeddings[0], np.ndarray):
                    embeddings = [emb.tolist() if isinstance(emb, np.ndarray) else emb for emb in embeddings]
        
        total_docs = len(documents)
        print(f"📤 총 {total_docs}개 문서를 {batch_size}개씩 배치 업로드 시작...")
        
        success_count = 0
        
        # 배치별 업로드
        for i in range(0, total_docs, batch_size):
            batch_end = min(i + batch_size, total_docs)
            batch_num = i // batch_size + 1
            
            batch_data = {
                "ids": ids[i:batch_end],
                "documents": documents[i:batch_end],
                "embeddings": embeddings[i:batch_end] if embeddings else None,
                "metadatas": metadatas[i:batch_end] if metadatas else None
            }
            
            print(f"   📦 배치 {batch_num}: {i+1}-{batch_end}/{total_docs}")
            
            # API 호출 (재시도 로직)
            max_retries = 3
            for retry in range(max_retries):
                try:
                    response = requests.post(
                        f"{self.pod_base_url}/collections/{self.pod_collection_name}/add",
                        headers=self.headers,
                        json=batch_data,
                        timeout=120  # 내부 네트워크이므로 타임아웃 단축
                    )
                    
                    if response.status_code in [200, 201]:
                        success_count += 1
                        print(f"      ✅ 배치 {batch_num} 업로드 완료")
                        break
                    else:
                        print(f"      ❌ 배치 {batch_num} 실패: {response.status_code}")
                        if retry < max_retries - 1:
                            print(f"      🔄 재시도 {retry + 2}/{max_retries}")
                        else:
                            print(f"      💥 최대 재시도 초과")
                            return False
                            
                except requests.exceptions.Timeout:
                    print(f"      ⏰ 배치 {batch_num} 타임아웃")
                    if retry < max_retries - 1:
                        print(f"      🔄 재시도 {retry + 2}/{max_retries}")
                    else:
                        return False
                        
                except Exception as e:
                    print(f"      ❌ 배치 {batch_num} 예외: {str(e)}")
                    if retry < max_retries - 1:
                        print(f"      🔄 재시도 {retry + 2}/{max_retries}")
                    else:
                        return False
        
        print(f"   🎉 모든 배치 업로드 완료! ({success_count}/{(total_docs + batch_size - 1) // batch_size})")
        return True
    
    def verify_upload(self):
        """업로드 결과 검증"""
        print("🔍 업로드 결과 검증 중...")
        
        try:
            # 검색 테스트로 검증
            search_data = {
                "query_texts": ["경력"],
                "n_results": 3
            }
            
            response = requests.post(
                f"{self.pod_base_url}/collections/{self.pod_collection_name}/query",
                headers=self.headers,
                json=search_data,
                timeout=30
            )
            
            if response.status_code == 200:
                results = response.json()
                documents = results.get('documents', [[]])
                result_count = len(documents[0]) if documents and len(documents) > 0 else 0
                
                print(f"   ✅ 검색 테스트 성공: {result_count}개 결과")
                
                if result_count > 0:
                    first_doc = documents[0][0] if documents[0] else ""
                    preview = first_doc[:100] + "..." if len(first_doc) > 100 else first_doc
                    print(f"   📄 첫 번째 결과: {preview}")
                    return True
                else:
                    print("   ❌ 검색 결과 없음")
                    return False
            else:
                print(f"   ❌ 검색 테스트 실패: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   ❌ 검증 중 예외: {str(e)}")
            return False
    
    def run_upload(self):
        """전체 업로드 프로세스 실행"""
        try:
            print("🚀 K8s 내부 ChromaDB 업로드 시작")
            print("=" * 50)
            
            # 1. 연결 테스트
            if not self.test_connection():
                raise Exception("ChromaDB 연결 실패")
            
            # 2. 로컬 컬렉션 로드
            collection_data = self.load_local_collection()
            
            # 3. Pod에 컬렉션 생성
            if not self.create_pod_collection():
                raise Exception("Pod 컬렉션 생성 실패")
            
            # 4. 문서 업로드
            if not self.upload_documents_batch(collection_data):
                raise Exception("문서 업로드 실패")
            
            # 5. 업로드 검증
            if not self.verify_upload():
                raise Exception("업로드 검증 실패")
            
            print("\n🎉 K8s 내부 ChromaDB 업로드 완료!")
            print(f"   로컬: {self.local_collection_name}")
            print(f"   Pod: {self.pod_collection_name}")
            print(f"   URL: {self.pod_base_url}")
            
        except Exception as e:
            print(f"\n❌ 업로드 실패: {str(e)}")
            raise

def main():
    """메인 실행 함수"""
    print("🚀 K8s 내부 ChromaDB 컬렉션 업로드")
    
    # OpenAI API 키만 필요 (인증 불필요)
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY 환경변수가 필요합니다")
        return
    
    # 업로드 실행
    uploader = ChromaPodUploader()
    uploader.run_upload()

if __name__ == "__main__":
    main()