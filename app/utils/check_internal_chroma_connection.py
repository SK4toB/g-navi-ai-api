# app/utils/check_internal_chroma_connection.py
"""
같은 네임스페이스(sk-team-04)의 ChromaDB 연결 확인 스크립트
chromadb-1-0 Pod에 직접 연결하여 상태 확인
"""

import os
import requests
import base64
import json
from typing import Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

class InternalChromaChecker:
    """같은 네임스페이스 ChromaDB 연결 확인 클래스"""
    
    def __init__(self):
        # 내부 ChromaDB 설정 (같은 네임스페이스)
        self.internal_urls = [
            "http://chromadb-1-0:8000/api/v1",  # Pod 이름으로 직접 접근
            "http://chromadb-1-0.sk-team-04.svc.cluster.local:8000/api/v1",  # FQDN 접근
            "http://chromadb-service:8000/api/v1",  # 서비스가 있다면
        ]
        
        # 인증 정보
        self.auth_credentials = os.getenv("CHROMA_AUTH_CREDENTIALS")
        self.headers = self._get_auth_headers() if self.auth_credentials else {}
        
        print("🔍 같은 네임스페이스(sk-team-04) ChromaDB 연결 확인")
        print(f"🔐 인증 설정: {'✅ 있음' if self.auth_credentials else '❌ 없음'}")
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """ChromaDB 인증 헤더 생성"""
        if not self.auth_credentials:
            return {}
        
        try:
            encoded_credentials = base64.b64encode(
                self.auth_credentials.encode()
            ).decode()
            return {
                "Authorization": f"Basic {encoded_credentials}",
                "Content-Type": "application/json"
            }
        except Exception as e:
            print(f"⚠️ 인증 헤더 생성 실패: {e}")
            return {}
    
    def test_connection(self) -> bool:
        """ChromaDB 연결 테스트"""
        print("\n📡 ChromaDB 연결 테스트 시작...")
        
        successful_url = None
        
        for i, url in enumerate(self.internal_urls, 1):
            print(f"\n{i}. {url} 테스트 중...")
            
            try:
                # Heartbeat 테스트
                response = requests.get(
                    f"{url}/heartbeat",
                    headers=self.headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    heartbeat_data = response.json()
                    print(f"   ✅ 연결 성공!")
                    print(f"   📊 Heartbeat: {heartbeat_data}")
                    successful_url = url
                    break
                else:
                    print(f"   ❌ HTTP {response.status_code}: {response.text[:100]}")
                    
            except requests.exceptions.ConnectTimeout:
                print(f"   ⏰ 연결 타임아웃 (10초)")
            except requests.exceptions.ConnectionError as e:
                print(f"   🔌 연결 실패: {str(e)[:100]}")
            except Exception as e:
                print(f"   ❌ 기타 오류: {str(e)[:100]}")
        
        if successful_url:
            print(f"\n🎉 성공한 URL: {successful_url}")
            self.base_url = successful_url
            return True
        else:
            print(f"\n❌ 모든 URL 연결 실패")
            return False
    
    def check_collections(self) -> List[Dict]:
        """컬렉션 목록 확인"""
        if not hasattr(self, 'base_url'):
            print("❌ 먼저 연결 테스트를 성공해야 합니다")
            return []
        
        print(f"\n📚 컬렉션 목록 확인...")
        
        try:
            response = requests.get(
                f"{self.base_url}/collections",
                headers=self.headers,
                timeout=15
            )
            
            if response.status_code == 200:
                collections = response.json()
                print(f"   📊 총 컬렉션 수: {len(collections)}")
                
                if collections:
                    print(f"   📋 컬렉션 목록:")
                    for i, col in enumerate(collections, 1):
                        col_name = col.get('name', 'Unknown')
                        col_id = col.get('id', 'Unknown')
                        metadata = col.get('metadata', {})
                        print(f"      {i}. {col_name} (ID: {col_id[:8]}...)")
                        if metadata:
                            print(f"         메타데이터: {metadata}")
                else:
                    print("   📭 컬렉션이 없습니다")
                
                return collections
            else:
                print(f"   ❌ 컬렉션 조회 실패: HTTP {response.status_code}")
                print(f"      응답: {response.text}")
                return []
                
        except Exception as e:
            print(f"   ❌ 컬렉션 조회 중 오류: {str(e)}")
            return []
    
    def test_sample_data(self, collections: List[Dict]) -> bool:
        """샘플 데이터 확인"""
        if not collections:
            print("\n📭 테스트할 컬렉션이 없습니다")
            return False
        
        print(f"\n🔍 샘플 데이터 확인...")
        
        found_data = False
        
        for col in collections:
            col_name = col.get('name')
            print(f"\n   📂 {col_name} 컬렉션 데이터 확인...")
            
            try:
                # 처음 3개 문서만 가져오기
                response = requests.post(
                    f"{self.base_url}/collections/{col_name}/get",
                    headers=self.headers,
                    json={
                        "limit": 3,
                        "include": ["documents", "metadatas"]
                    },
                    timeout=15
                )
                
                if response.status_code == 200:
                    data = response.json()
                    doc_count = len(data.get('documents', []))
                    
                    if doc_count > 0:
                        print(f"      ✅ {doc_count}개 문서 발견")
                        
                        # 첫 번째 문서 미리보기
                        first_doc = data['documents'][0]
                        preview = first_doc[:150] + "..." if len(first_doc) > 150 else first_doc
                        print(f"      📄 첫 번째 문서: {preview}")
                        
                        # 메타데이터 미리보기
                        if data.get('metadatas') and data['metadatas'][0]:
                            metadata_keys = list(data['metadatas'][0].keys())
                            print(f"      🏷️ 메타데이터 키: {metadata_keys[:5]}{'...' if len(metadata_keys) > 5 else ''}")
                        
                        found_data = True
                    else:
                        print(f"      📭 문서 없음")
                else:
                    print(f"      ❌ 데이터 조회 실패: HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"      ❌ 데이터 조회 중 오류: {str(e)[:100]}")
        
        return found_data
    
    def test_search_functionality(self, collections: List[Dict]) -> bool:
        """검색 기능 테스트"""
        if not collections:
            return False
        
        print(f"\n🔍 검색 기능 테스트...")
        
        # 가장 큰 컬렉션 찾기
        target_collection = None
        for col in collections:
            try:
                response = requests.post(
                    f"{self.base_url}/collections/{col['name']}/get",
                    headers=self.headers,
                    json={"limit": 1},
                    timeout=10
                )
                if response.status_code == 200:
                    data = response.json()
                    if len(data.get('documents', [])) > 0:
                        target_collection = col['name']
                        break
            except:
                continue
        
        if not target_collection:
            print("   ❌ 테스트할 데이터가 있는 컬렉션을 찾을 수 없습니다")
            return False
        
        print(f"   🎯 {target_collection} 컬렉션에서 텍스트 검색 테스트...")
        
        try:
            # 간단한 텍스트 기반 검색 테스트
            search_data = {
                "query_texts": ["프로젝트"],  # 일반적인 검색어
                "n_results": 3
            }
            
            response = requests.post(
                f"{self.base_url}/collections/{target_collection}/query",
                headers=self.headers,
                json=search_data,
                timeout=15
            )
            
            if response.status_code == 200:
                search_results = response.json()
                documents = search_results.get('documents', [[]])
                result_count = len(documents[0]) if documents and len(documents) > 0 else 0
                
                print(f"      ✅ 검색 성공: {result_count}개 결과")
                
                if result_count > 0:
                    first_result = documents[0][0]
                    preview = first_result[:100] + "..." if len(first_result) > 100 else first_result
                    print(f"      📄 첫 번째 결과: {preview}")
                
                return result_count > 0
            else:
                print(f"      ❌ 검색 실패: HTTP {response.status_code}")
                print(f"         응답: {response.text[:200]}")
                return False
                
        except Exception as e:
            print(f"      ❌ 검색 테스트 중 오류: {str(e)}")
            return False
    
    def run_full_check(self) -> Dict[str, Any]:
        """전체 확인 프로세스 실행"""
        print("=" * 60)
        print("🚀 sk-team-04 네임스페이스 ChromaDB 연결 확인 시작")
        print("=" * 60)
        
        results = {
            "connection": False,
            "collections": [],
            "has_data": False,
            "search_works": False,
            "summary": {}
        }
        
        # 1. 연결 테스트
        if self.test_connection():
            results["connection"] = True
            
            # 2. 컬렉션 확인
            collections = self.check_collections()
            results["collections"] = collections
            
            # 3. 데이터 확인
            has_data = self.test_sample_data(collections)
            results["has_data"] = has_data
            
            # 4. 검색 테스트
            search_works = self.test_search_functionality(collections)
            results["search_works"] = search_works
            
            # 5. 요약
            results["summary"] = {
                "total_collections": len(collections),
                "collection_names": [col.get('name') for col in collections],
                "base_url": getattr(self, 'base_url', 'Unknown'),
                "status": "✅ 정상" if (has_data and search_works) else "⚠️ 일부 문제" if results["connection"] else "❌ 연결 실패"
            }
        
        # 최종 결과 출력
        print("\n" + "=" * 60)
        print("📊 최종 결과")
        print("=" * 60)
        
        status_icon = "✅" if results["connection"] else "❌"
        print(f"{status_icon} 연결: {'성공' if results['connection'] else '실패'}")
        
        if results["connection"]:
            print(f"📚 컬렉션: {len(results['collections'])}개")
            print(f"📄 데이터: {'있음' if results['has_data'] else '없음'}")
            print(f"🔍 검색: {'작동' if results['search_works'] else '문제'}")
            print(f"🌐 URL: {results['summary']['base_url']}")
            
            if results["collections"]:
                print(f"📋 컬렉션 목록: {', '.join(results['summary']['collection_names'])}")
        
        if results["connection"] and results["has_data"] and results["search_works"]:
            print("\n🎉 ChromaDB가 정상적으로 작동하고 있습니다!")
        elif results["connection"]:
            print("\n⚠️ ChromaDB 연결은 되지만 데이터나 검색에 문제가 있을 수 있습니다.")
        else:
            print("\n❌ ChromaDB 연결에 실패했습니다.")
            print("\n🔧 해결 방법:")
            print("1. ChromaDB Pod 상태 확인: kubectl get pod chromadb-1-0 -n sk-team-04")
            print("2. Pod 로그 확인: kubectl logs chromadb-1-0 -n sk-team-04")
            print("3. 포트 포워딩 테스트: kubectl port-forward chromadb-1-0 8000:8000 -n sk-team-04")
            print("4. 서비스 확인: kubectl get svc -n sk-team-04 | grep chroma")
        
        return results

def main():
    """메인 실행 함수"""
    # 환경변수 확인
    if not os.getenv("CHROMA_AUTH_CREDENTIALS"):
        print("⚠️ CHROMA_AUTH_CREDENTIALS 환경변수가 설정되지 않았습니다.")
        print("   인증이 필요한 경우 .env 파일에 추가하세요:")
        print("   CHROMA_AUTH_CREDENTIALS=your_credentials")
        print("")
    
    # 연결 확인 실행
    checker = InternalChromaChecker()
    results = checker.run_full_check()
    
    return results

if __name__ == "__main__":
    main()