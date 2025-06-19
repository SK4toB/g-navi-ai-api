# app/utils/upload_education_vectorstore_to_pod.py
"""
로컬 교육과정 ChromaDB 컬렉션을 Pod ChromaDB로 업로드하는 스크립트
기존 경력 데이터 업로더와 동일한 방식
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

class EducationChromaPodUploader:
    """로컬 교육과정 ChromaDB를 Pod ChromaDB로 업로드"""
    
    def __init__(self):
        # 로컬 교육과정 ChromaDB 설정
        self.local_persist_dir = "app/storage/vector_stores/education_courses"
        self.local_cache_dir = "app/storage/cache/education_embedding_cache"
        
        # Pod ChromaDB 설정
        self.pod_base_url = "https://chromadb-1.skala25a.project.skala-ai.com/api/v1"
        self.pod_auth_credentials = os.getenv("CHROMA_AUTH_CREDENTIALS")
        
        # 컬렉션 이름 설정
        self.local_collection_name = "education_courses"  # 로컬 컬렉션명
        self.pod_collection_name = "gnavi4_education_prod"  # Pod 운영용 컬렉션명
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
        """로컬 교육과정 ChromaDB 컬렉션 로드"""
        print("로컬 교육과정 ChromaDB 컬렉션 로드 중...")
        
        if not os.path.exists(self.local_persist_dir):
            raise FileNotFoundError(f"로컬 교육과정 ChromaDB 디렉토리가 없습니다: {self.local_persist_dir}")
        
        # 캐시된 임베딩 설정
        cached_embeddings = CacheBackedEmbeddings.from_bytes_store(
            self.embeddings,
            LocalFileStore(self.local_cache_dir),
            namespace="education_embeddings"
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
        
        print(f"로컬 교육과정 컬렉션 로드 완료:")
        print(f"  - 문서 수: {len(collection['documents'])}")
        print(f"  - 벡터 차원: {embeddings_info}")
        print(f"  - 메타데이터 수: {len(collection.get('metadatas', []))}")
        print(f"  - ID 수: {len(collection.get('ids', []))}")
        
        # embeddings가 없으면 에러
        if embeddings_data is None or len(embeddings_data) == 0:
            raise Exception("로컬 교육과정 ChromaDB에 embeddings가 없습니다. 벡터 데이터를 다시 생성해주세요.")
        
        return collection
    
    def create_pod_collection(self):
        """Pod ChromaDB에 새 교육과정 컬렉션 생성"""
        print(f"Pod ChromaDB에 교육과정 컬렉션 생성 중: {self.pod_collection_name}")
        
        # 기존 컬렉션 삭제 (있다면)
        try:
            delete_url = f"{self.pod_base_url}/collections/{self.pod_collection_name}"
            response = requests.delete(delete_url, headers=self.headers, timeout=30)
            if response.status_code == 200:
                print(f"  기존 교육과정 컬렉션 삭제됨: {self.pod_collection_name}")
        except:
            pass  # 없어도 상관없음
        
        # 새 컬렉션 생성
        create_data = {
            "name": self.pod_collection_name,
            "metadata": {
                "description": "gnavi4 education courses data",
                "dimensions": 1536,
                "embedding_model": "text-embedding-3-small",
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
            self.pod_collection_id = collection_info.get("id")
            print(f"  새 교육과정 컬렉션 생성 성공: {self.pod_collection_name}")
            print(f"  컬렉션 ID: {self.pod_collection_id}")
            return True
        else:
            print(f"  교육과정 컬렉션 생성 실패: {response.status_code} - {response.text}")
            return False
    
    def upload_documents_batch(self, collection_data: Dict, batch_size: int = 25):
        """교육과정 문서를 배치로 Pod ChromaDB에 업로드"""
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
                if isinstance(embeddings[0], np.ndarray):
                    embeddings = [emb.tolist() if isinstance(emb, np.ndarray) else emb for emb in embeddings]
        
        total_docs = len(documents)
        print(f"총 {total_docs}개 교육과정 문서를 {batch_size}개씩 배치 업로드 시작...")
        print(f"예상 총 배치 수: {(total_docs + batch_size - 1) // batch_size}")
        
        success_count = 0
        
        # 배치별 업로드
        for i in range(0, total_docs, batch_size):
            batch_end = min(i + batch_size, total_docs)
            batch_num = i // batch_size + 1
            
            # 배치 데이터 준비
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
                    collection_identifier = self.pod_collection_id if self.pod_collection_id else self.pod_collection_name
                    
                    response = requests.post(
                        f"{self.pod_base_url}/collections/{collection_identifier}/add",
                        headers=self.headers,
                        json=batch_data,
                        timeout=180
                    )
                    
                    if response.status_code in [200, 201]:
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
        
        print(f"\n🎉 모든 교육과정 문서 업로드 완료!")
        print(f"   성공한 배치: {success_count}/{(total_docs + batch_size - 1) // batch_size}")
        return True
    

    
    def run_upload(self):
        """전체 교육과정 업로드 프로세스 실행"""
        try:
            # 1. 로컬 교육과정 컬렉션 로드
            collection_data = self.load_local_collection()
            
            # 2. Pod에 교육과정 컬렉션 생성
            if not self.create_pod_collection():
                raise Exception("Pod 교육과정 컬렉션 생성 실패")
            
            # 3. 교육과정 문서 업로드
            if not self.upload_documents_batch(collection_data):
                raise Exception("교육과정 문서 업로드 실패")
            
            print("\n🎉 교육과정 ChromaDB 컬렉션 업로드가 완료되었습니다!")
            print(f"   로컬: {self.local_collection_name}")
            print(f"   Pod: {self.pod_collection_name}")
            print("\n💡 업로드 결과를 검증하려면 다음 명령어를 실행하세요:")
            print("   python app/utils/verify_education_chroma_upload.py")
            
        except Exception as e:
            print(f"\n❌ 교육과정 업로드 실패: {str(e)}")
            raise

def main():
    """메인 실행 함수"""
    print("🚀 교육과정 ChromaDB 컬렉션 Pod 업로드를 시작합니다...")
    
    # 환경변수 확인
    required_env = ["OPENAI_API_KEY", "CHROMA_AUTH_CREDENTIALS"]
    missing_env = [env for env in required_env if not os.getenv(env)]
    
    if missing_env:
        print(f"❌ 필수 환경변수가 없습니다: {missing_env}")
        print("   .env 파일에 다음을 추가하세요:")
        for env in missing_env:
            print(f"   {env}=your_value_here")
        return
    
    # 교육과정 업로드 실행
    uploader = EducationChromaPodUploader()
    uploader.run_upload()

if __name__ == "__main__":
    main()