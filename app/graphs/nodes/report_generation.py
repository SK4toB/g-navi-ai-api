# app/graphs/nodes/report_generation.py
# 보고서 생성 노드

import logging
import time
import os
from typing import Dict, Any

from app.graphs.state import ChatState
from app.graphs.agents.report_generator import ReportGeneratorAgent


class ReportGenerationNode:
    """보고서 생성 노드 클래스"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.report_generator = ReportGeneratorAgent()
    
    def generate_report_node(self, state: ChatState) -> ChatState:
        """
        5단계: 보고서 생성 노드
        사용자 요청에 보고서 생성 의도가 있으면 HTML 보고서를 생성
        """
        start_time = time.perf_counter()  # 더 정밀한 시간 측정
        
        try:
            print(f"\n🔧 [5단계] 보고서 생성 분석 시작... (시작시간: {start_time})")
            
            # 기본 정보 추출
            user_question = state.get("user_question", "")
            final_response = state.get("final_response", {})
            user_data = state.get("user_data", {})
            
            self.logger.info(f"보고서 생성 검토: {user_question[:50]}...")
            
            # 보고서 생성 필요성 판단 시간 측정
            analysis_start = time.perf_counter()
            should_generate = self.report_generator.should_generate_report(
                user_question, user_data
            )
            analysis_time = time.perf_counter() - analysis_start
            print(f"🔍 보고서 필요성 판단 시간: {analysis_time * 1000:.1f}ms")
            
            if should_generate:
                print("📊 보고서 생성 필요 → HTML 파일 생성 중...")
                
                # HTML 보고서 생성 시간 측정
                generation_start = time.perf_counter()
                report_path = self.report_generator.generate_html_report(
                    final_response, user_data, state
                )
                generation_time = time.perf_counter() - generation_start
                print(f"📝 HTML 보고서 생성 시간: {generation_time * 1000:.1f}ms")
                
                if report_path:
                    print(f"✅ 보고서 생성 완료: {report_path}")
                    
                    # 상태에 보고서 정보 추가
                    state["report_generated"] = True
                    state["report_path"] = report_path
                    
                    # 최종 응답에 보고서 생성 알림 추가 (하이퍼링크 포함)
                    if isinstance(final_response.get("formatted_content"), str):
                        # 파일명만 추출 (전체 경로에서)
                        report_filename = os.path.basename(report_path)
                        
                        # 마크다운 하이퍼링크 형식으로 추가
                        report_link = f"[📊 {report_filename}](file://{report_path})"
                        final_response["formatted_content"] += f"\n\n📊 **보고서가 생성되었습니다**\n\n{report_link}\n\n> 💡 링크를 클릭하면 생성된 HTML 보고서를 바로 열어볼 수 있습니다."
                        state["final_response"] = final_response
                else:
                    print("❌ 보고서 생성 실패")
                    state["report_generated"] = False
                    state["report_error"] = "보고서 생성 중 오류가 발생했습니다."
            else:
                print("ℹ️  보고서 생성 불필요 → 건너뛰기")
                state["report_generated"] = False
                state["report_skip_reason"] = "사용자 요청에 보고서 생성 의도 없음"
            
            # 5단계 처리 시간 계산 및 로그 추가 (정밀도 향상)
            end_time = time.perf_counter()
            step5_time = end_time - start_time
            processing_log = state.get("processing_log", [])
            
            # 마이크로초 단위까지 표시
            if step5_time < 0.001:  # 1ms 미만인 경우 마이크로초로 표시
                time_display = f"{step5_time * 1000000:.0f}μs"
            elif step5_time < 0.01:  # 10ms 미만인 경우 밀리초로 표시
                time_display = f"{step5_time * 1000:.1f}ms"
            else:
                time_display = f"{step5_time:.3f}초"
            
            processing_log.append(f"5단계 처리 시간: {time_display}")
            state["processing_log"] = processing_log
            
            print(f"⏱️  [5단계] 보고서 생성 처리 완료: {time_display}")
            print(f"📊 상세시간 - 시작: {start_time:.6f}, 종료: {end_time:.6f}, 차이: {step5_time:.6f}초")
            
            return state
            
        except Exception as e:
            self.logger.error(f"보고서 생성 노드 오류: {e}")
            
            # 오류 발생 시에도 처리 시간 기록 (정밀도 향상)
            end_time = time.perf_counter()
            step5_time = end_time - start_time
            processing_log = state.get("processing_log", [])
            
            # 마이크로초 단위까지 표시
            if step5_time < 0.001:  # 1ms 미만인 경우 마이크로초로 표시
                time_display = f"{step5_time * 1000000:.0f}μs"
            elif step5_time < 0.01:  # 10ms 미만인 경우 밀리초로 표시
                time_display = f"{step5_time * 1000:.1f}ms"
            else:
                time_display = f"{step5_time:.3f}초"
                
            processing_log.append(f"5단계 처리 시간 (오류): {time_display}")
            state["processing_log"] = processing_log
            
            print(f"❌ [5단계] 보고서 생성 오류 완료: {time_display} (오류: {e})")
            
            state["report_generated"] = False
            state["report_error"] = str(e)
            return state
