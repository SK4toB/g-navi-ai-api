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
        6단계: 보고서 생성 노드 (다이어그램 통합 포함)
        - Mermaid 다이어그램을 최종 응답에 통합
        - 사용자 요청에 보고서 생성 의도가 있으면 HTML 보고서 생성
        """
        start_time = time.perf_counter()  # 더 정밀한 시간 측정
        
        try:
            print(f"\n🔧 [6단계] 최종 보고서 생성 시작... (시작시간: {start_time})")
            
            # 기본 정보 추출
            user_question = state.get("user_question", "")
            formatted_response = state.get("formatted_response", {})
            mermaid_diagram = state.get("mermaid_diagram", "")
            diagram_generated = state.get("diagram_generated", False)
            user_data = state.get("user_data", {})
            
            # 1. 다이어그램을 최종 응답에 통합
            final_response = self._integrate_diagram_to_response(
                formatted_response, mermaid_diagram, diagram_generated
            )
            
            self.logger.info(f"보고서 생성 검토: {user_question[:50]}...")
            
            # 2. 보고서 생성 필요성 판단 시간 측정
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
                else:
                    print("❌ 보고서 생성 실패")
                    state["report_generated"] = False
                    state["report_error"] = "보고서 생성 중 오류가 발생했습니다."
            else:
                print("ℹ️  보고서 생성 불필요 → 건너뛰기")
                state["report_generated"] = False
                state["report_skip_reason"] = "사용자 요청에 보고서 생성 의도 없음"
            
            # 최종 응답 저장
            state["final_response"] = final_response
            
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
        
    def _integrate_diagram_to_response(self, 
                                     formatted_response: Dict[str, Any],
                                     mermaid_diagram: str,
                                     diagram_generated: bool) -> Dict[str, Any]:
        """
        포맷된 응답에 Mermaid 다이어그램을 통합
        
        Args:
            formatted_response: 포맷터에서 생성된 응답
            mermaid_diagram: 생성된 Mermaid 다이어그램 코드
            diagram_generated: 다이어그램 생성 성공 여부
            
        Returns:
            Dict[str, Any]: 다이어그램이 통합된 최종 응답
        """
        
        try:
            # 응답 복사
            final_response = formatted_response.copy() if formatted_response else {}
            
            # 다이어그램이 생성되지 않았으면 원본 응답 반환
            if not diagram_generated or not mermaid_diagram or not mermaid_diagram.strip():
                print("ℹ️  다이어그램 없음 → 원본 응답 사용")
                return final_response
            
            # 포맷된 콘텐츠 추출
            formatted_content = final_response.get("formatted_content", "")
            if not formatted_content:
                print("⚠️ 포맷된 콘텐츠가 없어 다이어그램 통합 불가")
                return final_response
            
            # 다이어그램 섹션 생성
            diagram_section = f"""

---

```mermaid
{mermaid_diagram.strip()}
```

*위 다이어그램은 설명 내용을 구조적으로 시각화한 것입니다.*

---
"""
            
            # 마무리 부분(G.Navi 멘트 등) 찾아서 그 앞에 다이어그램 삽입
            lines = formatted_content.split('\n')
            insert_index = len(lines)
            
            # 역순으로 검색하여 마무리 부분 찾기
            for i in range(len(lines) - 1, -1, -1):
                line = lines[i].strip()
                if (line.startswith('*G.Navi') or line.startswith('---') or 
                    '응원합니다' in line or '궁금한' in line):
                    insert_index = i
                    break
            
            # 다이어그램 삽입
            if insert_index < len(lines):
                lines.insert(insert_index, diagram_section)
            else:
                lines.append(diagram_section)
            
            # 통합된 콘텐츠 저장
            final_response["formatted_content"] = '\n'.join(lines)
            final_response["has_diagram"] = True
            final_response["diagram_type"] = "mermaid"
            
            print(f"✅ 다이어그램 통합 완료 ({len(mermaid_diagram)}자)")
            self.logger.info("Mermaid 다이어그램이 최종 응답에 통합됨")
            
            return final_response
            
        except Exception as e:
            self.logger.warning(f"다이어그램 통합 실패: {e}")
            print(f"⚠️ 다이어그램 통합 실패: {e}")
            # 실패 시 원본 응답 반환
            return formatted_response if formatted_response else {}
