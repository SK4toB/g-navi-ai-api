# app/graphs/nodes/chat_history.py
# 현재 세션 대화내역 관리 노드

import logging
from datetime import datetime
from app.graphs.state import ChatState


class ChatHistoryNode:
    """현재 세션 대화내역 관리 노드"""

    def __init__(self, graph_builder_instance):
        self.graph_builder = graph_builder_instance
        self.logger = logging.getLogger(__name__)

    def retrieve_chat_history_node(self, state: ChatState) -> ChatState:
        """1단계: 현재 세션 대화내역 관리"""
        import time
        start_time = time.perf_counter()
        
        try:
            # 메시지 검증 실패 시 처리 건너뛰기
            if state.get("workflow_status") == "validation_failed":
                print(f"⚠️  [1단계] 메시지 검증 실패로 처리 건너뛰기")
                return state
                
            print(f"\n💬 [1단계] 현재 세션 대화내역 관리 시작...")
            self.logger.info("=== 1단계: 현재 세션 대화내역 관리 ===")
            
            # MemorySaver에서 복원된 기존 current_session_messages 확인
            # LangGraph는 이전 실행의 상태를 자동으로 복원함
            if "current_session_messages" not in state or state["current_session_messages"] is None:
                state["current_session_messages"] = []
                self.logger.info("새로운 대화 세션 시작 - 빈 current_session_messages 초기화")
            else:
                restored_count = len(state["current_session_messages"])
                self.logger.info(f"MemorySaver에서 복원된 대화 내역: {restored_count}개")
                if restored_count > 0:
                    self.logger.info("최근 복원된 대화:")
                    for i, msg in enumerate(state["current_session_messages"][-3:], 1):
                        role = msg.get("role", "unknown")
                        content = msg.get("content", "")[:100]
                        timestamp = msg.get("timestamp", "")
                        self.logger.info(f"  복원 {i}. [{role}] {content}... ({timestamp})")
            
            # 현재 사용자 질문을 대화 내역에 추가
            current_user_message = {
                "role": "user",
                "content": state["user_question"],
                "timestamp": datetime.now().isoformat()
            }
            state["current_session_messages"].append(current_user_message)
            self.logger.info(f"현재 사용자 메시지 추가: {state['user_question'][:100]}...")
            self.logger.info(f"총 current_session_messages 개수: {len(state['current_session_messages'])}개")
            
            state["processing_log"].append(f"현재 세션 대화 내역 관리 완료: {len(state['current_session_messages'])}개")
            
            # 처리 시간 계산 및 로그
            end_time = time.perf_counter()
            step_time = end_time - start_time
            
            if step_time < 0.001:
                time_display = f"{step_time * 1000000:.0f}μs"
            elif step_time < 0.01:
                time_display = f"{step_time * 1000:.1f}ms"
            else:
                time_display = f"{step_time:.3f}초"
            
            processing_log = state.get("processing_log", [])
            processing_log.append(f"1단계 처리 시간: {time_display}")
            state["processing_log"] = processing_log
            
            print(f"✅ [1단계] 현재 세션 대화내역 관리 완료")
            print(f"📊 복원된 메시지: {len(state['current_session_messages'])-1}개, 현재 추가: 1개")
            print(f"⏱️  [1단계] 처리 시간: {time_display}")
            
            self.logger.info(f"현재 세션 대화 내역 관리 완료")
            
        except Exception as e:
            # 오류 발생 시에도 처리 시간 기록
            end_time = time.perf_counter()
            step_time = end_time - start_time
            
            if step_time < 0.001:
                time_display = f"{step_time * 1000000:.0f}μs"
            elif step_time < 0.01:
                time_display = f"{step_time * 1000:.1f}ms"
            else:
                time_display = f"{step_time:.3f}초"
                
            processing_log = state.get("processing_log", [])
            processing_log.append(f"1단계 처리 시간 (오류): {time_display}")
            state["processing_log"] = processing_log
            
            error_msg = f"현재 세션 대화 내역 관리 실패: {e}"
            self.logger.error(error_msg)
            state["error_messages"].append(error_msg)
            
            print(f"❌ [1단계] 대화내역 관리 오류: {time_display} (오류: {e})")
            
            # 오류가 있어도 현재 대화는 유지
            if "current_session_messages" not in state:
                state["current_session_messages"] = [{"role": "user", "content": state["user_question"], "timestamp": datetime.now().isoformat()}]
        
        return state