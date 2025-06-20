# app/graphs/nodes/diagram_generation.py
# Mermaid 다이어그램 생성 노드

from typing import Dict, Any
import logging
from app.graphs.state import ChatState


class DiagramGenerationNode:
    """
    Mermaid 다이어그램 생성 노드
    - formatter에서 생성된 응답을 기반으로 다이어그램 생성
    - 생성된 다이어그램을 state에 저장
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_diagram_node(self, state: ChatState) -> ChatState:
        """
        포맷된 응답을 기반으로 Mermaid 다이어그램 생성
        
        Args:
            state: ChatState 객체
            
        Returns:
            ChatState: 다이어그램 정보가 추가된 state
        """
        
        try:
            print("🎨 [Diagram Generation] 다이어그램 생성 노드 시작")
            
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
                print("⚠️ [Diagram Generation] 포맷된 콘텐츠가 없어 다이어그램 생성 건너뛰기")
                state["mermaid_diagram"] = ""
                state["diagram_generated"] = False
                return state
            
            # 다이어그램 생성이 의미있는지 판단
            if not self._should_generate_diagram(formatted_content, user_question):
                print("⚠️ [Diagram Generation] 다이어그램 생성이 필요하지 않은 내용으로 판단")
                state["mermaid_diagram"] = ""
                state["diagram_generated"] = False
                return state
            
            # Mermaid 에이전트 import (순환 import 방지를 위해 지연 import)
            from app.graphs.agents.mermaid_agent import MermaidDiagramAgent
            
            # 다이어그램 생성
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
            
            if state["diagram_generated"]:
                print(f"✅ [Diagram Generation] 다이어그램 생성 완료 ({len(mermaid_code)}자)")
                self.logger.info("Mermaid 다이어그램 생성 성공")
            else:
                print("❌ [Diagram Generation] 다이어그램 생성 실패")
                self.logger.warning("Mermaid 다이어그램 생성 실패")
                
            return state
            
        except Exception as e:
            self.logger.error(f"다이어그램 생성 노드 오류: {e}")
            print(f"❌ [Diagram Generation] 오류 발생: {e}")
            
            # 오류 시 빈 다이어그램으로 설정하고 계속 진행
            state["mermaid_diagram"] = ""
            state["diagram_generated"] = False
            return state
    
    def _should_generate_diagram(self, content: str, question: str = "") -> bool:
        """
        다이어그램 생성이 유용한지 판단
        
        Args:
            content: 포맷된 내용
            question: 사용자 질문
            
        Returns:
            bool: 다이어그램 생성 여부
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
