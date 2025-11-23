import logging
from datetime import datetime
from app.graphs.state import ChatState
from app.graphs.agents.analyzer import IntentAnalysisAgent


class IntentAnalysisNode:
    """
    사용자 의도 분석 및 상황 이해 노드
    
    AgentRAG 워크플로우의 2단계로, 사용자 질문을 분석하여
    다음 단계에 필요한 검색 키워드와 의도 정보를 추출합니다.
    """

    def __init__(self, graph_builder_instance):
        self.graph_builder = graph_builder_instance
        self.intent_analysis_agent = IntentAnalysisAgent()
        self.logger = logging.getLogger(__name__)

    def _map_level_to_experience(self, level: str) -> str:
        """
        CL 레벨을 연차 정보로 매핑한다.
        """
        level_mapping = {
            "CL1": "1~3년",
            "CL2": "4~6년",
            "CL3": "7~9년",
            "CL4": "10~12년",
            "CL5": "13년 이상"
        }
        if level and level.upper() in level_mapping:
            return level_mapping[level.upper()]
        return "정보 없음"

    def analyze_intent_node(self, state: ChatState) -> ChatState:
        """
         2단계: 사용자 의도 분석 및 상황 이해
        
        사용자 질문과 대화 맥락을 분석하여 의도를 파악하고,
        다음 단계의 데이터 검색에 필요한 키워드를 추출합니다.
        
        Args:
            state: 현재 워크플로우 상태
            
        Returns:
            ChatState: 의도 분석 결과가 포함된 상태
        """
        import time
        start_time = time.perf_counter()
        
        try:  # 의도 분석 처리 시작
            # 메시지 검증 실패 시 처리 건너뛰기
            if state.get("workflow_status") == "validation_failed":  # 검증 실패 상태 확인
                print(f"[2단계] 메시지 검증 실패로 처리 건너뛰기")
                return state
                
            print(f"[2단계] 의도 분석 및 상황 이해 시작...")
            self.logger.info("=== 2단계: 의도 분석 및 상황 이해 ===")
            
            # 세션 정보에서 사용자 데이터 가져오기
            user_data = self.graph_builder.get_user_info_from_session(state)  # 사용자 정보 조회 호출
            # level → experience 변환 (user_info_collection과 동일하게)
            if user_data and isinstance(user_data, dict):
                level = user_data.get('level')
                if level and 'experience' not in user_data:
                    user_data['experience'] = self._map_level_to_experience(level)
            
            intent_analysis = self.intent_analysis_agent.analyze_intent_and_context(  # 의도 분석 에이전트 호출
                user_question=state.get("user_question", ""),
                user_data=user_data,
                chat_history=state.get("current_session_messages", [])
            )
            
            state["intent_analysis"] = intent_analysis
            state["processing_log"].append("의도 분석 및 상황 이해 완료")
            
            # 처리 시간 계산 및 로그
            end_time = time.perf_counter()
            step_time = end_time - start_time
            
            if step_time < 0.001:  # 마이크로초 단위인 경우
                time_display = f"{step_time * 1000000:.0f}μs"
            elif step_time < 0.01:  # 밀리초 단위인 경우
                time_display = f"{step_time * 1000:.1f}ms"
            else:  # 초 단위인 경우
                time_display = f"{step_time:.3f}초"
            
            processing_log = state.get("processing_log", [])
            processing_log.append(f"2단계 처리 시간: {time_display}")
            state["processing_log"] = processing_log
            
            # 분석 결과 요약
            intent_type = intent_analysis.get("intent", "일반 상담")  # 의도 타입 추출
            career_keywords = intent_analysis.get("career_history", [])  # 커리어 키워드 추출
            
            print(f"[2단계] 의도 분석 및 상황 이해 완료")
            print(f"분석된 의도: {intent_type}")
            print(f"키워드 추출: {len(career_keywords)}개")
            print(f"[2단계] 처리 시간: {time_display}")
            
            self.logger.info("의도 분석 및 상황 이해 완료")
            
        except Exception as e:  # 예외 처리
            # 오류 발생 시에도 처리 시간 기록
            end_time = time.perf_counter()
            step_time = end_time - start_time
            
            if step_time < 0.001:  # 마이크로초 단위인 경우
                time_display = f"{step_time * 1000000:.0f}μs"
            elif step_time < 0.01:  # 밀리초 단위인 경우
                time_display = f"{step_time * 1000:.1f}ms"
            else:  # 초 단위인 경우
                time_display = f"{step_time:.3f}초"
                
            processing_log = state.get("processing_log", [])
            processing_log.append(f"2단계 처리 시간 (오류): {time_display}")
            state["processing_log"] = processing_log
            
            error_msg = f"의도 분석 실패: {e}"
            self.logger.error(error_msg)
            state["error_messages"].append(error_msg)
            state["intent_analysis"] = {
                "error": str(e),
                "career_history": []
            }
            
            print(f"[2단계] 의도 분석 오류: {time_display} (오류: {e})")
        
        return state