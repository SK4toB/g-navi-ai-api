# app/graphs/nodes/chat_history.py
# 과거 대화내역 검색 노드

import logging
from datetime import datetime
from app.graphs.state import ChatState
from app.graphs.agents.retriever import CareerEnsembleRetrieverAgent


class ChatHistoryNode:
    """과거 대화내역 검색 노드"""

    def __init__(self, graph_builder_instance):
        self.graph_builder = graph_builder_instance
        self.career_retriever_agent = CareerEnsembleRetrieverAgent()
        self.logger = logging.getLogger(__name__)

    def retrieve_chat_history_node(self, state: ChatState) -> ChatState:
        """1단계: 과거 대화내역 검색 및 현재 대화 추가"""
        start_time = datetime.now()
        try:
            self.logger.info("=== 1단계: 과거 대화내역 검색 ===")
            
            # MemorySaver에서 복원된 기존 current_session_messages 확인
            if "current_session_messages" not in state or state["current_session_messages"] is None:
                state["current_session_messages"] = []
                self.logger.info("새로운 대화 세션 시작")
            else:
                self.logger.info(f"MemorySaver에서 복원된 대화 내역: {len(state['current_session_messages'])}개")
            
            # 현재 사용자 질문을 대화 내역에 추가
            current_user_message = {
                "role": "user",
                "content": state["user_question"],
                "timestamp": datetime.now().isoformat()
            }
            state["current_session_messages"].append(current_user_message)
            self.logger.info(f"현재 사용자 메시지 추가: {state['user_question'][:100]}...")
            
            # 세션 정보에서 사용자 데이터 가져오기
            user_data = self.graph_builder.get_user_info_from_session(state)
            user_id = user_data.get("memberId") if "memberId" in user_data else user_data.get("name")
            
            if user_id:
                self.logger.info(f"사용자 {user_id}의 과거 대화내역 검색 중...")
                chat_results = self.career_retriever_agent.load_chat_history(user_id=user_id)
            else:
                self.logger.warning("사용자 ID가 없어 전체 대화내역을 로드합니다")
                chat_results = self.career_retriever_agent.load_chat_history()
            
            state["previous_conversations_found"] = chat_results
            
            # 대화 내역 로그 출력
            current_session_count = len(state["current_session_messages"])
            self.logger.info(f"현재 세션 대화 내역: {current_session_count}개 메시지")
            if current_session_count > 1:
                self.logger.info("최근 대화:")
                for i, msg in enumerate(state["current_session_messages"][-3:], 1):  # 최근 3개만 로그
                    self.logger.info(f"  {i}. {msg['role']}: {msg['content'][:100]}...")
            
            state["processing_log"].append(f"과거 대화내역 검색 완료: {len(chat_results)}개 (사용자: {user_id or 'ALL'})")
            state["processing_log"].append(f"현재 세션 대화 내역: {current_session_count}개")
            self.logger.info(f"과거 대화내역 검색 완료: {len(chat_results)}개")
            
        except Exception as e:
            error_msg = f"과거 대화내역 검색 실패: {e}"
            self.logger.error(error_msg)
            state["error_messages"].append(error_msg)
            state["previous_conversations_found"] = []
            # 오류가 있어도 현재 대화는 유지
            if "current_session_messages" not in state:
                state["current_session_messages"] = [{"role": "user", "content": state["user_question"]}]
        
        processing_time = (datetime.now() - start_time).total_seconds()
        state["processing_log"].append(f"1단계 처리 시간: {processing_time:.2f}초")
        return state
