# app/graphs/nodes/message_check.py
"""
* @className : MessageCheckNode
* @description : 메시지 검증 노드 모듈
*                사용자 입력 메시지를 검증하는 워크플로우 노드입니다.
*                메시지 유효성 검사와 전처리를 담당합니다.
*
"""
# 0️⃣ 메시지 검증 및 상태 초기화 노드

import time
import logging
from app.graphs.state import ChatState


class MessageCheckNode:
    """
    메시지 검증 및 상태 초기화 노드
    
    역할:
    - 사용자 메시지의 유효성 검증 (빈값, 길이, 부적절한 내용)
    - ChatState의 모든 필드 초기화
    - 검증 실패 시 workflow_status = "validation_failed" 설정
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def create_node(self):
        """메시지 검증 및 상태 초기화 노드 생성"""
        async def message_check_node(state: ChatState) -> ChatState:
            start_time = time.perf_counter()
            
            print("\n [0단계] 메시지 검증 및 상태 초기화 시작...")
            
            # 1. 메시지 검증
            user_question = state.get("user_question", "")
            validation_result = self._validate_message(user_question)
            
            if not validation_result["is_valid"]:
                # 처리 시간 기록 (오류 시에도)
                end_time = time.perf_counter()
                step_time = end_time - start_time
                
                if step_time < 0.001:
                    time_display = f"{step_time * 1000000:.0f}μs"
                elif step_time < 0.01:
                    time_display = f"{step_time * 1000:.1f}ms"
                else:
                    time_display = f"{step_time:.3f}초"
                
                print(f"[0단계] 메시지 검증 실패: {validation_result['error']}")
                print(f"[0단계] 처리 시간: {time_display}")
                
                # 최소한의 상태 초기화 (오류 응답용)
                state.setdefault("processing_log", [])
                state.setdefault("error_messages", [])
                
                # 오류 정보 설정
                state["error_messages"] = [validation_result["error"]]
                state["processing_log"].append(f"0단계 처리 시간 (검증 실패): {time_display}")
                
                # 최종 응답을 오류 메시지로 설정 (워크플로우 중단)
                state["final_response"] = {
                    "error": validation_result["error"],
                    "formatted_content": validation_result["error"],
                    "format_type": "error",
                    "validation_failed": True,
                    "skip_processing": True  # 후속 단계 건너뛰기 플래그
                }
                
                # 워크플로우 중단을 위한 특별 상태 설정
                state["workflow_status"] = "validation_failed"
                
                self.logger.warning(f"메시지 검증 실패로 워크플로우 중단: {validation_result['error']}")
                
                return state
            
            print(f"[0단계] 메시지 검증 성공: {len(user_question)}자")
            
            # 상태 초기화 (MemorySaver 복원 데이터 보존 - current_session_messages 제외)
            # Note: current_session_messages는 MemorySaver에서 복원되므로 초기화하지 않음
            state.setdefault("intent_analysis", {})
            state.setdefault("career_cases", [])
            state.setdefault("education_courses", {})
            state.setdefault("formatted_response", {})
            state.setdefault("mermaid_diagram", "")
            state.setdefault("diagram_generated", False)
            state.setdefault("final_response", {})
            state.setdefault("user_data", {})
            state.setdefault("processing_log", [])
            state.setdefault("error_messages", [])
            state.setdefault("total_processing_time", 0.0)
            
            # 처리 시간 계산
            end_time = time.perf_counter()
            step_time = end_time - start_time
            
            if step_time < 0.001:
                time_display = f"{step_time * 1000000:.0f}μs"
            elif step_time < 0.01:
                time_display = f"{step_time * 1000:.1f}ms"
            else:
                time_display = f"{step_time:.3f}초"
            
            processing_log = state.get("processing_log", [])
            processing_log.append(f"0단계 처리 시간: {time_display}")
            state["processing_log"] = processing_log
            
            print(f"상태 초기화 완료: {len(state.keys())}개 필드")
            print(f"[0단계] 처리 시간: {time_display}")
            
            return state
        
        return message_check_node
    
    def _validate_message(self, user_question: str) -> dict:
        """메시지 유효성 검증"""
        
        # 1. 빈 메시지 검증
        if not user_question or not user_question.strip():
            return {
                "is_valid": False,
                "error": "메시지가 비어있습니다. 질문을 입력해주세요."
            }
        
        # 2. 최소 길이 검증
        if len(user_question.strip()) < 2:
            return {
                "is_valid": False,
                "error": "너무 짧은 메시지입니다. 조금 더 구체적으로 질문해주세요."
            }
        
        # 3. 최대 길이 검증
        if len(user_question) > 1000:
            return {
                "is_valid": False,
                "error": "메시지가 너무 깁니다. 1000자 이내로 질문해주세요."
            }
        
        # 4. 스팸/반복 문자 검증
        if self._is_spam_message(user_question):
            return {
                "is_valid": False,
                "error": "적절하지 않은 메시지입니다. 의미있는 질문을 입력해주세요."
            }
        
        # 5. 욕설/부적절한 내용 검증
        inappropriate_words = [
            # 일반 욕설
            "ㅅㅂ", "ㅂㅅ", "ㅁㅊ", "시발", "씨발", "병신", "개새끼", "새끼", 
            "미친", "미쳤", "또라이", "놈", "창년", "걸레", "쓰레기",
            "개자식", "개놈", "개년", "개뚱", "바카", "멍청이", "등신",
            "바보", "똥", "개똥", "fuck", "shit", "damn", "bitch",
            
            # 성적 표현
            "섹스", "sex", "야동", "porn", "딜도", "자위", "오나니",
            "발정", "변태", "색녀", "색남", "엣치", "야해", "음란",
            
            # 차별적 표현
            "장애인", "정신병자", "장애자", "벙어리", "반신불수", "절름발이",
            "애미", "애비", "지랄", "꺼져", "죽어", "뒤져", "망해",
            
            # 자음 조합 욕설
            "ㅄ", "ㅅㄲ", "ㅆㅂ", "ㅈㄹ", "ㅗㅜㅑ", "ㅁㅊ", "ㅂㅅ"
        ]
        
        # 대소문자 구분 없이 검사
        message_lower = user_question.lower()
        for word in inappropriate_words:
            if word in message_lower:
                return {
                    "is_valid": False,
                    "error": "부적절한 내용이 포함되어 있습니다. 정중한 언어로 질문해주세요."
                }
        
        return {"is_valid": True, "error": None}
    
    def _is_spam_message(self, message: str) -> bool:
        """스팸 메시지 여부 확인"""
        
        # 같은 문자가 연속으로 5번 이상 반복
        for i in range(len(message) - 4):
            if len(set(message[i:i+5])) == 1:
                return True
        
        # 같은 단어가 3번 이상 반복
        words = message.split()
        if len(words) >= 3:
            for word in set(words):
                if words.count(word) >= 3 and len(word) > 1:
                    return True
        
        return False