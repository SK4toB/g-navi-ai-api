# app/services/conversation_history_manager.py

from typing import List, Dict, Any
from datetime import datetime

class ConversationHistoryManager:
    """
    세션별 대화 히스토리 관리 서비스
    """
    
    def __init__(self, max_messages: int = 20):
        """
        초기화
        max_messages: 최대 저장할 메시지 수 (토큰 절약을 위해)
        """
        self.session_histories: Dict[str, List[Dict[str, Any]]] = {}
        self.max_messages = max_messages
        print(f"ConversationHistoryManager 초기화 (최대 {max_messages}개 메시지)")
    
    def add_message(self, conversation_id: str, role: str, content: str, metadata: Dict[str, Any] = None):
        """
        대화 히스토리에 메시지 추가
        
        Args:
            conversation_id: 대화방 ID
            role: 'user' 또는 'assistant'
            content: 메시지 내용
            metadata: 추가 메타데이터 (선택)
        """
        if conversation_id not in self.session_histories:
            self.session_histories[conversation_id] = []
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        self.session_histories[conversation_id].append(message)
        
        # 최대 메시지 수 제한
        if len(self.session_histories[conversation_id]) > self.max_messages:
            # 가장 오래된 2개 메시지 제거 (user-assistant 쌍)
            self.session_histories[conversation_id] = self.session_histories[conversation_id][2:]
        
        print(f"메시지 추가: {conversation_id} ({role}) - 총 {len(self.session_histories[conversation_id])}개")
    
    def get_history(self, conversation_id: str) -> List[Dict[str, str]]:
        """
        OpenAI API 형식으로 대화 히스토리 반환
        
        Returns:
            OpenAI messages 형식의 리스트
        """
        if conversation_id not in self.session_histories:
            return []
        
        # OpenAI API 형식으로 변환 (timestamp, metadata 제거)
        openai_messages = []
        for msg in self.session_histories[conversation_id]:
            openai_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        return openai_messages
    
    def get_history_with_metadata(self, conversation_id: str) -> List[Dict[str, Any]]:
        """
        메타데이터 포함한 전체 히스토리 반환
        """
        return self.session_histories.get(conversation_id, [])
    
    def clear_history(self, conversation_id: str):
        """특정 대화방의 히스토리 삭제"""
        if conversation_id in self.session_histories:
            del self.session_histories[conversation_id]
            print(f"대화 히스토리 삭제: {conversation_id}")
    
    def get_history_summary(self, conversation_id: str) -> Dict[str, Any]:
        """대화 히스토리 요약 정보"""
        if conversation_id not in self.session_histories:
            return {
                "conversation_id": conversation_id,
                "message_count": 0,
                "user_messages": 0,
                "assistant_messages": 0,
                "first_message_time": None,
                "last_message_time": None
            }
        
        messages = self.session_histories[conversation_id]
        user_count = len([m for m in messages if m["role"] == "user"])
        assistant_count = len([m for m in messages if m["role"] == "assistant"])
        
        return {
            "conversation_id": conversation_id,
            "message_count": len(messages),
            "user_messages": user_count,
            "assistant_messages": assistant_count,
            "first_message_time": messages[0]["timestamp"] if messages else None,
            "last_message_time": messages[-1]["timestamp"] if messages else None
        }
    
    def get_all_active_conversations(self) -> List[str]:
        """활성 대화방 ID 목록"""
        return list(self.session_histories.keys())
    
    def cleanup_old_conversations(self, max_age_hours: int = 24):
        """
        오래된 대화 정리 (향후 구현 예정)
        """
        # TODO: timestamp 기반으로 오래된 대화 정리
        pass