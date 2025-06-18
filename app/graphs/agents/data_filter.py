# data_filter.py

from typing import Dict, Any, List, Union
import logging


class DataFilter:
    """데이터 필터링을 담당하는 클래스"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def filter_meaningful_career_cases(self, career_cases: List[Any]) -> List[Any]:
        """커리어 사례 필터링 - 완화된 버전 (빈 내용이 아니면 모두 포함)"""
        if not career_cases:
            return []
        
        meaningful_cases = []
        
        for case in career_cases:
            # 이미 딕셔너리로 변환된 경우
            if isinstance(case, dict) and 'content' in case:
                content = case.get('content', '')
                # 필터링 기준을 매우 완화 - 빈 문자열이 아니면 모두 포함
                if content and str(content).strip():
                    meaningful_cases.append(case)
            
            # Document 객체인 경우 (fallback)
            elif hasattr(case, 'page_content'):
                content = case.page_content
                # 빈 내용이 아니면 모두 포함
                if content and str(content).strip():
                    meaningful_cases.append({
                        'content': content,
                        'metadata': case.metadata if hasattr(case, 'metadata') else {},
                        'source': 'document_object'
                    })
        
        self.logger.info(f"커리어 사례 필터링: {len(meaningful_cases)}개 (원본: {len(career_cases)}개)")
        return meaningful_cases

    def filter_meaningful_chat_history(self, chat_history: List[Any]) -> List[Any]:
        """의미 있는 대화 히스토리만 필터링 (완화된 기준)"""
        if not chat_history:
            return []
        
        meaningful_history = []
        for chat in chat_history:
            if not isinstance(chat, dict):
                continue
                
            # 기본적인 세션 정보가 있으면 포함 (매우 완화된 기준)
            has_session_id = chat.get('session_id') and not self.is_empty_value(chat.get('session_id'))
            has_user_id = chat.get('user_id') and not self.is_empty_value(chat.get('user_id'))
            
            # messages 배열이 있고 비어있지 않은지 확인
            messages = chat.get('messages', [])
            has_messages = isinstance(messages, list) and len(messages) > 0
            
            # messages 내용 확인
            has_meaningful_messages = False
            if has_messages:
                for message in messages:
                    if isinstance(message, dict):
                        content = message.get('content', '')
                        role = message.get('role', '')
                        # 내용이 있고 역할이 있으면 의미있는 메시지로 간주
                        if content and not self.is_empty_value(content) and role:
                            has_meaningful_messages = True
                            break
            
            # 레거시 format 지원 (question/response 필드)
            has_question = chat.get('question') and not self.is_empty_value(chat.get('question'))
            has_response = chat.get('response') and not self.is_empty_value(chat.get('response'))
            
            # 다음 중 하나라도 만족하면 포함 (매우 관대한 기준)
            if (has_session_id or has_user_id or has_meaningful_messages or 
                has_question or has_response):
                meaningful_history.append(chat)
        
        self.logger.info(f"대화 히스토리 필터링 : {len(meaningful_history)}개 (원본: {len(chat_history)}개)")
        return meaningful_history
    
    def has_meaningful_data(self, data: Union[Dict, List, Any]) -> bool:
        """데이터에 의미있는 내용이 있는지 확인 (개선된 버전)"""
        if not data:
            return False
        
        if isinstance(data, dict):
            # 오류 상태인 경우 의미 없는 데이터로 간주
            if data.get("error"):
                return False
                
            for key, value in data.items():
                if key == "error":  # 에러 필드는 건너뛰기
                    continue
                    
                if not self.is_empty_value(value):
                    if isinstance(value, (dict, list)):
                        if self.has_meaningful_data(value):
                            return True
                    else:
                        # 문자열이 충분히 긴지 확인을 완화 (1자 이상이면 OK)
                        if isinstance(value, str) and len(value.strip()) >= 1:
                            return True
                        elif not isinstance(value, str):
                            return True
            return False
        
        elif isinstance(data, list):
            for item in data:
                if not self.is_empty_value(item):
                    if isinstance(item, (dict, list)):
                        if self.has_meaningful_data(item):
                            return True
                    else:
                        return True
            return False
        
        else:
            return not self.is_empty_value(data)
    
    def is_empty_value(self, value: Any) -> bool:
        """값이 비어있는지 확인 (개선된 버전)"""
        if value is None:
            return True
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return True
            # 의미 없는 값들 확인
            empty_indicators = ['*정보 없음*', '정보 없음', '', 'N/A', 'n/a', 'null', 
                               'undefined', 'None', '빈 목록', '내용 없음', 'no data']
            if stripped.lower() in [indicator.lower() for indicator in empty_indicators]:
                return True
            # 너무 짧은 문자열 필터링을 완화 (1자 이상이면 OK)
            if len(stripped) < 1:
                return True
        if isinstance(value, (list, dict)) and not value:
            return True
        return False
