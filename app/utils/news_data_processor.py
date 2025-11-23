# app/utils/news_data_processor.py
"""
* @className : NewsDataProcessor
* @description : 뉴스 데이터를 처리하고 벡터 데이터베이스에 저장하는 유틸리티 클래스
*                뉴스 데이터를 임베딩하여 ChromaDB에 저장하고 검색할 수 있도록 지원합니다.
*
"""

import json
import logging
from typing import List, Dict, Any
from datetime import datetime
import chromadb
from chromadb.config import Settings
from langchain_openai import OpenAIEmbeddings
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()


class NewsDataProcessor:
    """
    * @className : NewsDataProcessor
    * @description : 뉴스 데이터 처리 및 벡터화 클래스
    *                JSON 형태의 뉴스 데이터를 읽어와서 임베딩하고
    *                ChromaDB에 저장하는 유틸리티 클래스입니다.
    *                 검색 로직은 포함하지 않음 - retriever.py의 Agent가 담당
    """
    
    def __init__(self):
        """
        NewsDataProcessor 생성자
        """
        self.logger = logging.getLogger(__name__)
        
        # OpenAI 임베딩 모델 설정
        self.embedding_model = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # ChromaDB 클라이언트 설정
        news_db_path = "./app/storage/vector_stores/news_data"
        Path(news_db_path).mkdir(parents=True, exist_ok=True)
        
        self.chroma_client = chromadb.PersistentClient(
            path=news_db_path,
            settings=Settings(
                allow_reset=True,
                anonymized_telemetry=False
            )
        )
        
        # 뉴스 컬렉션 생성 또는 가져오기
        try:
            self.news_collection = self.chroma_client.get_collection("news_articles")
            print("📰 기존 뉴스 컬렉션 로드 완료")
        except:
            self.news_collection = self.chroma_client.create_collection(
                name="news_articles",
                metadata={"description": "G-Navi 뉴스 아티클 벡터 저장소"}
            )
            print("📰 새 뉴스 컬렉션 생성 완료")
    
    def load_news_data(self, file_path: str) -> List[Dict[str, Any]]:
        """
        JSON 파일에서 뉴스 데이터를 로드합니다.
        
        @param file_path: str - JSON 파일 경로
        @return List[Dict[str, Any]] - 뉴스 데이터 리스트
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                news_data = json.load(file)
            
            print(f"📰 뉴스 데이터 로드 완료: {len(news_data)}개 아티클")
            return news_data
        
        except Exception as e:
            self.logger.error(f"뉴스 데이터 로드 실패: {e}")
            return []
    
    def create_embedding_text(self, news_item: Dict[str, Any]) -> str:
        """
        뉴스 아이템을 임베딩용 텍스트로 변환합니다.
        
        @param news_item: Dict[str, Any] - 뉴스 아이템
        @return str - 임베딩용 텍스트
        """
        # 제목, 내용, 도메인을 결합한 텍스트 생성
        embedding_text = f"""
        제목: {news_item.get('title', '')}
        도메인: {news_item.get('domain', '')}
        카테고리: {news_item.get('category', '')}
        내용: {news_item.get('content', '')}
        """
        
        return embedding_text.strip()
    
    def process_and_store_news(self, news_data: List[Dict[str, Any]]) -> bool:
        """
        뉴스 데이터를 처리하고 ChromaDB에 저장합니다.
        
        @param news_data: List[Dict[str, Any]] - 뉴스 데이터 리스트
        @return bool - 성공 여부
        """
        try:
            # 기존 데이터 확인
            existing_count = self.news_collection.count()
            if existing_count > 0:
                print(f"📰 기존 뉴스 데이터 {existing_count}개 존재, 초기화 후 새로 저장합니다.")
                self.chroma_client.delete_collection("news_articles")
                self.news_collection = self.chroma_client.create_collection(
                    name="news_articles",
                    metadata={"description": "G-Navi 뉴스 아티클 벡터 저장소"}
                )
            
            documents = []
            metadatas = []
            ids = []
            
            for news_item in news_data:
                # 임베딩용 텍스트 생성
                embedding_text = self.create_embedding_text(news_item)
                
                # 데이터 준비
                documents.append(embedding_text)
                metadatas.append({
                    "news_id": news_item.get("id", ""),
                    "domain": news_item.get("domain", ""),
                    "title": news_item.get("title", ""),
                    "category": news_item.get("category", ""),
                    "published_date": news_item.get("published_date", ""),
                    "source": news_item.get("source", ""),
                    "processed_at": datetime.now().isoformat()
                })
                ids.append(news_item.get("id", f"news_{len(ids)}"))
                
                print(f" 뉴스 처리 완료: {news_item.get('title', 'Unknown')[:50]}...")
            
            # ChromaDB에 저장 (자동으로 임베딩 생성됨)
            if documents:
                self.news_collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                
                print(f" 뉴스 데이터 저장 완료: {len(documents)}개 아티클")
                return True
            else:
                print(" 저장할 뉴스 데이터가 없습니다.")
                return False
        
        except Exception as e:
            self.logger.error(f"뉴스 데이터 저장 실패: {e}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        뉴스 컬렉션의 통계 정보를 반환합니다.
        
        @return Dict[str, Any] - 컬렉션 통계
        """
        try:
            count = self.news_collection.count()
            return {
                "total_articles": count,
                "collection_name": "news_articles",
                "storage_path": "./app/storage/vector_stores/news_data",
                "last_updated": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"통계 정보 조회 실패: {e}")
            return {}
    
    def get_chroma_collection(self):
        """
        ChromaDB 컬렉션 객체를 반환합니다.
        Retriever Agent에서 직접 검색을 수행할 때 사용됩니다.
        
        @return: ChromaDB Collection 객체
        """
        return self.news_collection


def main():
    """
    뉴스 데이터 처리 메인 함수 (초기 VectorDB 구축용)
    CLI에서 직접 실행하거나 스크립트로 호출할 수 있습니다.
     검색 테스트는 retriever.py의 Agent에서 수행
    """
    print("� G-Navi 뉴스 데이터 VectorDB 업로드 시작...")
    
    try:
        # 환경 변수 확인
        if not os.getenv("OPENAI_API_KEY"):
            print(" OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
            return False
        
        # 뉴스 데이터 처리기 인스턴스 생성
        processor = NewsDataProcessor()
        
        # 뉴스 데이터 파일 경로 설정
        news_file_path = Path("./app/data/json/news_dummy_data.json")
        
        if not news_file_path.exists():
            print(f" 뉴스 데이터 파일을 찾을 수 없습니다: {news_file_path}")
            return False
        
        print(f"📂 뉴스 데이터 파일: {news_file_path}")
        
        # 뉴스 데이터 로드
        news_data = processor.load_news_data(str(news_file_path))
        
        if not news_data:
            print(" 뉴스 데이터를 로드할 수 없습니다.")
            return False
        
        print(f"📰 총 {len(news_data)}개의 뉴스 데이터 로드 완료")
        
        # VectorDB에 저장
        success = processor.process_and_store_news(news_data)
        
        if success:
            # 통계 정보 출력
            stats = processor.get_collection_stats()
            print(f"\n VectorDB 저장 완료!")
            print(f"   - 총 아티클 수: {stats.get('total_articles', 0)}개")
            print(f"   - 컬렉션 이름: {stats.get('collection_name', 'N/A')}")
            print(f"   - 저장 경로: {stats.get('storage_path', 'N/A')}")
            print(f"   - 마지막 업데이트: {stats.get('last_updated', 'N/A')}")
            
            print("\n 뉴스 데이터 VectorDB 구축 완료!")
            print(" 검색 테스트는 NewsRetrieverAgent에서 수행하세요.")
            return True
        else:
            print(" VectorDB 저장 실패")
            return False
            
    except ImportError as e:
        print(f" 필요한 모듈을 임포트할 수 없습니다: {e}")
        print(" 다음 패키지들이 설치되어 있는지 확인해주세요:")
        print("   - chromadb")
        print("   - langchain-openai")
        print("   - openai")
        return False
    except Exception as e:
        print(f" 뉴스 데이터 업로드 중 오류 발생: {e}")
        return False


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
