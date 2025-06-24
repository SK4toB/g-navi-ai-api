# app/services/session_manager.py

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta


class SessionManager:
    """
    채팅 세션 관리 전담 클래스
    - 세션 생성/조회/삭제
    - 세션 상태 관리
    - 자동 정리
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
    
    def close_session(self, conversation_id: str) -> Dict[str, Any]:
        """단일 세션 종료"""
        if conversation_id not in self.active_sessions:
            return {
                "status": "not_found",
                "message": f"세션 {conversation_id}을 찾을 수 없습니다",
                "conversation_id": conversation_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        session = self.active_sessions[conversation_id]
        user_name = session.get("user_info", {}).get("name", "Unknown")
        created_at = session.get("created_at")
        now = datetime.utcnow()
        session_age_minutes = int((now - created_at).total_seconds() / 60)
        
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
        # MemorySaver 스레드 정리
        try:
            # LangGraph의 MemorySaver는 자동으로 관리되므로 특별한 정리 불필요
            # 세션 메타데이터만 제거
            if conversation_id in self.active_sessions:
                del self.active_sessions[conversation_id]
                print(f"세션 메타데이터 삭제: {conversation_id}")
        except Exception as e:
            print(f"세션 정리 실패: {e}")
        # ###################################
        
        # 세션 제거
        del self.active_sessions[conversation_id]
        
        print(f"세션 종료: {conversation_id} (사용자: {user_name}, 지속시간: {session_age_minutes}분)")
        
        return {
            "status": "closed",
            "message": f"세션 {conversation_id}이 성공적으로 종료되었습니다",
            "conversation_id": conversation_id,
            "user_name": user_name,
            "session_age_minutes": session_age_minutes,
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
    
    def cleanup_expired_sessions(self) -> Dict[str, Any]:
        """만료된 세션 정리"""
        if not self.active_sessions:
            return {
                "status": "no_sessions",
                "cleaned_count": 0,
                "message": "정리할 세션이 없습니다"
            }
        
        expired_sessions = []
        now = datetime.utcnow()
        
        for conv_id, session in list(self.active_sessions.items()):
            last_active = session.get("last_active", session.get("created_at"))
            inactive_duration = now - last_active
            
            if inactive_duration > self.session_timeout:
                user_name = session.get("user_info", {}).get("name", "Unknown")
                inactive_minutes = int(inactive_duration.total_seconds() / 60)
                
                expired_sessions.append({
                    "conversation_id": conv_id,
                    "user_name": user_name,
                    "inactive_minutes": inactive_minutes
                })
                
                # 만료된 세션 제거
                del self.active_sessions[conv_id]
                print(f"🧹 만료 세션 정리: {conv_id} (사용자: {user_name}, 비활성: {inactive_minutes}분)")
        
        return {
            "status": "cleanup_completed",
            "cleaned_count": len(expired_sessions),
            "expired_sessions": expired_sessions,
            "remaining_sessions": len(self.active_sessions),
            "message": f"{len(expired_sessions)}개의 만료된 세션을 정리했습니다",
            "timestamp": now.isoformat()
        }
    
    # ============================================================================
    # 자동 세션 정리 기능
    # ============================================================================
    
    async def start_auto_cleanup(self):
        """자동 세션 정리 시작"""
        if self.cleanup_task and not self.cleanup_task.done():
            print("⚠️ 자동 세션 정리가 이미 실행 중입니다")
            return
        
        if not self.auto_cleanup_enabled:
            print("⚠️ 자동 세션 정리가 비활성화되어 있습니다")
            return
        
        print(f"🚀 자동 세션 정리 시작 (주기: {self.cleanup_interval_minutes}분)")
        self.cleanup_task = asyncio.create_task(self._auto_cleanup_loop())
    
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
    
    async def _auto_cleanup_loop(self):
        """자동 정리 루프 (백그라운드 실행)"""
        try:
            while self.auto_cleanup_enabled:
                try:
                    # 만료된 세션 정리
                    cleanup_result = self.cleanup_expired_sessions()
                    self.cleanup_count += 1
                    
                    cleaned_count = cleanup_result.get("cleaned_count", 0)
                    remaining_count = cleanup_result.get("remaining_sessions", 0)
                    current_time = datetime.now().strftime("%H:%M:%S")
                    
                    if cleaned_count > 0:
                        print(f"🧹 [{current_time}] 자동 세션 정리: {cleaned_count}개 정리, {remaining_count}개 유지")
                        self.logger.info(f"자동 세션 정리: {cleaned_count}개 정리됨")
                        
                        # 정리된 세션 상세 로그
                        for session in cleanup_result.get("expired_sessions", []):
                            conv_id = session.get("conversation_id", "")
                            user_name = session.get("user_name", "Unknown")
                            inactive_minutes = session.get("inactive_minutes", 0)
                            print(f"   └─ {conv_id} (사용자: {user_name}, 비활성: {inactive_minutes}분)")
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
    
    async def manual_cleanup(self) -> Dict[str, Any]:
        """수동 세션 정리 (즉시 실행)"""
        try:
            print("🔧 수동 세션 정리 실행...")
            result = self.cleanup_expired_sessions()
            
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