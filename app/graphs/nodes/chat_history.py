# app/graphs/nodes/chat_history.py
"""
* @className : ChatHistoryNode
* @description : 채팅 히스토리 노드 모듈
*                대화 내역을 관리하는 워크플로우 노드입니다.
*                이전 대화와 현재 세션의 메시지를 통합 관리합니다.
*
"""

import logging
from datetime import datetime
from typing import List, Dict
from app.graphs.state import ChatState


class ChatHistoryNode:
    """
    현재 세션 대화내역 통합 관리 노드
    
    AgentRAG 워크플로우의 1단계로, 다양한 소스의 대화 내역을 
    통일된 current_session_messages 형식으로 관리합니다.
    """

    def __init__(self, graph_builder_instance):
        self.graph_builder = graph_builder_instance
        self.logger = logging.getLogger(__name__)

    def retrieve_chat_history_node(self, state: ChatState) -> ChatState:
        """
         1단계: 현재 세션 대화내역 통합 관리
        
        SpringBoot 이전 메시지와 MemorySaver 복원 메시지를 통합하여
        current_session_messages로 일원화하고, 현재 사용자 질문을 추가합니다.
        
        Args:
            state: 현재 워크플로우 상태
            
        Returns:
            ChatState: 통합된 대화 내역이 포함된 상태
        """
        import time
        start_time = time.perf_counter()
        
        try:
            # 메시지 검증 실패 시 처리 건너뛰기
            if state.get("workflow_status") == "validation_failed":
                print(f"[1단계] 메시지 검증 실패로 처리 건너뛰기")
                return state
                
            print(f"\n[1단계] 현재 세션 대화내역 관리 시작...")
            self.logger.info("=== 1단계: 현재 세션 대화내역 관리 ===")
            
            # SpringBoot에서 전달받은 이전 메시지를 current_session_messages에 통합
            previous_messages_from_session = self.graph_builder.get_previous_messages_from_session(state)
            
            # MemorySaver에서 복원된 기존 current_session_messages 확인
            # LangGraph는 이전 실행의 상태를 자동으로 복원함
            if "current_session_messages" not in state:
                state["current_session_messages"] = []
                self.logger.info("새로운 대화 세션 시작 - 빈 current_session_messages 초기화")
            elif state["current_session_messages"] is None:
                state["current_session_messages"] = []
                self.logger.info("None 상태의 current_session_messages 초기화")
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
            
            # SpringBoot 이전 메시지를 current_session_messages 앞에 추가 (한 번만)
            if previous_messages_from_session and len(previous_messages_from_session) > 0:
                # 중복 추가 방지: 이미 SpringBoot 메시지가 추가되었는지 확인
                has_restored_messages = any(
                    msg.get("metadata", {}).get("restored_from") == "springboot" 
                    for msg in state["current_session_messages"]
                )
                
                if not has_restored_messages:
                    self.logger.info(f"SpringBoot에서 전달받은 이전 메시지 {len(previous_messages_from_session)}개를 current_session_messages에 통합")
                    restored_messages = self._convert_previous_messages_to_session_format(previous_messages_from_session, state)
                    # 기존 current_session_messages 앞에 SpringBoot 메시지 추가
                    state["current_session_messages"] = restored_messages + state["current_session_messages"]
                    self.logger.info(f"총 {len(state['current_session_messages'])}개 메시지로 통합됨")
                else:
                    self.logger.info("이미 SpringBoot 메시지가 복원되어 있어 건너뜀")
            else:
                self.logger.info("SpringBoot에서 전달받은 이전 메시지 없음")
            
            # 현재 사용자 질문을 대화 내역에 추가
            current_user_message = {
                "role": "user",
                "content": state["user_question"],
                "timestamp": datetime.now().isoformat()
            }
            state["current_session_messages"].append(current_user_message)
            self.logger.info(f"현재 사용자 메시지 추가: {state['user_question'][:100]}...")
            self.logger.info(f"총 current_session_messages 개수: {len(state['current_session_messages'])}개")
            
            #  ConversationHistoryManager에도 사용자 질문 추가 (세션 종료 시 VectorDB 구축을 위해)
            try:
                from app.core.dependencies import get_service_container
                container = get_service_container()
                history_manager = container.history_manager
                
                session_id = state.get("session_id", "")
                if session_id:
                    history_manager.add_message(
                        conversation_id=session_id,
                        role="user",
                        content=state["user_question"],
                        metadata={
                            "timestamp": datetime.now().isoformat(),
                            "source": "chat_history_node"
                        }
                    )
                    print(f"ConversationHistoryManager에 사용자 질문 추가: {session_id}")
                else:
                    print(f"session_id가 없어 ConversationHistoryManager에 추가하지 못함")
            except Exception as e:
                print(f"ConversationHistoryManager에 사용자 질문 추가 실패: {e}")
            
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
            
            print(f"[1단계] 현재 세션 대화내역 관리 완료")
            print(f"복원된 메시지: {len(state['current_session_messages'])-1}개, 현재 추가: 1개")
            print(f"[1단계] 처리 시간: {time_display}")
            
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
            
            print(f"[1단계] 대화내역 관리 오류: {time_display} (오류: {e})")
            
            # 오류가 있어도 현재 대화는 유지
            if "current_session_messages" not in state:
                state["current_session_messages"] = [{"role": "user", "content": state["user_question"], "timestamp": datetime.now().isoformat()}]
        
        return state

    def _convert_previous_messages_to_session_format(self, previous_messages: List, state: ChatState) -> List[Dict[str, str]]:
        """
        SpringBoot 메시지 → current_session_messages 형식 변환
        
        SpringBoot에서 전달받은 이전 메시지들을 current_session_messages 
        표준 형식으로 변환하여 일관된 대화 내역 관리를 지원합니다.
        
        Args:
            previous_messages: SpringBoot에서 전달받은 메시지 리스트
            state: 현재 워크플로우 상태 (사용자 정보 포함)
            
        Returns:
            List[Dict]: current_session_messages 형식으로 변환된 메시지 리스트
        """
        converted_messages = []
        user_data = state.get("user_data", {})
        user_name = user_data.get("name", "사용자")
        
        self.logger.info(f"previous_messages를 session format으로 변환 시작: {len(previous_messages)}개")
        
        for i, message in enumerate(previous_messages, 1):
            try:
                # message 객체의 속성 확인
                sender_type = getattr(message, 'sender_type', None)
                message_text = getattr(message, 'message_text', None)
                timestamp = getattr(message, 'timestamp', None)
                
                if not sender_type or not message_text:
                    continue
                
                # sender_type을 role로 변환
                if sender_type == "USER":
                    role = "user"
                elif sender_type == "BOT":
                    role = "assistant"
                else:
                    self.logger.warning(f"알 수 없는 sender_type: {sender_type}")
                    continue
                
                # current_session_messages 형식으로 변환
                session_message = {
                    "role": role,
                    "content": message_text,
                    "timestamp": str(timestamp) if timestamp else datetime.now().isoformat(),
                    "metadata": {
                        "restored_from": "springboot",
                        "original_index": i,
                        "user_name": user_name if role == "user" else None
                    }
                }
                
                converted_messages.append(session_message)
                self.logger.info(f"변환 완료 ({i}): {role} - {message_text[:50]}...")
                
            except Exception as msg_error:
                self.logger.error(f"개별 메시지 변환 실패: {str(msg_error)}")
                continue
        
        self.logger.info(f"변환 완료: {len(converted_messages)}개 메시지")
        return converted_messages