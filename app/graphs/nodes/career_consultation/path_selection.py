# app/graphs/nodes/career_consultation/path_selection.py
"""
커리어 경로 선택 처리 노드
사용자가 선택한 경로에 대한 심화 논의를 진행
AI 기반 개인 맞춤형 질문 생성 포함
"""

import os
from typing import Dict, Any
from app.graphs.state import ChatState
from app.utils.html_logger import save_career_response_to_html


class PathSelectionNode:
    """
    경로 선택 및 구체화 노드
    """
    
    def __init__(self, graph_builder):
        self.graph_builder = graph_builder
    
    async def _generate_path_selection_response(self, merged_user_data: dict, selected_path: dict) -> str:
        """선택한 경로에 대한 AI 기반 간결한 확인 및 목표 설정 질문 생성"""
        try:
            from openai import AsyncOpenAI
            
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return "경로 선택을 확인했습니다. 구체적인 목표를 설정해보겠습니다."
            
            client = AsyncOpenAI(api_key=api_key)
            
            skills_str = ", ".join(merged_user_data.get('skills', ['정보 없음']))
            path_name = selected_path.get('name', '선택된 경로')
            
            prompt = f"""
당신은 G.Navi의 전문 커리어 상담사입니다. 현재 상담이 진행 중이며, {merged_user_data.get('name', '고객')}님이 "{path_name}" 경로를 선택했습니다.

**고객 정보:**
- 이름: {merged_user_data.get('name', '고객')}
- 경력: {merged_user_data.get('experience', '정보 없음')}
- 보유 기술: {skills_str}
- 도메인: {merged_user_data.get('domain', '정보 없음')}
- 선택한 경로: {path_name}

**요청사항:**
1. 경로 선택에 대한 간단한 확인 및 격려
2. 다음 단계 맞춤형 분석을 위한 핵심 질문 3개 (각 카테고리당 1개씩만)

**응답 형식 (반드시 마크다운 문법을 사용하여 작성해주세요):**

## 경로 선택 확인

**{merged_user_data.get('name', '고객')}님**이 선택하신 **{path_name}** 경로는 훌륭한 선택입니다! 
더 구체적이고 실무적인 액션 플랜을 수립하기 위해 3가지 핵심 질문을 준비했습니다

### 맞춤형 전략 수립을 위한 질문

** 참고사항**
아래 질문들에 답변해 주시면 더욱 정확한 맞춤형 전략을 제안드릴 수 있지만, **답변하지 않으셔도 됩니다**. 현재까지 수집된 고객님의 정보(경력, 기술스택, 도메인)와 사내 데이터를 기반으로도 충분히 실무적인 성공 전략을 제안드릴 수 있습니다!


**1. 선택 이유**
- 이 경로를 선택하신 가장 중요한 이유 한 가지는 무엇인가요?

**2. 구체적 목표**  
- 이 경로를 통해 1년 후 달성하고 싶은 구체적인 목표는 무엇인가요?

**3. 현재 상황**
- 현재 이 목표 달성에 가장 큰 걸림돌이나 고민은 무엇인가요?

---

**다음 스텝: 맞춤형 성장 로드맵**

위 질문들에 대한 답변을 바탕으로 더욱 구체적이고 실무적인 성장 로드맵을 함께 설계해보시겠어요? 개인 맞춤형 학습 계획과 실행 전략을 제안드릴 수 있습니다!

**작성 지침:**
- 반드시 마크다운 문법을 사용하여 응답 (## 제목, ### 소제목, **굵은글씨**, - 리스트 등)
- 인사말 없이 바로 "## 경로 선택 확인" 제목으로 시작
- 상담사처럼 친근하고 전문적인 톤으로 작성
- 120-150단어 내외로 간결하게 작성
- 각 카테고리당 정확히 1개의 질문만 포함
- **선택 이유**, **구체적 목표**, **현재 상황** 각각 1개씩 총 3개 질문
- 다음 단계(path_deepening)에서 활용할 수 있는 핵심 컨텍스트 정보 수집에 초점
"""
            
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.4
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"경로 선택 응답 생성 중 오류: {e}")
            return "경로 선택을 확인했습니다. 이제 구체적인 목표를 설정해보겠습니다."
    
    async def process_path_selection_node(self, state: ChatState) -> Dict[str, Any]:
        """
        사용자가 선택한 경로를 처리하고 심화 질문을 진행한다.
        """
        print(" 경로 선택 처리 시작...")
        
        user_question = state.get("user_question", "").strip()
        career_paths = state.get("career_paths_suggested", [])
        
        # 사용자 선택 파싱
        selected_path = None
        user_question_upper = user_question.upper()
        
        # 번호 기반 선택 처리
        if "1번" in user_question or "1" in user_question or "첫" in user_question or "ONE" in user_question_upper:
            selected_path = career_paths[0] if len(career_paths) > 0 else None
        elif "2번" in user_question or "2" in user_question or "둘" in user_question or "TWO" in user_question_upper:
            selected_path = career_paths[1] if len(career_paths) > 1 else None
        else:
            # ID나 이름 기반 선택 처리
            for path in career_paths:
                if (path.get("id", "") in user_question_upper or 
                    path.get("name", "") in user_question):
                    selected_path = path
                    break
        
        # 기본값 처리
        if not selected_path:
            selected_path = career_paths[0] if career_paths else {"name": "기본 경로", "id": "default_path"}
        
        # selected_path에 path_name 추가
        if selected_path and "path_name" not in selected_path:
            selected_path["path_name"] = selected_path.get("name", "선택된 경로")
        
        user_data = self.graph_builder.get_user_info_from_session(state)
        collected_info = state.get("collected_user_info", {})
        merged_user_data = {**user_data, **collected_info}
        
        # AI 기반 경로 선택 확인 및 목표 설정 질문 생성
        ai_response = await self._generate_path_selection_response(merged_user_data, selected_path)
        
        # 응답 구성
        deepening_response = {
            "message": ai_response,
            "selected_path": selected_path
        }
        
        # path_selection에서 수집된 정보를 path_deepening에서 활용할 수 있도록 저장
        path_selection_info = {
            "user_input_for_deepening": user_question  # 다음 단계에서 분석할 사용자 응답 (유일하게 실제 사용되는 정보)
        }
        
        # HTML 로그 저장
        save_career_response_to_html("path_selection", deepening_response, state.get("session_id", "unknown"))
        
        # path_selection에서 state_trace에 추가
        import time
        updated_state_trace = state.get("state_trace", []) + [f"path_selection_completed_{int(time.time())}"]
        
        return {
            **state,
            "consultation_stage": "deepening",
            "selected_career_path": selected_path,
            "path_selection_info": path_selection_info,  # path_deepening에서 활용할 정보
            "path_name": selected_path.get("path_name") or selected_path.get("name", "선택된 경로"),  # learning_roadmap에서 사용
            "formatted_response": deepening_response,
            "final_response": deepening_response,
            "awaiting_user_input": True,
            "next_expected_input": "goals_and_reasons",
            "state_trace": updated_state_trace,  # 추적 정보 업데이트
            "processing_log": state.get("processing_log", []) + [f"경로 선택 완료: {selected_path.get('name', '')} (번호: {selected_path.get('number', 'N/A')})"]
        }
