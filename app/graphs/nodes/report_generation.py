# app/graphs/nodes/report_generation.py
# 보고서 생성 노드

import logging
import time
import os
from typing import Dict, Any

from app.graphs.state import ChatState
from app.graphs.agents.report_generator import ReportGeneratorAgent


class ReportGenerationNode:
    """
    보고서 생성 노드 클래스 (관리자 전용 기능)
    
    **관리자 전용 기능:**
    - HTML 보고서 파일 생성 및 저장
    - 보고서 생성 여부를 관리자가 설정 가능
    
    **주의:** 
    - 이 노드는 순수하게 HTML 보고서 생성만 담당
    - FE용 최종 답변은 이미 이전 단계(다이어그램 생성)에서 완성됨
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.report_generator = ReportGeneratorAgent()
    
    def generate_report_node(self, state: ChatState) -> ChatState:
        """
        6단계: HTML 보고서 생성 노드 (관리자 전용 기능)
        
        **기능:**
        - HTML 보고서 파일 생성 및 저장 (관리자 설정에 따라 실행)
        
        **중요:**
        - FE용 최종 답변(final_response)은 이미 이전 단계에서 완성됨
        - 이 노드는 순수하게 관리자용 HTML 보고서 생성만 담당
        
        **관리자 설정:**
        - 보고서 생성 on/off 제어 가능
        - 특정 키워드 감지 시 자동 생성 또는 완전 비활성화
        """
        start_time = time.perf_counter()  # 더 정밀한 시간 측정
        
        try:
            # 메시지 검증 실패 시 처리 건너뛰기
            if state.get("workflow_status") == "validation_failed":
                print(f"⚠️  [6단계] 메시지 검증 실패로 처리 건너뛰기")
                return state
                
            print(f"\n🔧 [6단계] HTML 보고서 생성 시작... (시작시간: {start_time})")
            
            # 기본 정보 추출
            user_question = state.get("user_question", "")
            final_response = state.get("final_response", {})  # 이미 완성된 FE용 최종 답변
            user_data = state.get("user_data", {})
            
            self.logger.info(f"HTML 보고서 생성 검토: {user_question[:50]}...")
            
            # 6단계에서 보고서 생성 여부 판단 (관리자 기능)
            analysis_start = time.perf_counter()
            should_generate = self.report_generator.should_generate_report(
                user_question, user_data
            )
            analysis_time = time.perf_counter() - analysis_start
            print(f"🔍 [관리자 기능] 보고서 필요성 판단 시간: {analysis_time * 1000:.1f}ms")
            
            if should_generate:
                print("📊 [관리자 기능] 보고서 생성 필요 → HTML 파일 생성 중...")
                
                # HTML 보고서 생성 시간 측정
                generation_start = time.perf_counter()
                report_path = self.report_generator.generate_html_report(
                    final_response, user_data, state
                )
                generation_time = time.perf_counter() - generation_start
                print(f"📝 [관리자 기능] HTML 보고서 생성 시간: {generation_time * 1000:.1f}ms")
                
                if report_path:
                    print(f"✅ [관리자 기능] 보고서 생성 완료: {report_path}")
                    
                    # 상태에 보고서 정보 추가
                    state["report_generated"] = True
                    state["report_path"] = report_path
                    
                    # FE용 최종 응답은 수정하지 않음 (이미 완성된 상태)
                    # 보고서 정보는 별도 필드로만 제공
                    print("ℹ️  FE용 최종 응답은 이미 완성됨 → 보고서 정보만 추가")
                else:
                    print("❌ [관리자 기능] 보고서 생성 실패")
                    state["report_generated"] = False
                    state["report_error"] = "보고서 생성 중 오류가 발생했습니다."
            else:
                print("ℹ️  [관리자 기능] 보고서 생성 불필요 → 건너뛰기")
                state["report_generated"] = False
                state["report_skip_reason"] = "사용자 요청에 보고서 생성 의도 없음"
            
            # 최종 응답은 수정하지 않음 (이미 이전 단계에서 완성됨)
            # state["final_response"] = final_response  # 제거됨
            
            # 6단계 처리 시간 계산 및 로그 추가 (정밀도 향상)
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
            
            print(f"⏱️  [6단계] HTML 보고서 생성 처리 완료: {time_display}")
            self.logger.info(f"6단계 HTML 보고서 생성 완료: {time_display}")
            
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
            
            print(f"❌ [6단계] HTML 보고서 생성 오류 완료: {time_display} (오류: {e})")
            
            state["report_generated"] = False
            state["report_error"] = str(e)
            return state
