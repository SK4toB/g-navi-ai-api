# app/graphs/nodes/report_generation.py
"""
* @className : ReportGenerationNode
* @description : 보고서 생성 노드 모듈
*                관리자용 보고서를 생성하는 워크플로우 노드입니다.
*                상담 내용과 AI 응답을 종합한 리포트를 작성합니다.
*
"""

import logging
import time
import os
from typing import Dict, Any

from app.graphs.state import ChatState
from app.graphs.agents.report_generator import ReportGeneratorAgent


class ReportGenerationNode:
    """
    관리자 전용 HTML 보고서 생성 노드
    
    **핵심 역할:**
    - HTML 보고서 파일 생성 및 저장 (관리자용)
    - 사용자 응답과 완전히 분리된 별도 기능
    - 보고서 생성 여부를 관리자가 제어 가능
    
    **중요:** 
    - 이 노드는 순수하게 관리자용 HTML 보고서 생성만 담당
    - 사용자 응답(bot_message)은 이전 단계에서 이미 완성됨
    - 보고서 생성 실패해도 사용자 응답에 영향 없음
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.report_generator = ReportGeneratorAgent()
    
    def generate_report_node(self, state: ChatState) -> ChatState:
        """
        6단계: 관리자 전용 HTML 보고서 생성
        
        상담 내용을 체계적으로 정리한 HTML 보고서를 생성하여
        관리자가 상담 품질을 검토할 수 있도록 지원합니다.
        
        **기능:**
        - HTML 보고서 파일 생성 및 저장 (관리자 설정에 따라 실행)
        - 사용자 응답과 완전히 분리된 백그라운드 작업
        
        **중요:**
        - 사용자 응답(bot_message)은 5단계에서 이미 완성됨
        - 이 노드는 순수하게 관리자용 HTML 보고서 생성만 담당
        - 보고서 생성 실패해도 사용자 경험에 영향 없음
        
        Args:
            state: 현재 워크플로우 상태 (최종 응답 포함)
            
        Returns:
            ChatState: 보고서 생성 결과가 포함된 상태
        """
        start_time = time.perf_counter()  # 더 정밀한 시간 측정
        
        try:
            # 메시지 검증 실패 시 처리 건너뛰기
            if state.get("workflow_status") == "validation_failed":
                print(f"[6단계] 메시지 검증 실패로 처리 건너뛰기")
                return state
                
            print(f"\n[6단계] HTML 보고서 생성 시작... (시작시간: {start_time})")
            
            # 기본 정보 추출
            user_question = state.get("user_question", "")
            final_response = state.get("final_response", {})
            user_data = state.get("user_data", {})
            
            self.logger.info(f"HTML 보고서 생성 검토: {user_question[:50]}...")
            
            # 6단계에서 보고서 생성 여부 판단 (관리자 기능)
            analysis_start = time.perf_counter()
            should_generate = self.report_generator.should_generate_report(
                user_question, user_data
            )
            analysis_time = time.perf_counter() - analysis_start
            print(f"[관리자 기능] 보고서 필요성 판단 시간: {analysis_time * 1000:.1f}ms")
            
            if should_generate:
                print("[관리자 기능] 보고서 생성 필요 → HTML 파일 생성 중...")
                
                # HTML 보고서 생성 시간 측정
                generation_start = time.perf_counter()
                report_path = self.report_generator.generate_html_report(
                    final_response, user_data, state
                )
                generation_time = time.perf_counter() - generation_start
                print(f"[관리자 기능] HTML 보고서 생성 시간: {generation_time * 1000:.1f}ms")
                
                if report_path:
                    print(f"[관리자 기능] 보고서 생성 완료: {report_path}")
                    
                    # 상태에 보고서 정보 추가
                    state["report_generated"] = True
                    state["report_path"] = report_path
                    
                    # FE용 최종 응답은 수정하지 않음 (이미 완성된 상태)
                    # 보고서 정보는 별도 필드로만 제공
                    print("FE용 최종 응답은 이미 완성됨 → 보고서 정보만 추가")
                else:
                    print("[관리자 기능] 보고서 생성 실패")
                    state["report_generated"] = False
                    state["report_error"] = "보고서 생성 중 오류가 발생했습니다."
            else:
                print("[관리자 기능] 보고서 생성 불필요 → 건너뛰기")
                state["report_generated"] = False
                state["report_skip_reason"] = "사용자 요청에 보고서 생성 의도 없음"
            
            
            # 6단계 처리 시간 계산 및 로그 추가
            end_time = time.perf_counter()
            step_time = end_time - start_time
            processing_log = state.get("processing_log", [])
            
            # 시간 단위 결정 (다른 노드들과 일치)
            if step_time < 0.001:  # 1ms 미만
                time_display = f"{step_time * 1000000:.0f}μs"
            elif step_time < 0.01:  # 10ms 미만
                time_display = f"{step_time * 1000:.1f}ms"
            else:
                time_display = f"{step_time:.3f}초"
            
            processing_log.append(f"6단계 처리 시간: {time_display}")
            state["processing_log"] = processing_log
            
            print(f"[6단계] 관리자용 HTML 보고서 처리 완료: {time_display}")
            self.logger.info(f"6단계 관리자용 HTML 보고서 완료: {time_display}")
            print("[관리자 모드] 보고서 생성은 관리자 전용 기능입니다")
            
            return state
            
        except Exception as e:
            self.logger.error(f"보고서 생성 노드 오류: {e}")
            
            # 오류 발생 시에도 처리 시간 기록 (정밀도 향상)
            end_time = time.perf_counter()
            step_time = end_time - start_time
            processing_log = state.get("processing_log", [])
            
            # 시간 단위 결정 (다른 노드들과 일치)
            if step_time < 0.001:  # 1ms 미만
                time_display = f"{step_time * 1000000:.0f}μs"
            elif step_time < 0.01:  # 10ms 미만
                time_display = f"{step_time * 1000:.1f}ms"
            else:
                time_display = f"{step_time:.3f}초"
                
            processing_log.append(f"6단계 처리 시간 (오류): {time_display}")
            state["processing_log"] = processing_log
            
            print(f"[6단계] 관리자용 HTML 보고서 오류: {time_display} (오류: {e})")
            print("[관리자 모드] 보고서 오류는 사용자 응답에 영향 없음")
            
            state["report_generated"] = False
            state["report_error"] = str(e)
            return state