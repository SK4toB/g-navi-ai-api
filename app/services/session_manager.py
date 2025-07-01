# app/services/session_manager.py
"""
* @className : SessionManager
* @description : 채팅 세션 생명주기 관리 및 VectorDB 자동 구축 시스템
*                G-Navi AI 시스템의 채팅 세션 관리를 담당하는 핵심 서비스입니다.
*                세션 생성/조회/삭제, 자동 정리, VectorDB 구축 등을 관리합니다.
*
*                📋 핵심 기능:
*                1. 채팅 세션 생성/조회/삭제 관리
*                2. 세션 만료 시간 추적 및 자동 정리
*                3. 세션 종료 시 VectorDB 자동 구축 트리거
*                4. 백그라운드 정리 작업으로 리소스 최적화
*
*                🔄 VectorDB 통합 플로우:
*                세션 활성화 → 대화 진행 → 세션 종료/만료 → current_session_messages 수집 → VectorDB 구축 → 세션 삭제
*
*                ⚡ 핵심 시점:
*                - 세션 생성: 사용자 첫 메시지 시
*                - VectorDB 구축: 세션 종료/만료 직전 (데이터 손실 방지)
*                - 세션 삭제: VectorDB 구축 완료 후
*
*                🛡️ 안전 장치:
*                - VectorDB 구축 실패 시에도 세션 정리 진행
*                - 이중 삭제 방지 (세션이 이미 삭제된 경우 처리)
*                - 백그라운드 정리 작업 예외 처리
*
* @modification : 2025.07.01(이재원) 최초생성
*
* @author 이재원
* @Date 2025.07.01
* @version 1.0
* @see VectorDB, ChromaService, asyncio
*  == 개정이력(Modification Information) ==
*  
*   수정일        수정자        수정내용
*   ----------   --------     ---------------------------
*   2025.07.01   이재원       최초 생성
*  
* Copyright (C) by G-Navi AI System All right reserved.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

# VectorDB 구축을 위한 import 추가
from app.utils.session_vectordb_builder import session_vectordb_builder


class SessionManager:
    """
    🗂️ 채팅 세션 생명주기 관리자
    
    주요 책임:
    - 세션 생성, 조회, 삭제 관리
    - 세션 타임아웃 추적 및 자동 정리
    - 세션 종료 시 VectorDB 구축 트리거 (핵심 기능)
    - 메모리 및 리소스 최적화
    
    🔄 VectorDB 통합 시점:
    1. close_session() 호출 시: 수동 세션 종료 → VectorDB 구축
    2. cleanup_expired_sessions() 실행 시: 자동 만료 → VectorDB 구축
    
    💾 저장되는 데이터:
    - 세션 메타데이터: 생성시간, 사용자 정보, 마지막 활동 시간
    - 대화 내용: current_session_messages → VectorDB
    """
    
    def __init__(self, session_timeout_hours: int = 1):
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        # 실제 서비스용: 세션 타임아웃 30분으로 설정
        self.session_timeout = timedelta(minutes=30)  # 30분으로 설정
        
        # 자동 정리 관련
        self.auto_cleanup_enabled = True
        self.cleanup_interval_minutes = 5  # 5분마다 정리 (서비스용)
        self.cleanup_task: Optional[asyncio.Task] = None
        self.cleanup_count = 0
        self.logger = logging.getLogger(__name__)
        
        print(f"SessionManager 초기화 (타임아웃: 30분, 자동정리: {self.cleanup_interval_minutes}분 주기) - 서비스모드")
    
    def create_session(self, conversation_id: str, graph, thread_id: str, config: Dict, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """새 세션 생성"""
        now = datetime.utcnow()
        
        session_data = {
            "graph": graph,
            "thread_id": thread_id,
            "config": config,
            "user_info": user_info,
            "created_at": now,
            "last_active": now,
            "status": "active"
        }
        
        self.active_sessions[conversation_id] = session_data
        
        print(f"세션 생성: {conversation_id} (사용자: {user_info.get('name', 'Unknown')})")
        
        return session_data
    
    def get_session(self, conversation_id: str) -> Dict[str, Any]:
        """세션 조회"""
        return self.active_sessions.get(conversation_id)
    
    def update_last_active(self, conversation_id: str) -> bool:
        """마지막 활동 시간 업데이트"""
        if conversation_id in self.active_sessions:
            self.active_sessions[conversation_id]["last_active"] = datetime.utcnow()
            return True
        return False
    
    def is_session_expired(self, conversation_id: str) -> bool:
        """세션 만료 여부 확인"""
        session = self.get_session(conversation_id)
        if not session:
            return True
        
        now = datetime.utcnow()
        last_active = session.get("last_active", session.get("created_at"))
        inactive_duration = now - last_active
        
        return inactive_duration > self.session_timeout
    
    async def close_session(self, conversation_id: str, current_session_messages: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        🔚 세션 종료 및 VectorDB 구축 (핵심 메서드)
        
        Args:
            conversation_id: 종료할 세션 ID
            current_session_messages: 세션의 모든 대화 메시지들 (VectorDB 구축용)
                                    [{"role": "user/assistant", "content": "..."}] 형태
        
        Returns:
            Dict: 종료 결과 (VectorDB 구축 성공 여부 포함)
            
        🔄 처리 순서:
        1. 세션 존재 여부 확인
        2. 세션 메타데이터 수집 (사용자 정보, 세션 지속시간 등)
        3. ⭐ VectorDB 구축 실행 (current_session_messages 사용)
        4. 세션 메타데이터 삭제
        5. 결과 반환 (VectorDB 구축 성공/실패 여부 포함)
        
        ⚠️ 중요: VectorDB 구축 실패 시에도 세션은 정상 삭제됨 (리소스 누수 방지)
        """
        print(f"🔚 close_session 시작: {conversation_id}")
        print(f"📊 전달받은 current_session_messages: {len(current_session_messages) if current_session_messages else 0}개")
        
        if current_session_messages:
            print(f"📋 current_session_messages 내용 확인:")
            for i, msg in enumerate(current_session_messages):
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')[:50]
                print(f"     #{i+1} {role}: {content}{'...' if len(msg.get('content', '')) > 50 else ''}")
        else:
            print(f"⚠️ current_session_messages가 비어있거나 None입니다")
        
        if conversation_id not in self.active_sessions:
            return {
                "status": "not_found",
                "message": f"세션 {conversation_id}을 찾을 수 없습니다",
                "conversation_id": conversation_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # 📊 세션 기본 정보 수집
        session = self.active_sessions[conversation_id]
        user_name = session.get("user_info", {}).get("name", "Unknown")
        
        # 🔍 member_id 추출 (여러 필드에서 시도)
        user_info = session.get("user_info", {})
        member_id = (
            user_info.get("member_id") or           # API에서 추가한 member_id
            user_info.get("id") or                  # 기존 id 필드
            user_info.get("memberId") or            # camelCase 필드
            user_info.get("user_id") or             # 다른 가능한 필드
            "unknown"                               # 최후 폴백
        )
        
        print(f"🔍 VectorDB용 member_id 추출: {member_id} (user_info: {user_info})")
        
        created_at = session.get("created_at")
        now = datetime.utcnow()
        session_age_minutes = int((now - created_at).total_seconds() / 60)
        
        # 🗃️ VectorDB 구축 (세션 종료 전에 실행 - 데이터 손실 방지)
        vectordb_success = False
        if current_session_messages:
            try:
                print(f"🗃️ VectorDB 구축 시작...")
                print(f"   📊 메시지 수: {len(current_session_messages)}개")
                print(f"   👤 사용자: {user_name} (member_id: {member_id})")
                
                # VectorDB 구축에 필요한 세션 메타데이터 준비
                session_metadata = {
                    "created_at": created_at,
                    "session_duration_minutes": session_age_minutes,
                    "last_active": session.get("last_active", created_at)
                }
                
                # SessionVectorDBBuilder를 통한 VectorDB 구축 실행
                vectordb_success = await session_vectordb_builder.build_vector_db(
                    conversation_id=conversation_id,
                    member_id=str(member_id),          # 사용자별 VectorDB 분리
                    user_name=user_name,
                    messages=current_session_messages,  # 실제 대화 내용
                    session_metadata=session_metadata
                )
                
                if vectordb_success:
                    print(f"✅ VectorDB 구축 성공: {conversation_id}")
                else:
                    print(f"❌ VectorDB 구축 실패: {conversation_id}")
                    
            except Exception as e:
                print(f"❌ VectorDB 구축 중 예외 발생: {conversation_id} - {e}")
                import traceback
                traceback.print_exc()
                vectordb_success = False                
        else:
            print(f"⚠️ current_session_messages가 없어서 VectorDB 구축 생략: {conversation_id}")
        
        # ###################################
        # # 대화 히스토리도 함께 삭제
        # try:
        #     from app.core.dependencies import get_service_container
        #     container = get_service_container()
        #     history_manager = container.history_manager
        #     history_manager.clear_history(conversation_id)
        #     print(f"대화 히스토리 삭제 완료: {conversation_id}")
        # except Exception as e:
        #     print(f"대화 히스토리 삭제 실패: {e}")
        # ####################################

        # ####################################
        # MemorySaver 스레드 정리 및 세션 제거
        try:
            # LangGraph의 MemorySaver는 자동으로 관리되므로 특별한 정리 불필요
            # 세션 메타데이터 제거
            if conversation_id in self.active_sessions:
                del self.active_sessions[conversation_id]
                print(f"세션 메타데이터 삭제: {conversation_id}")
            else:
                print(f"⚠️ 세션이 이미 삭제됨: {conversation_id}")
        except Exception as e:
            print(f"세션 정리 실패: {e}")
        # ###################################
        
        print(f"세션 종료: {conversation_id} (사용자: {user_name}, 지속시간: {session_age_minutes}분, VectorDB: {'성공' if vectordb_success else '실패'})")
        
        return {
            "status": "closed",
            "message": f"세션 {conversation_id}이 성공적으로 종료되었습니다",
            "conversation_id": conversation_id,
            "user_name": user_name,
            "session_age_minutes": session_age_minutes,
            "vectordb_built": vectordb_success,
            "closed_at": now.isoformat()
        }
    
    def close_all_sessions(self) -> Dict[str, Any]:
        """모든 세션 종료"""
        if not self.active_sessions:
            return {
                "status": "no_sessions",
                "message": "종료할 활성 세션이 없습니다",
                "closed_sessions": [],
                "timestamp": datetime.utcnow().isoformat()
            }
        
        closed_sessions = []
        now = datetime.utcnow()
        
        for conv_id, session in list(self.active_sessions.items()):
            user_name = session.get("user_info", {}).get("name", "Unknown")
            created_at = session.get("created_at")
            session_age_minutes = int((now - created_at).total_seconds() / 60)
            
            closed_sessions.append({
                "conversation_id": conv_id,
                "user_name": user_name,
                "session_age_minutes": session_age_minutes
            })
            
            print(f"전체 종료: {conv_id} (사용자: {user_name})")
        
        # 모든 세션 제거
        total_closed = len(self.active_sessions)
        self.active_sessions.clear()
        
        print(f"전체 {total_closed}개 세션 종료 완료")
        
        return {
            "status": "all_closed",
            "message": f"총 {total_closed}개의 세션이 종료되었습니다",
            "closed_sessions": closed_sessions,
            "total_closed": total_closed,
            "timestamp": now.isoformat()
        }
    
    def close_sessions_by_user(self, user_name: str) -> Dict[str, Any]:
        """특정 사용자의 모든 세션 종료"""
        if not self.active_sessions:
            return {
                "status": "no_sessions",
                "message": "활성 세션이 없습니다",
                "user_name": user_name,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        user_sessions = []
        now = datetime.utcnow()
        
        # 해당 사용자의 세션 찾기
        for conv_id, session in list(self.active_sessions.items()):
            session_user_name = session.get("user_info", {}).get("name", "")
            
            if session_user_name == user_name:
                created_at = session.get("created_at")
                session_age_minutes = int((now - created_at).total_seconds() / 60)
                
                user_sessions.append({
                    "conversation_id": conv_id,
                    "session_age_minutes": session_age_minutes
                })
                
                # 세션 제거
                del self.active_sessions[conv_id]
                print(f"사용자별 종료: {conv_id} (사용자: {user_name})")
        
        if not user_sessions:
            return {
                "status": "user_not_found",
                "message": f"사용자 '{user_name}'의 활성 세션을 찾을 수 없습니다",
                "user_name": user_name,
                "timestamp": now.isoformat()
            }
        
        print(f"사용자 {user_name}의 {len(user_sessions)}개 세션 종료 완료")
        
        return {
            "status": "user_sessions_closed",
            "message": f"사용자 '{user_name}'의 {len(user_sessions)}개 세션이 종료되었습니다",
            "user_name": user_name,
            "closed_sessions": user_sessions,
            "total_closed": len(user_sessions),
            "timestamp": now.isoformat()
        }
    
    def get_session_status(self, conversation_id: str) -> Dict[str, Any]:
        """세션 상태 조회"""
        if conversation_id in self.active_sessions:
            return {
                "conversation_id": conversation_id,
                "status": "active",
                "thread_id": self.active_sessions[conversation_id]["thread_id"]
            }
        return {"conversation_id": conversation_id, "status": "inactive"}
    
    def get_session_health(self, conversation_id: str) -> Dict[str, Any]:
        """특정 세션의 상세 헬스 정보"""
        now = datetime.utcnow()
        
        if conversation_id not in self.active_sessions:
            return {
                "conversation_id": conversation_id,
                "status": "not_found",
                "message": "세션이 존재하지 않습니다",
                "timestamp": now.isoformat()
            }
        
        session = self.active_sessions[conversation_id]
        created_at = session.get("created_at")
        last_active = session.get("last_active")
        
        # 시간 계산
        alive_duration = now - created_at
        inactive_duration = now - last_active
        
        # 만료 여부 체크
        is_expired = inactive_duration > self.session_timeout
        
        return {
            "conversation_id": conversation_id,
            "status": "expired" if is_expired else "active",
            "created_at": created_at.isoformat(),
            "last_active": last_active.isoformat(),
            "alive_minutes": int(alive_duration.total_seconds() / 60),
            "inactive_minutes": int(inactive_duration.total_seconds() / 60),
            "timeout_minutes": int(self.session_timeout.total_seconds() / 60),
            "expires_in_minutes": max(0, int((self.session_timeout - inactive_duration).total_seconds() / 60)),
            "thread_id": session.get("thread_id"),
            "message": "정상 활성화된 세션입니다" if not is_expired else f"{int(inactive_duration.total_seconds() / 60)}분 비활성으로 만료되었습니다",
            "timestamp": now.isoformat()
        }
    
    def get_all_active_sessions(self) -> Dict[str, Any]:
        """전체 활성 세션 정보"""
        now = datetime.utcnow()
        
        if not self.active_sessions:
            return {
                "total_sessions": 0,
                "sessions": [],
                "message": "현재 활성화된 세션이 없습니다",
                "timestamp": now.isoformat()
            }
        
        sessions_list = []
        
        for conv_id, session in self.active_sessions.items():
            created_at = session.get("created_at")
            last_active = session.get("last_active", created_at)
            
            # 시간 계산
            alive_minutes = int((now - created_at).total_seconds() / 60)
            inactive_minutes = int((now - last_active).total_seconds() / 60)
            
            sessions_list.append({
                "conversation_id": conv_id,
                "user_name": session.get("user_info", {}).get("name", "Unknown"),
                "alive_minutes": alive_minutes,
                "inactive_minutes": inactive_minutes,
                "last_active": last_active.isoformat(),
                "thread_id": session.get("thread_id")
            })
        
        # inactive_minutes 기준으로 정렬 (오래 비활성인 것부터)
        sessions_list.sort(key=lambda x: x["inactive_minutes"], reverse=True)
        
        return {
            "total_sessions": len(self.active_sessions),
            "sessions": sessions_list,
            "session_timeout_minutes": int(self.session_timeout.total_seconds() / 60),
            "message": f"현재 {len(self.active_sessions)}개의 세션이 활성화되어 있습니다",
            "timestamp": now.isoformat()
        }
    
    async def cleanup_expired_sessions(self, get_session_messages_func=None) -> Dict[str, Any]:
        """만료된 세션 정리 (VectorDB 구축 포함)"""
        if not self.active_sessions:
            return {
                "status": "no_sessions",
                "cleaned_count": 0,
                "message": "정리할 세션이 없습니다"
            }
        
        expired_sessions = []
        vectordb_results = []
        now = datetime.utcnow()
        
        for conv_id, session in list(self.active_sessions.items()):
            last_active = session.get("last_active", session.get("created_at"))
            inactive_duration = now - last_active
            
            if inactive_duration > self.session_timeout:
                user_name = session.get("user_info", {}).get("name", "Unknown")
                
                # 🔍 member_id 추출 (여러 필드에서 시도) - close_session과 동일한 로직
                user_info = session.get("user_info", {})
                member_id = (
                    user_info.get("member_id") or           # API에서 추가한 member_id
                    user_info.get("id") or                  # 기존 id 필드
                    user_info.get("memberId") or            # camelCase 필드
                    user_info.get("user_id") or             # 다른 가능한 필드
                    "unknown"                               # 최후 폴백
                )
                
                print(f"🔍 자동정리 VectorDB용 member_id 추출: {member_id} (user_info: {user_info})")
                
                inactive_minutes = int(inactive_duration.total_seconds() / 60)
                session_age_minutes = int((now - session.get("created_at")).total_seconds() / 60)
                
                # VectorDB 구축을 위해 current_session_messages 가져오기
                current_messages = []
                vectordb_success = False
                
                if get_session_messages_func:
                    try:
                        current_messages = get_session_messages_func(conv_id)
                        
                        if current_messages:
                            session_metadata = {
                                "created_at": session.get("created_at"),
                                "session_duration_minutes": session_age_minutes,
                                "last_active": last_active
                            }
                            
                            vectordb_success = await session_vectordb_builder.build_vector_db(
                                conversation_id=conv_id,
                                member_id=str(member_id),
                                user_name=user_name,
                                messages=current_messages,
                                session_metadata=session_metadata
                            )
                            
                    except Exception as e:
                        print(f"❌ 자동 정리 중 VectorDB 구축 실패: {conv_id} - {e}")
                        vectordb_success = False
                
                expired_sessions.append({
                    "conversation_id": conv_id,
                    "user_name": user_name,
                    "inactive_minutes": inactive_minutes,
                    "message_count": len(current_messages) if current_messages else 0,
                    "vectordb_built": vectordb_success
                })
                
                vectordb_results.append({
                    "conversation_id": conv_id,
                    "vectordb_success": vectordb_success,
                    "message_count": len(current_messages) if current_messages else 0
                })
                
                # 만료된 세션 제거
                del self.active_sessions[conv_id]
                vectordb_status = "📚" if vectordb_success else "⚠️"
                print(f"🧹 만료 세션 정리: {conv_id} (사용자: {user_name}, 비활성: {inactive_minutes}분) {vectordb_status}")
        
        return {
            "status": "cleanup_completed",
            "cleaned_count": len(expired_sessions),
            "expired_sessions": expired_sessions,
            "vectordb_results": vectordb_results,
            "remaining_sessions": len(self.active_sessions),
            "message": f"{len(expired_sessions)}개의 만료된 세션을 정리했습니다",
            "timestamp": now.isoformat()
        }
    
    # ============================================================================
    # 자동 세션 정리 기능
    # ============================================================================
    
    async def start_auto_cleanup(self, get_session_messages_func=None):
        """자동 세션 정리 시작"""
        if self.cleanup_task and not self.cleanup_task.done():
            print("⚠️ 자동 세션 정리가 이미 실행 중입니다")
            return
        
        if not self.auto_cleanup_enabled:
            print("⚠️ 자동 세션 정리가 비활성화되어 있습니다")
            return
        
        print(f"🚀 자동 세션 정리 시작 (주기: {self.cleanup_interval_minutes}분)")
        self.cleanup_task = asyncio.create_task(self._auto_cleanup_loop(get_session_messages_func))
    
    async def stop_auto_cleanup(self):
        """자동 세션 정리 중지"""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            finally:
                self.cleanup_task = None
        
        print(f"🛑 자동 세션 정리 중지 (총 {self.cleanup_count}회 정리 수행)")
    
    async def _auto_cleanup_loop(self, get_session_messages_func=None):
        """자동 정리 루프 (백그라운드 실행)"""
        try:
            while self.auto_cleanup_enabled:
                try:
                    # 만료된 세션 정리 (VectorDB 구축 포함)
                    cleanup_result = await self.cleanup_expired_sessions(get_session_messages_func)
                    self.cleanup_count += 1
                    
                    cleaned_count = cleanup_result.get("cleaned_count", 0)
                    remaining_count = cleanup_result.get("remaining_sessions", 0)
                    vectordb_results = cleanup_result.get("vectordb_results", [])
                    current_time = datetime.now().strftime("%H:%M:%S")
                    
                    if cleaned_count > 0:
                        vectordb_success_count = sum(1 for r in vectordb_results if r.get("vectordb_success", False))
                        print(f"🧹 [{current_time}] 자동 세션 정리: {cleaned_count}개 정리, {remaining_count}개 유지 (VectorDB: {vectordb_success_count}/{cleaned_count})")
                        self.logger.info(f"자동 세션 정리: {cleaned_count}개 정리됨, VectorDB: {vectordb_success_count}개 성공")
                        
                        # 정리된 세션 상세 로그
                        for session in cleanup_result.get("expired_sessions", []):
                            conv_id = session.get("conversation_id", "")
                            user_name = session.get("user_name", "Unknown")
                            inactive_minutes = session.get("inactive_minutes", 0)
                            message_count = session.get("message_count", 0)
                            vectordb_built = session.get("vectordb_built", False)
                            vectordb_icon = "📚" if vectordb_built else "⚠️"
                            print(f"   └─ {conv_id} (사용자: {user_name}, 비활성: {inactive_minutes}분, 메시지: {message_count}개) {vectordb_icon}")
                    else:
                        # 조용한 로그 (정리할 세션이 없을 때는 간단히)
                        if self.cleanup_count % 12 == 1:  # 1시간마다 한 번씩만 로그 출력 (5분 주기)
                            print(f"✅ [{current_time}] 세션 정리 체크: 만료된 세션 없음 ({remaining_count}개 활성)")
                    
                    # 다음 정리까지 대기
                    await asyncio.sleep(self.cleanup_interval_minutes * 60)
                    
                except Exception as e:
                    self.logger.error(f"자동 세션 정리 중 오류: {e}")
                    print(f"❌ 자동 세션 정리 오류: {e}")
                    # 오류 발생 시 1분 후 재시도
                    await asyncio.sleep(60)
                    
        except asyncio.CancelledError:
            print("🔄 자동 세션 정리 태스크가 취소되었습니다")
            raise
    
    async def manual_cleanup(self, get_session_messages_func=None) -> Dict[str, Any]:
        """수동 세션 정리 (즉시 실행, VectorDB 구축 포함)"""
        try:
            print("🔧 수동 세션 정리 실행...")
            result = await self.cleanup_expired_sessions(get_session_messages_func)
            
            return {
                "status": "success",
                "message": "수동 세션 정리 완료",
                "result": result
            }
            
        except Exception as e:
            error_msg = f"수동 세션 정리 실패: {e}"
            self.logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg,
                "error": str(e)
            }
    
    def get_cleanup_status(self) -> Dict[str, Any]:
        """자동 정리 상태 조회"""
        is_running = self.cleanup_task and not self.cleanup_task.done()
        
        return {
            "auto_cleanup_enabled": self.auto_cleanup_enabled,
            "is_running": is_running,
            "cleanup_interval_minutes": self.cleanup_interval_minutes,
            "cleanup_count": self.cleanup_count,
            "session_timeout_hours": self.session_timeout.total_seconds() / 3600,
            "active_sessions_count": len(self.active_sessions),
            "status": "running" if is_running else "stopped"
        }
    
    def set_auto_cleanup_enabled(self, enabled: bool):
        """자동 정리 활성화/비활성화"""
        self.auto_cleanup_enabled = enabled
        status = "활성화" if enabled else "비활성화"
        print(f"🔧 자동 세션 정리 {status}")
    
    def set_cleanup_interval(self, minutes: int):
        """정리 주기 변경 (분 단위)"""
        if minutes < 5:
            minutes = 5  # 최소 5분
        elif minutes > 180:
            minutes = 180  # 최대 3시간
        
        self.cleanup_interval_minutes = minutes
        print(f"🔧 자동 정리 주기 변경: {minutes}분")