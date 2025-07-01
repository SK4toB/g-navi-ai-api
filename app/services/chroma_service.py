# app/services/chroma_service.py
"""
* @className : ChromaService
* @description : ChromaDB 서비스 모듈
*                벡터 데이터베이스 관리를 담당하는 서비스입니다.
*                대화 내역을 벡터화하여 저장하고 검색 기능을 제공합니다.
*
* @modification : 2025.07.01(이재원) 최초생성
*
* @author 이재원
* @Date 2025.07.01
* @version 1.0
* @see ChromaDB, VectorStore
*  == 개정이력(Modification Information) ==
*  
*   수정일        수정자        수정내용
*   ----------   --------     ---------------------------
*   2025.07.01   이재원       최초 생성
*  
* Copyright (C) by G-Navi AI System All right reserved.
"""

import requests
import base64
from typing import Dict, Any

from app.config.settings import settings


class ChromaService:
    """
    ChromaDB 연동 서비스 (간단 버전)
    - 접근 가능 여부만 확인
    """
    
    def __init__(self):
        self.base_url = None
        self.headers = None
        self.available = False
        self._init_client()
        print("ChromaService 초기화 완료")
    
    def _init_client(self):
        """ChromaDB 연결 설정 초기화"""
        try:
            # 인증 정보 검증
            if not settings.chroma_auth_credentials:
                print("❌ ChromaDB 인증 정보가 설정되지 않았습니다.")
                print("   개발환경: .env 파일에 CHROMA_AUTH_CREDENTIALS 추가")
                print("   운영환경: K8s Secret에 CHROMA_AUTH_CREDENTIALS 추가")
                return
            
            # 접속 방식 선택
            if settings.chroma_use_external:
                # 외부 URL 사용 (개발/테스트용)
                self.base_url = f"{settings.chroma_external_url}/api/v1"
                print(f"ChromaDB 외부 접속 시도: {self.base_url}")
            else:
                # k8s 내부 접근 (운영환경)
                self.base_url = f"http://{settings.chroma_host}:{settings.chroma_port}/api/v1"
                print(f"ChromaDB 내부 접속 시도: {self.base_url}")
            
            # 인증 헤더 설정
            self.headers = self._get_auth_headers()
            
            # 연결 테스트
            heartbeat_result = self._test_heartbeat()
            if heartbeat_result:
                print(f"ChromaDB 연결 성공: {heartbeat_result}")
                self.available = True
            else:
                print("ChromaDB heartbeat 실패")
                self.available = False
            
        except Exception as e:
            print(f"ChromaDB 연결 실패: {e}")
            self.available = False
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """인증 헤더 생성"""
        credentials = settings.chroma_auth_credentials
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        return {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/json"
        }
    
    def _test_heartbeat(self) -> bool:
        """Heartbeat 테스트"""
        try:
            response = requests.get(
                f"{self.base_url}/heartbeat", 
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Heartbeat 실패: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"Heartbeat 오류: {e}")
            return False
    
    def is_available(self) -> bool:
        """ChromaDB 사용 가능 여부"""
        return self.available
    
    def test_connection(self) -> Dict[str, Any]:
        """연결 테스트"""
        try:
            if not self.base_url or not self.headers:
                return {
                    "status": "failed",
                    "error": "클라이언트가 초기화되지 않았습니다",
                    "available": False
                }
            
            # Heartbeat 테스트
            heartbeat = self._test_heartbeat()
            
            if heartbeat:
                return {
                    "status": "success",
                    "heartbeat": heartbeat,
                    "available": True,
                    "base_url": self.base_url,
                    "connection_mode": "external" if settings.chroma_use_external else "internal"
                }
            else:
                return {
                    "status": "failed",
                    "error": "heartbeat 실패",
                    "available": False,
                    "base_url": self.base_url
                }
            
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "available": False
            }
    
    def get_basic_info(self) -> Dict[str, Any]:
        """기본 정보 조회"""
        return {
            "available": self.is_available(),
            "collection_name": settings.chroma_collection_name,
            "connection_mode": "external" if settings.chroma_use_external else "internal",
            "base_url": self.base_url,
            "auth_configured": bool(settings.chroma_auth_credentials)
        }
    
    def list_collections(self) -> Dict[str, Any]:
        """컬렉션 목록 조회 (테스트용)"""
        try:
            if not self.is_available():
                return {"error": "ChromaDB 사용 불가"}
            
            response = requests.get(
                f"{self.base_url}/collections",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                collections = response.json()
                return {
                    "status": "success",
                    "collections": collections,
                    "count": len(collections)
                }
            else:
                return {
                    "status": "failed",
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }