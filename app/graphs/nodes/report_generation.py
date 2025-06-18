# app/graphs/nodes/report_generation.py
# 보고서 생성 노드

import logging
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
        try:
            print("\n🔧 [5단계] 보고서 생성 분석 시작...")
            
            # 기본 정보 추출
            user_question = state.get("user_question", "")
            final_response = state.get("final_response", {})
            user_data = state.get("user_data", {})
            
            self.logger.info(f"보고서 생성 검토: {user_question[:50]}...")
            
            # 보고서 생성 필요성 판단
            should_generate = self.report_generator.should_generate_report(
                user_question, user_data
            )
            
            if should_generate:
                print("📊 보고서 생성 필요 → HTML 파일 생성 중...")
                
                # HTML 보고서 생성
                report_path = self.report_generator.generate_html_report(
                    final_response, user_data, state
                )
                
                if report_path:
                    print(f"✅ 보고서 생성 완료: {report_path}")
                    
                    # 상태에 보고서 정보 추가
                    state["report_generated"] = True
                    state["report_path"] = report_path
                    
                    # 최종 응답에 보고서 생성 알림 추가
                    if isinstance(final_response.get("formatted_content"), str):
                        final_response["formatted_content"] += f"\n\n📊 **보고서가 생성되었습니다**\n파일 경로: `{report_path}`"
                        state["final_response"] = final_response
                else:
                    print("❌ 보고서 생성 실패")
                    state["report_generated"] = False
                    state["report_error"] = "보고서 생성 중 오류가 발생했습니다."
            else:
                print("ℹ️  보고서 생성 불필요 → 건너뛰기")
                state["report_generated"] = False
                state["report_skip_reason"] = "사용자 요청에 보고서 생성 의도 없음"
            
            return state
            
        except Exception as e:
            self.logger.error(f"보고서 생성 노드 오류: {e}")
            state["report_generated"] = False
            state["report_error"] = str(e)
            return state
