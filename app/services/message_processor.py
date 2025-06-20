# app/services/message_processor.py

from typing import Dict, Any
import traceback


class MessageProcessor:
    """
    메시지 처리 전담 클래스
    - LangGraph 실행
    - 메시지 상태 구성
    - 에러 처리
    """
    
    def __init__(self):
        print("MessageProcessor 초기화")
    
    async def process_message(
        self, 
        graph, 
        config: Dict, 
        conversation_id: str, 
        member_id: str, 
        message_text: str, 
        user_info: Dict[str, Any]
    ) -> str:
        """
        LangGraph를 통한 메시지 처리
        """
        try:
            print(f"MessageProcessor 메시지 처리 시작: {conversation_id} - {message_text[:50]}...")
            
            # 입력 상태 구성
            input_state = self._build_input_state(
                conversation_id=conversation_id,
                member_id=member_id,
                message_text=message_text,
                user_info=user_info
            )
            
            print(f"MessageProcessor LangGraph 실행 시작")
            
            # LangGraph 실행
            result = await graph.ainvoke(input_state, config)
            
            print(f"MessageProcessor LangGraph 실행 완료")
            
            # 응답 추출 및 검증
            bot_message = self._extract_bot_message(result)
            
            print(f"MessageProcessor 최종 응답: {bot_message[:100]}...")
            return bot_message
            
        except Exception as e:
            print(f"MessageProcessor 메시지 처리 실패: {e}")
            print(f"MessageProcessor 상세 에러: {traceback.format_exc()}")
            return self._generate_error_message(str(e))
    
    def _build_input_state(
        self, 
        conversation_id: str, 
        member_id: str, 
        message_text: str, 
        user_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """입력 상태 구성"""
        return {
            "message_text": message_text,
            "member_id": member_id,
            "conversation_id": conversation_id,
            "user_info": user_info,
            # 노드별 처리 결과 초기화
            "intent": None,
            "embedding_vector": None,
            "memory_results": None,
            "similarity_score": None,
            "profiling_data": None,
            "connection_suggestions": None,
            "bot_message": None
        }
    
    def _extract_bot_message(self, result: Dict[str, Any]) -> str:
        """LangGraph 결과에서 봇 메시지 추출"""
        bot_message = result.get("bot_message")
        
        if bot_message is None:
            print("MessageProcessor bot_message가 None입니다")
            print(f"MessageProcessor result 전체 내용: {result}")
            return "죄송합니다. 응답을 생성할 수 없습니다."
        
        return bot_message
    
    def _generate_error_message(self, error_str: str) -> str:
        """에러 시 사용자에게 보여줄 메시지 생성"""
        return f"죄송합니다. 메시지 처리 중 오류가 발생했습니다: {error_str}"