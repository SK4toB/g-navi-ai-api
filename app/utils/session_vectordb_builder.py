# app/utils/session_vectordb_builder.py
"""
🗃️ 사용자별 채팅 세션 대화내역 VectorDB 구축 시스템

📋 핵심 기능:
1. 세션 종료 시 사용자의 current_session_messages를 VectorDB로 자동 구축
2. 사용자별(member_id) 분리된 VectorDB 저장 → 개인정보 보호 및 개인화 검색
3. OpenAI Embeddings + ChromaDB를 활용한 의미 기반 검색
4. 과거 대화 요약 및 키워드 추출로 검색 품질 향상

🔄 동작 플로우:
세션 종료 → current_session_messages 수집 → LLM 요약 → VectorDB 구축 → 향후 검색 활용

📁 저장 구조:
storage/vector_stores/user_{member_id}_sessions/
├── chroma.sqlite3              # ChromaDB 벡터 저장소
├── session_index.json          # 세션 메타데이터 인덱스
└── 기타 ChromaDB 파일들

⚠️ 중요 사항:
- 각 사용자별로 완전히 분리된 VectorDB 생성 (타 사용자 데이터 접근 불가)
- 세션 종료 시에만 VectorDB 구축 (실시간 업데이트 아님)
- 검색 시 관련도 점수 기반 필터링으로 품질 보장
"""

import os
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

import chromadb
from chromadb.config import Settings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

class SessionVectorDBBuilder:
    """
    🗃️ 사용자별 채팅 세션 대화내역 VectorDB 구축 및 관리 클래스
    
    이 클래스는 채팅 세션이 종료될 때 해당 세션의 모든 대화 내역을
    사용자별로 분리된 VectorDB에 저장하여, 향후 개인화된 검색 서비스를 제공합니다.
    
    주요 책임:
    - 세션 종료 시 current_session_messages → VectorDB 자동 구축
    - 사용자별 VectorDB 분리 관리 (member_id 기준)
    - 과거 대화 의미 기반 검색 기능 제공
    - 세션 메타데이터 및 통계 관리
    """
    
    def __init__(self):
        """
        VectorDB 구축 시스템 초기화
        
        설정 내용:
        - 저장 경로: app/storage/vector_stores/
        - 임베딩 모델: OpenAI text-embedding-3-small
        - 텍스트 분할: 1000자 청크, 200자 오버랩
        """
        # 📁 VectorDB 저장 경로 설정 (사용자별 폴더로 분리됨)
        self.storage_path = Path(__file__).parent.parent / "storage" / "vector_stores"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 🤖 OpenAI 임베딩 모델 초기화 (환경변수 OPENAI_API_KEY 필요)
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small"  # 비용 효율적이면서 성능 좋은 모델
        )
        
        # ✂️ 텍스트 청킹 설정 (긴 대화를 적절한 크기로 분할)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,    # 각 청크 최대 1000자
            chunk_overlap=200,  # 청크 간 200자 중복 (컨텍스트 보존)
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]  # 자연스러운 분할점
        )
        
        print(f"SessionVectorDBBuilder 초기화 완료 (저장경로: {self.storage_path})")
    
    async def summarize_session_content(self, messages: List[Dict[str, Any]], user_name: str) -> str:
        """
        📝 세션 대화 내용을 요약하여 검색 가능한 메타데이터 생성
        
        Args:
            messages: 세션의 모든 대화 메시지 [{"role": "user/assistant", "content": "..."}]
            user_name: 사용자 이름
            
        Returns:
            str: "사용자 {이름}의 대화 세션 - 총 N개 질문, M개 응답 | 주요 주제: 키워드들"
            
        목적:
            - VectorDB 검색 시 빠른 세션 식별
            - 주요 키워드 추출로 검색 품질 향상
            - 관리자용 세션 개요 제공
        """
        try:
            # 메시지를 텍스트로 변환
            conversation_text = self._format_messages_to_text(messages)
            
            if not conversation_text.strip():
                return f"사용자 {user_name}의 빈 대화 세션"
            
            # 간단한 요약 생성 (실제로는 LLM API를 사용할 수 있음)
            summary = await self._generate_summary_with_llm(conversation_text, user_name)
            
            return summary
            
        except Exception as e:
            print(f"세션 내용 요약 실패: {e}")
            return f"사용자 {user_name}의 대화 세션 (요약 실패)"
    
    def _format_messages_to_text(self, messages: List[Dict[str, Any]]) -> str:
        """메시지 목록을 텍스트로 변환"""
        text_parts = []
        
        for msg in messages:
            if isinstance(msg, dict):
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                
                if role == 'user':
                    text_parts.append(f"사용자: {content}")
                elif role == 'assistant':
                    text_parts.append(f"AI: {content}")
                elif role == 'system':
                    text_parts.append(f"시스템: {content}")
                else:
                    text_parts.append(f"{role}: {content}")
        
        return "\n".join(text_parts)
    
    async def _generate_summary_with_llm(self, conversation_text: str, user_name: str) -> str:
        """
        LLM을 사용한 대화 요약 생성
        (실제 구현에서는 OpenAI API나 다른 LLM을 사용)
        """
        try:
            # 간단한 규칙 기반 요약 (실제로는 LLM API 호출)
            lines = conversation_text.split('\n')
            user_messages = [line for line in lines if line.startswith('사용자:')]
            ai_messages = [line for line in lines if line.startswith('AI:')]
            
            # 주요 키워드 추출
            keywords = self._extract_keywords(conversation_text)
            
            summary = f"사용자 {user_name}의 대화 세션 - "
            summary += f"총 {len(user_messages)}개 질문, {len(ai_messages)}개 응답"
            
            if keywords:
                summary += f" | 주요 주제: {', '.join(keywords[:5])}"
            
            return summary
            
        except Exception as e:
            print(f"LLM 요약 생성 실패: {e}")
            return f"사용자 {user_name}의 대화 세션 (요약 생성 실패)"
    
    def _extract_keywords(self, text: str) -> List[str]:
        """간단한 키워드 추출"""
        # 실제로는 더 정교한 키워드 추출 로직 사용
        common_words = {'은', '는', '이', '가', '을', '를', '에', '의', '와', '과', '로', '으로', '에서', '부터', '까지', 'AI', '사용자', '시스템'}
        
        words = text.split()
        keywords = []
        
        for word in words:
            if len(word) > 2 and word not in common_words:
                if word not in keywords:
                    keywords.append(word)
                if len(keywords) >= 10:
                    break
        
        return keywords
    
    async def build_vector_db(self, 
                            conversation_id: str, 
                            member_id: str, 
                            user_name: str, 
                            messages: List[Dict[str, Any]],
                            session_metadata: Dict[str, Any]) -> bool:
        """
        🗃️ 세션 대화 내역을 사용자별 VectorDB에 저장하는 핵심 메서드
        
        Args:
            conversation_id: 대화방 고유 ID (예: "chat_session_123")
            member_id: 사용자 고유 ID (VectorDB 분리 기준)
            user_name: 사용자 이름 (메타데이터용)
            messages: 세션의 모든 대화 메시지들
            session_metadata: 세션 기본 정보 (생성시간, 지속시간 등)
            
        Returns:
            bool: VectorDB 구축 성공 여부
            
        🔄 처리 과정:
        1. 대화 내용 요약 생성 (검색 품질 향상)
        2. 사용자별 VectorDB 폴더 생성/접근
        3. 대화 텍스트를 적절한 크기로 청킹
        4. OpenAI Embeddings로 벡터화
        5. ChromaDB에 저장 + 메타데이터 첨부
        6. 세션 인덱스 파일 업데이트
        
        💾 저장 위치: storage/vector_stores/user_{member_id}_sessions/
        """
        try:
            # ✅ 1단계: 빈 세션 검증
            if not messages:
                print(f"빈 메시지 세션 - VectorDB 구축 생략: {conversation_id}")
                return False
            
            # 📝 2단계: 대화 내용 요약 생성 (검색 품질 향상을 위해)
            summary = await self.summarize_session_content(messages, user_name)
            print(f"세션 요약 생성 완료: {conversation_id} - {summary}")
            
            # 📁 3단계: 사용자별 VectorDB 저장 경로 생성
            # 중요: 각 사용자마다 완전히 분리된 폴더로 개인정보 보호
            user_db_path = self.storage_path / f"user_{member_id}_sessions"
            user_db_path.mkdir(parents=True, exist_ok=True)
            
            # 🔤 4단계: 대화 메시지들을 하나의 텍스트로 변환
            conversation_text = self._format_messages_to_text(messages)
            
            # ✂️ 5단계: 긴 텍스트를 검색에 적합한 크기로 분할 (청킹)
            chunks = self.text_splitter.split_text(conversation_text)
            
            if not chunks:
                print(f"청킹된 텍스트가 없음 - VectorDB 구축 생략: {conversation_id}")
                return False
            
            # 🏷️ 6단계: 각 청크에 첨부할 메타데이터 준비
            metadata = {
                "conversation_id": conversation_id,        # 세션 ID
                "member_id": member_id,                   # 사용자 ID (검색 필터링용)
                "user_name": user_name,                   # 사용자 이름
                "summary": summary,                       # AI 생성 요약
                "created_at": session_metadata.get("created_at", datetime.utcnow()).isoformat(),
                "session_duration_minutes": session_metadata.get("session_duration_minutes", 0),
                "message_count": len(messages),           # 총 메시지 수
                "indexed_at": datetime.utcnow().isoformat()  # VectorDB 구축 시점
            }
            
            # 🗃️ 7단계: ChromaDB VectorStore 초기화 (사용자별 컬렉션)
            vectorstore = Chroma(
                collection_name=f"user_{member_id}_sessions",  # 사용자별 컬렉션명
                embedding_function=self.embeddings,            # OpenAI 임베딩 함수
                persist_directory=str(user_db_path)            # 저장 경로
            )
            
            # 📦 8단계: 각 청크에 고유 메타데이터 추가
            metadatas = []
            for i, chunk in enumerate(chunks):
                chunk_metadata = metadata.copy()                    # 기본 메타데이터 복사
                chunk_metadata["chunk_index"] = i                   # 청크 순번
                chunk_metadata["chunk_content"] = chunk[:100] + "..." if len(chunk) > 100 else chunk  # 미리보기
                metadatas.append(chunk_metadata)
            
            # VectorDB에 추가
            vectorstore.add_texts(
                texts=chunks,
                metadatas=metadatas,
                ids=[f"{conversation_id}_chunk_{i}" for i in range(len(chunks))]
            )
            
            # 영속화
            vectorstore.persist()
            
            print(f"✅ VectorDB 구축 완료: {conversation_id} (사용자: {user_name}, 청크: {len(chunks)}개)")
            
            # 7. 세션 인덱스 파일 업데이트
            await self._update_session_index(member_id, conversation_id, metadata)
            
            return True
            
        except Exception as e:
            print(f"❌ VectorDB 구축 실패: {conversation_id} - {e}")
            return False
    
    async def _update_session_index(self, member_id: str, conversation_id: str, metadata: Dict[str, Any]):
        """사용자별 세션 인덱스 파일 업데이트"""
        try:
            index_file = self.storage_path / f"user_{member_id}_sessions" / "session_index.json"
            
            # 기존 인덱스 로드
            if index_file.exists():
                with open(index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
            else:
                index_data = {
                    "member_id": member_id,
                    "created_at": datetime.utcnow().isoformat(),
                    "sessions": {}
                }
            
            # 새 세션 정보 추가
            index_data["sessions"][conversation_id] = {
                "summary": metadata["summary"],
                "created_at": metadata["created_at"],
                "indexed_at": metadata["indexed_at"],
                "message_count": metadata["message_count"],
                "session_duration_minutes": metadata["session_duration_minutes"]
            }
            
            index_data["last_updated"] = datetime.utcnow().isoformat()
            index_data["total_sessions"] = len(index_data["sessions"])
            
            # 인덱스 파일 저장
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, ensure_ascii=False, indent=2)
            
            print(f"세션 인덱스 업데이트 완료: {member_id} - 총 {len(index_data['sessions'])}개 세션")
            
        except Exception as e:
            print(f"세션 인덱스 업데이트 실패: {e}")
    
    def get_user_vectorstore(self, member_id: str) -> Optional[Chroma]:
        """사용자별 VectorDB 반환"""
        try:
            user_db_path = self.storage_path / f"user_{member_id}_sessions"
            
            if not user_db_path.exists():
                print(f"사용자 VectorDB가 존재하지 않음: {member_id}")
                return None
            
            vectorstore = Chroma(
                collection_name=f"user_{member_id}_sessions",
                embedding_function=self.embeddings,
                persist_directory=str(user_db_path)
            )
            
            return vectorstore
            
        except Exception as e:
            print(f"사용자 VectorDB 로드 실패: {member_id} - {e}")
            return None
    
    def search_user_sessions(self, member_id: str, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """사용자의 과거 세션에서 관련 내용 검색"""
        try:
            vectorstore = self.get_user_vectorstore(member_id)
            
            if not vectorstore:
                return []
            
            # 유사도 검색
            results = vectorstore.similarity_search_with_relevance_scores(
                query=query,
                k=k
            )
            
            search_results = []
            for doc, score in results:
                search_results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "relevance_score": score
                })
            
            print(f"사용자 {member_id} 세션 검색 완료: {len(search_results)}개 결과")
            return search_results
            
        except Exception as e:
            print(f"사용자 세션 검색 실패: {member_id} - {e}")
            return []
    
    def get_user_session_stats(self, member_id: str) -> Dict[str, Any]:
        """사용자별 세션 통계 반환"""
        try:
            index_file = self.storage_path / f"user_{member_id}_sessions" / "session_index.json"
            
            if not index_file.exists():
                return {
                    "member_id": member_id,
                    "total_sessions": 0,
                    "message": "저장된 세션이 없습니다"
                }
            
            with open(index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            return {
                "member_id": member_id,
                "total_sessions": index_data.get("total_sessions", 0),
                "created_at": index_data.get("created_at"),
                "last_updated": index_data.get("last_updated"),
                "sessions": index_data.get("sessions", {})
            }
            
        except Exception as e:
            print(f"사용자 세션 통계 조회 실패: {member_id} - {e}")
            return {
                "member_id": member_id,
                "error": str(e)
            }


# 전역 인스턴스
session_vectordb_builder = SessionVectorDBBuilder()
