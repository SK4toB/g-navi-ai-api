# app/graphs/nodes/diagram_generation.py
"""
* @className : DiagramGenerationNode
* @description : 다이어그램 생성 노드 모듈
*                Mermaid 다이어그램을 생성하는 워크플로우 노드입니다.
*                시각적 다이어그램으로 정보를 표현합니다.
*
* @modification : 2025.07.01(이재원) 최초생성
*
* @author 이재원
* @Date 2025.07.01
* @version 1.0
* @see MermaidDiagramAgent, ChatState
*  == 개정이력(Modification Information) ==
*  
*   수정일        수정자        수정내용
*   ----------   --------     ---------------------------
*   2025.07.01   이재원       최초 생성
*  
* Copyright (C) by G-Navi AI System All right reserved.
"""

from typing import Dict, Any
import logging
from app.graphs.state import ChatState


class DiagramGenerationNode:
    """
    🎨 Mermaid 다이어그램 생성 및 FE용 응답 통합 노드
    
    AgentRAG 워크플로우의 5단계로, 포맷팅된 응답을 분석하여
    필요시 Mermaid 다이어그램을 생성하고 최종 응답을 통합합니다.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_diagram_node(self, state: ChatState) -> ChatState:
        """
        🎨 5단계: Mermaid 다이어그램 생성 및 FE용 최종 응답 통합
        
        포맷팅된 응답을 분석하여 시각화가 도움이 되는 경우
        Mermaid 다이어그램을 생성하고, FE에서 사용할 최종 응답을 완성합니다.
        
        Args:
            state: ChatState 객체 (포맷팅된 응답 포함)
            
        Returns:
            ChatState: 다이어그램과 최종 응답이 통합된 상태
        """
        import time
        start_time = time.perf_counter()
        
        try:
            # 메시지 검증 실패 시 처리 건너뛰기
            if state.get("workflow_status") == "validation_failed":
                print(f"⚠️  [5단계] 메시지 검증 실패로 처리 건너뛰기")
                return state
                
            print(f"\n🎨 [5단계] 다이어그램 생성 및 통합 시작...")
            
            # 필요한 데이터 추출
            formatted_response = state.get("formatted_response", {})
            formatted_content = ""
            
            # formatted_response에서 내용 추출
            if isinstance(formatted_response, dict):
                formatted_content = formatted_response.get("formatted_content", "")
            elif isinstance(formatted_response, str):
                formatted_content = formatted_response
            
            user_question = state.get("user_question", "")
            intent_analysis = state.get("intent_analysis", {})
            user_data = state.get("user_data", {})
            
            # 포맷된 콘텐츠가 없으면 다이어그램 생성 건너뛰기
            if not formatted_content or not formatted_content.strip():
                print("⚠️ [다이어그램 생성] 포맷된 콘텐츠가 없어 생성 건너뛰기")
                state["mermaid_diagram"] = ""
                state["diagram_generated"] = False
                # 다이어그램 없이 원본 응답을 FE용 최종 응답으로 설정
                state["final_response"] = formatted_response
                print("ℹ️ [다이어그램 생성] 원본 응답을 FE용 최종 응답으로 설정")
                
                # 처리 시간 기록
                end_time = time.perf_counter()
                step_time = end_time - start_time
                
                if step_time < 0.001:
                    time_display = f"{step_time * 1000000:.0f}μs"
                elif step_time < 0.01:
                    time_display = f"{step_time * 1000:.1f}ms"
                else:
                    time_display = f"{step_time:.3f}초"
                
                processing_log = state.get("processing_log", [])
                processing_log.append(f"5단계 처리 시간: {time_display}")
                state["processing_log"] = processing_log
                
                print(f"⏱️  [5단계] 다이어그램 없음 처리 완료: {time_display}")
                return state
            
            # 다이어그램 생성이 의미있는지 판단
            if not self._should_generate_diagram(formatted_content, user_question):
                print("⚠️ [다이어그램 생성] 생성 필요하지 않은 내용으로 판단")
                state["mermaid_diagram"] = ""
                state["diagram_generated"] = False
                # 다이어그램 없이 원본 응답을 FE용 최종 응답으로 설정
                state["final_response"] = formatted_response
                print("ℹ️ [다이어그램 생성] 원본 응답을 FE용 최종 응답으로 설정")
                
                # 처리 시간 기록
                end_time = time.perf_counter()
                step_time = end_time - start_time
                
                if step_time < 0.001:
                    time_display = f"{step_time * 1000000:.0f}μs"
                elif step_time < 0.01:
                    time_display = f"{step_time * 1000:.1f}ms"
                else:
                    time_display = f"{step_time:.3f}초"
                
                processing_log = state.get("processing_log", [])
                processing_log.append(f"5단계 처리 시간: {time_display}")
                state["processing_log"] = processing_log
                
                print(f"⏱️  [5단계] 다이어그램 생성 불필요 처리 완료: {time_display}")
                return state
            
            # Mermaid 에이전트 import (순환 import 방지를 위해 지연 import)
            from app.graphs.agents.mermaid_agent import MermaidDiagramAgent
            
            # 다이어그램 생성
            print("🎯 [다이어그램 생성] Mermaid 다이어그램 생성 중...")
            mermaid_agent = MermaidDiagramAgent()
            mermaid_code = mermaid_agent.generate_diagram(
                formatted_content=formatted_content,
                user_question=user_question,
                intent_analysis=intent_analysis,
                user_data=user_data
            )
            
            # 상태 업데이트
            state["mermaid_diagram"] = mermaid_code
            state["diagram_generated"] = bool(mermaid_code and mermaid_code.strip())
            
            # 다이어그램 생성 여부와 관계없이 FE용 최종 응답 생성
            print("🔧 [다이어그램 생성] FE용 최종 응답 통합 중...")
            final_response = self._integrate_diagram_to_response(
                formatted_response, mermaid_code, state["diagram_generated"]
            )
            state["final_response"] = final_response
            
            # 처리 시간 계산 및 로그
            end_time = time.perf_counter()
            step_time = end_time - start_time
            
            if step_time < 0.001:
                time_display = f"{step_time * 1000000:.0f}μs"
            elif step_time < 0.01:
                time_display = f"{step_time * 1000:.1f}ms"
            else:
                time_display = f"{step_time:.3f}초"
            
            processing_log = state.get("processing_log", [])
            processing_log.append(f"5단계 처리 시간: {time_display}")
            state["processing_log"] = processing_log
            
            # 💫 MessageProcessor를 위한 bot_message 설정 (5단계에서 최종 설정)
            final_response = state.get("final_response", {})
            if isinstance(final_response, dict) and final_response.get("formatted_content"):
                state["bot_message"] = final_response["formatted_content"]
                print("📨 [5단계] bot_message 설정 완료 (사용자 응답 준비)")
            else:
                # 폴백: 기본 메시지
                state["bot_message"] = "응답 처리가 완료되었습니다."
                print("⚠️  [5단계] bot_message 폴백 설정")
            
            if state["diagram_generated"]:
                print(f"✅ [5단계] 다이어그램 생성 및 통합 완료")
                print(f"📊 다이어그램 길이: {len(mermaid_code)}자")
                print(f"🔧 FE 응답 통합: 완료")
                print(f"⏱️  [5단계] 처리 시간: {time_display}")
                self.logger.info("Mermaid 다이어그램 생성 및 FE용 최종 응답 통합 성공")
            else:
                print(f"✅ [5단계] 다이어그램 없는 응답 완료")
                print(f"🔧 FE 응답 통합: 원본 사용")
                print(f"⏱️  [5단계] 처리 시간: {time_display}")
                self.logger.info("다이어그램 없는 FE용 최종 응답 생성 완료")
                
            return state
            
        except Exception as e:
            # 오류 발생 시에도 처리 시간 기록
            end_time = time.perf_counter()
            step_time = end_time - start_time
            
            if step_time < 0.001:
                time_display = f"{step_time * 1000000:.0f}μs"
            elif step_time < 0.01:
                time_display = f"{step_time * 1000:.1f}ms"
            else:
                time_display = f"{step_time:.3f}초"
                
            processing_log = state.get("processing_log", [])
            processing_log.append(f"5단계 처리 시간 (오류): {time_display}")
            state["processing_log"] = processing_log
            
            self.logger.error(f"다이어그램 생성 노드 오류: {e}")
            print(f"❌ [5단계] 다이어그램 생성 오류: {time_display} (오류: {e})")
            
            # 오류 시 빈 다이어그램으로 설정하지만 FE용 최종 응답은 생성
            state["mermaid_diagram"] = ""
            state["diagram_generated"] = False
            
            # 다이어그램 없이 원본 응답을 최종 응답으로 설정
            formatted_response = state.get("formatted_response", {})
            state["final_response"] = formatted_response
            
            # 💫 오류 시에도 bot_message 설정 (5단계에서 최종 설정)
            if isinstance(formatted_response, dict) and formatted_response.get("formatted_content"):
                state["bot_message"] = formatted_response["formatted_content"]
                print("📨 [5단계] 오류 시 bot_message 설정 완료")
            else:
                # 완전 폴백: 오류 메시지
                state["bot_message"] = f"죄송합니다. 다이어그램 생성 중 오류가 발생했지만 응답은 준비되었습니다."
                print("⚠️  [5단계] 오류 시 bot_message 완전 폴백 설정")
            
            print("⚠️ [다이어그램 생성] 오류로 인해 다이어그램 없는 응답 사용")
            
            return state
    
    def _should_generate_diagram(self, content: str, question: str = "") -> bool:
        """
        🔍 다이어그램 생성 필요성 지능형 판단
        
        콘텐츠와 질문을 분석하여 시각화가 도움이 될지 판단합니다.
        단순한 인사나 짧은 답변은 제외하고, 구조화된 정보나
        프로세스를 포함한 내용만 다이어그램으로 생성합니다.
        
        Args:
            content: 포맷팅된 응답 내용
            question: 사용자 질문
            
        Returns:
            bool: 다이어그램 생성 필요 여부
        """
        
        try:
            # 내용이 너무 짧으면 다이어그램 불필요
            if len(content.strip()) < 100:
                return False
            
            # 단순 인사나 간단한 질문은 다이어그램 불필요
            simple_patterns = [
                "안녕", "감사", "고마워", "잘 부탁", "처음 뵙겠습니다",
                "이름이 뭐", "누구", "어디", "언제"
            ]
            
            if any(pattern in question.lower() for pattern in simple_patterns):
                return False
            
            # 다이어그램이 유용한 키워드들
            useful_patterns = [
                "단계", "과정", "절차", "방법", "로드맵", "경로", "계획",
                "구조", "관계", "흐름", "순서", "시퀀스", "프로세스",
                "역량", "스킬", "기술", "학습", "성장", "발전", "전환",
                "조직", "팀", "협업", "소통", "커뮤니케이션"
            ]
            
            content_lower = content.lower()
            question_lower = question.lower()
            
            # 내용이나 질문에 유용한 키워드가 있으면 다이어그램 생성
            if any(pattern in content_lower or pattern in question_lower 
                   for pattern in useful_patterns):
                return True
            
            # 목록이나 단계별 설명이 있으면 다이어그램 유용
            if ("1." in content and "2." in content) or ("첫째" in content and "둘째" in content):
                return True
            
            # 기본적으로 어느 정도 길이가 있는 내용은 다이어그램 생성
            return len(content.strip()) > 300
            
        except Exception as e:
            self.logger.warning(f"다이어그램 생성 필요성 판단 오류: {e}")
            # 오류 시 기본적으로 생성 시도
            return True
    
    def _integrate_diagram_to_response(self, 
                                     formatted_response: Dict[str, Any],
                                     mermaid_diagram: str,
                                     diagram_generated: bool) -> Dict[str, Any]:
        """
        포맷된 응답에 Mermaid 다이어그램을 통합하여 FE용 최종 응답 생성
        
        **핵심 기능:**
        - 생성된 다이어그램을 마크다운 응답에 자동 통합
        - FE에게 전달할 완성된 최종 응답 생성
        
        Args:
            formatted_response: 포맷터에서 생성된 응답
            mermaid_diagram: 생성된 Mermaid 다이어그램 코드
            diagram_generated: 다이어그램 생성 성공 여부
            
        Returns:
            Dict[str, Any]: 다이어그램이 통합된 FE용 최종 응답
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
            
            print(f"✅ FE용 최종 응답에 다이어그램 통합 완료 ({len(mermaid_diagram)}자)")
            self.logger.info("Mermaid 다이어그램이 FE용 최종 응답에 통합됨")
            
            return final_response
            
        except Exception as e:
            self.logger.warning(f"다이어그램 통합 실패: {e}")
            print(f"⚠️ 다이어그램 통합 실패: {e}")
            # 실패 시 원본 응답 반환
            return formatted_response if formatted_response else {}