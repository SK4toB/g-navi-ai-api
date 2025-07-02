# app/graphs/nodes/career_consultation/path_selection.py
"""
커리어 경로 선택 처리 노드
사용자가 선택한 경로에 대한 심화 논의를 진행
"""

from typing import Dict, Any
from app.graphs.state import ChatState


class PathSelectionNode:
    """
    경로 선택 및 구체화 노드
    """
    
    def __init__(self, graph_builder):
        self.graph_builder = graph_builder
    
    async def process_path_selection_node(self, state: ChatState) -> Dict[str, Any]:
        """
        사용자가 선택한 경로를 처리하고 심화 질문을 진행한다.
        """
        print("🛤️ 경로 선택 처리 시작...")
        
        user_question = state.get("user_question", "").upper().strip()
        career_paths = state.get("career_paths_suggested", [])
        
        # 사용자 선택 파싱 (A, B, C 또는 텍스트에서 추출)
        selected_path = None
        for path in career_paths:
            if path["id"] in user_question or path["name"] in user_question:
                selected_path = path
                break
        
        if not selected_path:
            # 기본값 처리 (첫 번째 경로)
            selected_path = career_paths[0] if career_paths else {}
        
        user_data = self.graph_builder.get_user_info_from_session(state)
        
        # 선택한 경로에 대한 전문적인 심화 분석 질문 생성
        deepening_response = {
            "message": f"""✅ **{selected_path.get('name', '선택하신 경로')} 경로 선택 확인**

{user_data.get('name', '고객')}님께서 **{selected_path.get('name', '')}** 경로를 선택해주셨습니다. 
이제 더 구체적이고 실행 가능한 계획을 수립하기 위해 몇 가지 핵심 질문을 드리겠습니다.

**🎯 목표 구체화를 위한 체크포인트**

**1. 선택 동기 및 배경**
   - 이 경로를 선택한 **핵심 이유**는 무엇인가요?
   - 현재 업무에서 이미 **관련 경험이나 성과**가 있나요?
   - **개인적 강점**과 이 경로의 연관성을 어떻게 보시나요?

**2. 구체적 목표 설정 (SMART 목표)**
   - **시간 프레임**: 언제까지 달성하고 싶으신가요? (6개월/1년/2년)
   - **구체적 포지션**: 어떤 직급이나 역할을 목표로 하시나요?
   - **측정 가능한 성과**: 어떤 기준으로 성공을 판단하시겠어요?

**3. 현실성 검토**
   - 현재 조직에서 이 경로로 성장할 **기회**가 있나요?
   - 예상되는 **장애요소나 어려움**은 무엇인가요?
   - **추가로 필요한 역량**은 무엇이라고 생각하시나요?

**답변 예시**: "데이터 분석 역량을 키워 1년 내 데이터 사이언티스트로 전환하고 싶습니다. 현재 업무에서 간단한 분석은 하고 있지만, 머신러닝 지식이 부족해서 체계적으로 학습하고 싶어요."

**상세하게 답변해주시면, 더 정확한 로드맵을 제시해드릴 수 있습니다.**""",
            "selected_path": selected_path
        }
        
        return {
            **state,
            "consultation_stage": "deepening",
            "selected_career_path": selected_path,
            "formatted_response": deepening_response,
            "awaiting_user_input": True,
            "next_expected_input": "goals_and_reasons",
            "processing_log": state.get("processing_log", []) + [f"경로 선택 완료: {selected_path.get('name', '')}"]
        }
