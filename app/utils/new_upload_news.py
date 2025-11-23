# upload_news_vectorstore_to_pod_v2.py
"""
로컬 뉴스 ChromaDB 컬렉션을 Pod ChromaDB v2 Multi-tenant로 업로드하는 스크립트
경로 문제 해결 버전 - 절대 경로 및 스크립트 위치 기반 경로 사용
"""

import os
import sys
import requests
import json
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
try:
    from langchain_chroma import Chroma
except ImportError:
    from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.storage import LocalFileStore
from langchain.embeddings import CacheBackedEmbeddings
import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv

load_dotenv()

class NewsChromaPodUploaderV2:
    """로컬 뉴스 ChromaDB를 Pod ChromaDB v2 Multi-tenant로 업로드 - 경로 문제 해결"""
    
    def __init__(self):
        # 스크립트 위치 기반으로 프로젝트 루트 찾기
        script_dir = Path(__file__).parent  # utils 디렉토리
        project_root = script_dir.parent.parent  # g-navi-ai-api 디렉토리
        
        # 로컬 뉴스 ChromaDB 설정 - 절대 경로 사용
        self.local_persist_dir = project_root / "app" / "storage" / "vector_stores" / "news_data"
        self.local_cache_dir = project_root / "app" / "storage" / "cache" / "embedding_cache"
        
        print(f" 뉴스 데이터 경로 정보:")
        print(f"   스크립트 위치: {script_dir}")
        print(f"   프로젝트 루트: {project_root}")
        print(f"   뉴스 ChromaDB 경로: {self.local_persist_dir}")
        print(f"   뉴스 캐시 경로: {self.local_cache_dir}")
        print(f"   ChromaDB 존재 여부: {self.local_persist_dir.exists()}")
        print(f"   캐시 디렉토리 존재 여부: {self.local_cache_dir.exists()}")
        
        # Pod ChromaDB v2 Multi-tenant 설정 - 고정 엔드포인트
        self.base_url = "https://sk-gnavi4.skala25a.project.skala-ai.com/vector/api/v2"
        self.tenant = "default_tenant"
        self.database = "default_database"
        self.collections_url = f"{self.base_url}/tenants/{self.tenant}/databases/{self.database}/collections"
        
        # 컬렉션 이름 설정
        self.local_collection_name = "news_articles"  # 로컬 컬렉션명
        self.pod_collection_name = "gnavi4_news_prod"  # Pod 운영용 컬렉션명
        self.pod_collection_id = None  # 컬렉션 생성 후 설정됨
        
        # 임베딩 설정
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            dimensions=1536
        )
        
        # 헤더 설정
        self.headers = {"Content-Type": "application/json"}
        
    def check_local_directories(self):
        """로컬 뉴스 디렉토리 구조 확인 및 생성"""
        print("📁 로컬 뉴스 디렉토리 구조 확인 중...")
        
        # 뉴스 ChromaDB 디렉토리 확인
        if not self.local_persist_dir.exists():
            print(f" 뉴스 ChromaDB 디렉토리가 없습니다: {self.local_persist_dir}")
            
            # 가능한 다른 경로들 확인
            possible_paths = [
                Path("storage/vector_stores/news_data"),
                Path("app/storage/vector_stores/news_data"),
                Path("../storage/vector_stores/news_data"),
                Path("../app/storage/vector_stores/news_data"),
            ]
            
            print("📍 가능한 뉴스 경로들 확인:")
            for path in possible_paths:
                abs_path = path.resolve()
                exists = abs_path.exists()
                print(f"   {path} -> {abs_path} (존재: {exists})")
                
                if exists:
                    print(f" 발견된 뉴스 경로 사용: {abs_path}")
                    self.local_persist_dir = abs_path
                    break
            else:
                raise FileNotFoundError(f"뉴스 ChromaDB 디렉토리를 찾을 수 없습니다. 확인된 경로들: {possible_paths}")
        
        # 뉴스 캐시 디렉토리 확인 및 생성
        if not self.local_cache_dir.exists():
            print(f" 뉴스 캐시 디렉토리가 없습니다: {self.local_cache_dir}")
            print(f"📂 뉴스 캐시 디렉토리 생성: {self.local_cache_dir}")
            self.local_cache_dir.mkdir(parents=True, exist_ok=True)
        
        print(f" 최종 사용 뉴스 경로:")
        print(f"   ChromaDB: {self.local_persist_dir}")
        print(f"   캐시: {self.local_cache_dir}")
        
    def load_local_collection(self):
        """로컬 뉴스 ChromaDB 컬렉션 로드 (직접 chromadb 사용)"""
        print(" 로컬 뉴스 ChromaDB 컬렉션 로드 중...")
        
        # 디렉토리 확인
        self.check_local_directories()
        
        try:
            # 직접 ChromaDB 클라이언트로 접근
            chroma_client = chromadb.PersistentClient(
                path=str(self.local_persist_dir),
                settings=Settings(
                    allow_reset=False,
                    anonymized_telemetry=False
                )
            )
            
            # 컬렉션 로드
            collection = chroma_client.get_collection(self.local_collection_name)
            
            # 모든 데이터 가져오기
            results = collection.get(include=['documents', 'metadatas', 'embeddings'])
            
            print(f" 로컬 뉴스 컬렉션 로드 완료:")
            print(f"   컬렉션 이름: {self.local_collection_name}")
            print(f"   문서 수: {len(results['documents'])}")
            print(f"   메타데이터 수: {len(results.get('metadatas', []))}")
            print(f"   ID 수: {len(results.get('ids', []))}")
            
            # embeddings 확인 (NumPy 배열 처리)
            embeddings_data = results.get('embeddings')
            embeddings_exist = False
            
            if embeddings_data is not None:
                import numpy as np
                if isinstance(embeddings_data, np.ndarray):
                    embeddings_exist = embeddings_data.size > 0
                elif isinstance(embeddings_data, list):
                    embeddings_exist = len(embeddings_data) > 0
                else:
                    embeddings_exist = bool(embeddings_data)
            
            if embeddings_exist:
                first_embedding = embeddings_data[0]
                if first_embedding is not None and len(first_embedding) > 0:
                    print(f"   벡터 차원: {len(first_embedding)}")
                else:
                    print("   벡터 차원: N/A (첫 번째 임베딩 없음)")
                    embeddings_exist = False
            else:
                print("   벡터 차원: N/A (embeddings 없음)")
            
            # embeddings가 없으면 생성
            if not embeddings_exist:
                print(" 로컬 뉴스 ChromaDB에 embeddings가 없습니다. 임베딩 생성 중...")
                documents = results['documents']
                embeddings_data = []
                
                print(f"📤 {len(documents)}개 문서에 대해 임베딩 생성 중...")
                for i, doc in enumerate(documents):
                    if i % 10 == 0:
                        print(f"   진행률: {i+1}/{len(documents)}")
                    
                    embedding = self.embeddings.embed_query(doc)
                    embeddings_data.append(embedding)
                
                # 결과에 임베딩 추가
                results['embeddings'] = embeddings_data
                print(" 임베딩 생성 완료")
            
            return results
            
        except Exception as e:
            print(f" 뉴스 ChromaDB 로드 실패: {str(e)}")
            print(" 사용 가능한 뉴스 컬렉션 확인 중...")
            
            # 디렉토리 내용 확인
            if self.local_persist_dir.exists():
                print(f"📁 뉴스 ChromaDB 디렉토리 내용:")
                for item in self.local_persist_dir.iterdir():
                    print(f"   {item.name} ({'디렉토리' if item.is_dir() else '파일'})")
                
                # chroma.sqlite3 파일 확인
                db_file = self.local_persist_dir / "chroma.sqlite3"
                if db_file.exists():
                    print(f" 뉴스 ChromaDB 파일 발견: {db_file}")
                    
                    # 다른 뉴스 컬렉션 이름들 시도
                    possible_collections = ["news_articles", "news", "articles", "default"]
                    chroma_client = chromadb.PersistentClient(
                        path=str(self.local_persist_dir),
                        settings=Settings(
                            allow_reset=False,
                            anonymized_telemetry=False
                        )
                    )
                    
                    # 사용 가능한 컬렉션 목록 확인
                    try:
                        collections = chroma_client.list_collections()
                        print(f" 사용 가능한 컬렉션들: {[c.name for c in collections]}")
                        
                        if collections:
                            # 첫 번째 컬렉션 사용
                            collection = collections[0]
                            print(f" 첫 번째 컬렉션 사용: {collection.name}")
                            self.local_collection_name = collection.name
                            
                            results = collection.get(include=['documents', 'metadatas', 'embeddings'])
                            
                            # embeddings 없으면 생성 (NumPy 배열 안전 처리)
                            embeddings_data = results.get('embeddings')
                            embeddings_exist = False
                            
                            if embeddings_data is not None:
                                import numpy as np
                                if isinstance(embeddings_data, np.ndarray):
                                    embeddings_exist = embeddings_data.size > 0
                                elif isinstance(embeddings_data, list):
                                    embeddings_exist = len(embeddings_data) > 0
                                else:
                                    embeddings_exist = bool(embeddings_data)
                            
                            if not embeddings_exist:
                                print(" 임베딩이 없어서 생성 중...")
                                documents = results['documents']
                                embeddings_data = []
                                
                                for i, doc in enumerate(documents):
                                    if i % 10 == 0:
                                        print(f"   진행률: {i+1}/{len(documents)}")
                                    embedding = self.embeddings.embed_query(doc)
                                    embeddings_data.append(embedding)
                                
                                results['embeddings'] = embeddings_data
                                print(" 임베딩 생성 완료")
                            else:
                                print(" 기존 임베딩 사용")
                            
                            return results
                        else:
                            raise Exception("사용 가능한 뉴스 컬렉션이 없습니다.")
                            
                    except Exception as inner_e:
                        print(f"    컬렉션 목록 조회 실패: {str(inner_e)}")
                        raise Exception("뉴스 컬렉션을 찾을 수 없습니다.")
                else:
                    raise Exception(f"뉴스 ChromaDB 파일이 없습니다: {db_file}")
            else:
                raise Exception(f"뉴스 ChromaDB 디렉토리가 없습니다: {self.local_persist_dir}")
    
    def create_pod_collection(self):
        """Pod ChromaDB v2 Multi-tenant에 새 뉴스 컬렉션 생성"""
        print(f" Pod ChromaDB v2 Multi-tenant에 뉴스 컬렉션 생성 중: {self.pod_collection_name}")
        print(f"   사용할 URL: {self.collections_url}")
        
        # 기존 컬렉션 목록 조회
        try:
            print("   기존 컬렉션 목록 조회 중...")
            list_response = requests.get(self.collections_url, headers=self.headers, timeout=30)
            print(f"   컬렉션 목록 조회 응답: {list_response.status_code}")
            
            if list_response.status_code == 200:
                collections = list_response.json()
                print(f"   기존 컬렉션 수: {len(collections)}")
                
                # 기존 뉴스 컬렉션 삭제 (있다면)
                for collection in collections:
                    if collection.get('name') == self.pod_collection_name:
                        collection_id = collection.get('id')
                        print(f"   🗑️ 기존 뉴스 컬렉션 삭제 중: {self.pod_collection_name} (ID: {collection_id})")
                        delete_url = f"{self.collections_url}/{collection_id}"
                        delete_response = requests.delete(delete_url, headers=self.headers, timeout=30)
                        print(f"   삭제 결과: {delete_response.status_code}")
            else:
                print(f"    컬렉션 목록 조회 실패: {list_response.status_code} - {list_response.text}")
                
        except Exception as e:
            print(f"    컬렉션 목록 조회 중 예외: {str(e)}")
        
        # 새 뉴스 컬렉션 생성
        create_data = {
            "name": self.pod_collection_name,
            "metadata": {
                "description": "gnavi4 news articles data",
                "dimensions": 1536,
                "embedding_model": "text-embedding-3-small"
            },
            "get_or_create": True
        }
        
        print(f"    뉴스 컬렉션 생성 데이터: {create_data}")
        
        try:
            response = requests.post(
                self.collections_url,
                headers=self.headers,
                json=create_data,
                timeout=30
            )
            
            print(f"   📡 뉴스 컬렉션 생성 응답: {response.status_code}")
            print(f"    응답 내용: {response.text}")
            
            if response.status_code in [200, 201]:
                collection_info = response.json()
                self.pod_collection_id = collection_info.get('id')  # 컬렉션 ID 저장
                print(f"    뉴스 컬렉션 생성 성공: {self.pod_collection_name}")
                print(f"    컬렉션 ID: {self.pod_collection_id}")
                return True
            elif response.status_code == 409:
                print(f"    뉴스 컬렉션이 이미 존재함: {self.pod_collection_name}")
                # 기존 컬렉션의 ID를 가져와야 함
                try:
                    list_response = requests.get(self.collections_url, headers=self.headers, timeout=30)
                    if list_response.status_code == 200:
                        collections = list_response.json()
                        for collection in collections:
                            if collection.get('name') == self.pod_collection_name:
                                self.pod_collection_id = collection.get('id')
                                print(f"    기존 뉴스 컬렉션 ID: {self.pod_collection_id}")
                                return True
                except:
                    pass
                return True
            else:
                print(f"    뉴스 컬렉션 생성 실패: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"    뉴스 컬렉션 생성 중 예외: {str(e)}")
            return False
    
    def upload_documents_batch(self, collection_data: Dict, batch_size: int = 25):
        """뉴스 문서를 배치로 Pod ChromaDB v2 Multi-tenant에 업로드"""
        if not self.pod_collection_id:
            raise Exception("컬렉션 ID가 설정되지 않았습니다. 컬렉션을 먼저 생성해주세요.")
            
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
        print(f"📤 총 {total_docs}개 뉴스 문서를 {batch_size}개씩 배치 업로드 시작...")
        print(f"   예상 총 배치 수: {(total_docs + batch_size - 1) // batch_size}")
        print(f"   뉴스 컬렉션 ID 사용: {self.pod_collection_id}")
        
        success_count = 0
        
        # 배치별 업로드
        for i in range(0, total_docs, batch_size):
            batch_end = min(i + batch_size, total_docs)
            batch_num = i // batch_size + 1
            
            # 배치 데이터 준비
            batch_data = {
                "ids": ids[i:batch_end],
                "embeddings": embeddings[i:batch_end] if embeddings else None,
                "documents": documents[i:batch_end],
                "metadatas": metadatas[i:batch_end] if metadatas else None
            }
            
            # None 값 제거
            batch_data = {k: v for k, v in batch_data.items() if v is not None}
            
            # 배치 크기 로깅
            try:
                batch_size_mb = len(str(batch_data).encode('utf-8')) / 1024 / 1024
                print(f"    배치 {batch_num}: {i+1}-{batch_end}/{total_docs} ({batch_size_mb:.2f}MB)")
            except:
                print(f"    배치 {batch_num}: {i+1}-{batch_end}/{total_docs}")
            
            # 업로드 URL - 컬렉션 ID 사용
            upload_url = f"{self.collections_url}/{self.pod_collection_id}/add"
            
            # API 호출 (재시도 로직 포함)
            max_retries = 3
            batch_success = False
            
            for retry in range(max_retries):
                try:
                    response = requests.post(
                        upload_url,
                        headers=self.headers,
                        json=batch_data,
                        timeout=180
                    )
                    
                    if response.status_code in [200, 201]:
                        success_count += 1
                        batch_success = True
                        print(f"       배치 {batch_num} 업로드 완료 (시도 {retry + 1}) - HTTP {response.status_code}")
                        break
                    else:
                        print(f"       배치 {batch_num} 업로드 실패 (시도 {retry + 1}): {response.status_code}")
                        print(f"       응답 내용: {response.text}")
                        if retry < max_retries - 1:
                            print(f"       재시도 {retry + 2}/{max_retries}")
                            continue
                        
                except requests.exceptions.Timeout:
                    print(f"      ⏰ 배치 {batch_num} 타임아웃 (시도 {retry + 1})")
                    if retry < max_retries - 1:
                        print(f"       재시도 {retry + 2}/{max_retries}")
                        continue
                        
                except Exception as e:
                    print(f"       배치 {batch_num} 예외 발생 (시도 {retry + 1}): {str(e)}")
                    if retry < max_retries - 1:
                        print(f"       재시도 {retry + 2}/{max_retries}")
                        continue
            
            if not batch_success:
                print(f"       배치 {batch_num} 최종 실패")
                return False
        
        print(f"\n 모든 뉴스 문서 업로드 완료!")
        print(f"   성공한 배치: {success_count}/{(total_docs + batch_size - 1) // batch_size}")
        return True
    
    def verify_upload(self):
        """뉴스 업로드 결과 검증"""
        print(" 뉴스 업로드 결과 검증 중...")
        
        if not self.pod_collection_id:
            print(" 컬렉션 ID가 없어서 검증할 수 없습니다.")
            return False
        
        try:
            # 1. 문서 개수 확인
            count_url = f"{self.collections_url}/{self.pod_collection_id}/count"
            count_response = requests.get(count_url, headers=self.headers, timeout=30)
            
            if count_response.status_code == 200:
                doc_count = count_response.json()
                print(f"    뉴스 문서 개수 확인: {doc_count}개")
            else:
                print(f"    뉴스 문서 개수 확인 실패: {count_response.status_code}")
            
            # 2. 검색 테스트 (임베딩 직접 제공)
            test_query = "뉴스"
            query_embedding = self.embeddings.embed_query(test_query)
            
            query_data = {
                "query_embeddings": [query_embedding],
                "n_results": 3,
                "include": ["documents", "metadatas"]
            }
            
            search_url = f"{self.collections_url}/{self.pod_collection_id}/query"
            search_response = requests.post(search_url, headers=self.headers, json=query_data, timeout=30)
            
            if search_response.status_code == 200:
                search_results = search_response.json()
                documents = search_results.get('documents', [[]])
                result_count = len(documents[0]) if documents and len(documents) > 0 else 0
                
                print(f"    뉴스 검색 테스트 성공: {result_count}개 결과 반환")
                
                if result_count > 0:
                    first_doc = documents[0][0] if documents[0] else ""
                    preview = first_doc[:100] + "..." if len(first_doc) > 100 else first_doc
                    print(f"    첫 번째 결과 미리보기: {preview}")
                    
                    print(" 뉴스 업로드 및 검증 성공!")
                    return True
                else:
                    print(" 뉴스 검색 결과가 없습니다")
                    return False
            else:
                print(f" 뉴스 검색 테스트 실패: {search_response.status_code}")
                print(f"   응답: {search_response.text}")
                return False
                
        except Exception as e:
            print(f" 뉴스 검증 중 예외 발생: {str(e)}")
            return False
    
    def get_collection_count(self):
        """뉴스 컬렉션 문서 수 조회"""
        if not self.pod_collection_id:
            return None
            
        try:
            count_url = f"{self.collections_url}/{self.pod_collection_id}/count"
            response = requests.get(count_url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                count_result = response.json()
                return count_result
            else:
                print(f"뉴스 컬렉션 카운트 조회 실패: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"뉴스 컬렉션 카운트 조회 중 예외: {str(e)}")
            return None
    
    def run_upload(self):
        """전체 뉴스 업로드 프로세스 실행"""
        try:
            print(f" 뉴스 ChromaDB v2 Multi-tenant 업로드 시작")
            print(f"   API 엔드포인트: {self.collections_url}")
            
            # 1. 로컬 뉴스 컬렉션 로드
            collection_data = self.load_local_collection()
            
            # 2. Pod에 뉴스 컬렉션 생성
            if not self.create_pod_collection():
                raise Exception("Pod 뉴스 컬렉션 생성 실패")
            
            # 3. 뉴스 문서 업로드
            if not self.upload_documents_batch(collection_data):
                raise Exception("뉴스 문서 업로드 실패")
            
            # 4. 뉴스 업로드 검증
            if not self.verify_upload():
                raise Exception("뉴스 업로드 검증 실패")
            
            # 5. 최종 통계
            count_result = self.get_collection_count()
            if count_result:
                print(f"   최종 뉴스 문서 수: {count_result}")
            
            print(f"\n 뉴스 ChromaDB v2 Multi-tenant 컬렉션 업로드가 완료되었습니다!")
            print(f"   로컬 컬렉션: {self.local_collection_name}")
            print(f"   Pod 컬렉션: {self.pod_collection_name}")
            print(f"   API 엔드포인트: {self.collections_url}")
            
        except Exception as e:
            print(f"\n 뉴스 업로드 실패: {str(e)}")
            import traceback
            print(" 상세 오류 정보:")
            traceback.print_exc()
            raise

def main():
    """메인 실행 함수"""
    print(" 뉴스 ChromaDB v2 Multi-tenant 컬렉션 Pod 업로드를 시작합니다...")
    
    # 현재 작업 디렉토리 출력
    print(f"📂 현재 작업 디렉토리: {os.getcwd()}")
    print(f" 스크립트 위치: {__file__}")
    
    # 환경변수 확인
    required_env = ["OPENAI_API_KEY"]
    missing_env = [env for env in required_env if not os.getenv(env)]
    
    if missing_env:
        print(f" 필수 환경변수가 없습니다: {missing_env}")
        print("   .env 파일에 다음을 추가하세요:")
        for env in missing_env:
            print(f"   {env}=your_value_here")
        return
    
    # 뉴스 업로드 실행
    uploader = NewsChromaPodUploaderV2()
    uploader.run_upload()

if __name__ == "__main__":
    main()