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
            
            # 디버깅: AI 메서드에 전달된 데이터 확인
            print(f"🔍 DEBUG - path_selection AI 메서드에 전달된 merged_user_data: {merged_user_data}")
            print(f"🔍 DEBUG - path_selection selected_path: {selected_path}")
            
            prompt = f"""
당신은 G.Navi의 전문 커리어 상담사입니다. 현재 상담이 진행 중이며, {merged_user_data.get('name', '고객')}님이 "{path_name}" 경로를 선택했습니다.

**고객 정보:**
- 이름: {merged_user_data.get('name', '고객')}
- 경력: {merged_user_data.get('experience', '정보 없음')}
- 보유 기술: {skills_str}
- 도메인: {merged_user_data.get('domain', '정보 없음')}
- 선택한 경로: {path_name}

**요청사항:**
1. 경로 선택에 대한 간단한 확인
2. 선택 이유를 묻는 질문
3. 구체적인 목표 설정을 위한 질문들

**응답 형식 (반드시 마크다운 문법을 사용하여 작성해주세요):**

## 경로 선택 확인

**{merged_user_data.get('name', '고객')}님**이 선택하신 **{path_name}** 경로는 훌륭한 선택입니다! 

### 선택 이유 및 목표 설정

이제 더 구체적인 계획을 세워보겠습니다. 아래 질문들에 답변해 주세요:

**1. 선택 이유**
- 이 경로를 선택하신 구체적인 이유는 무엇인가요?

**2. 목표 설정**
- [구체적인 목표 관련 질문]
- [달성 가능한 단계별 계획 질문]
- [시간 제한이 있는 목표 질문]

**작성 지침:**
- 반드시 마크다운 문법을 사용하여 응답 (## 제목, ### 소제목, **굵은글씨**, - 리스트 등)
- 인사말 없이 바로 "## 경로 선택 확인" 제목으로 시작
- 상담사처럼 친근하고 전문적인 톤으로 작성
- 100-120단어 내외로 간결하게 작성
- 고객이 구체적으로 답변할 수 있는 명확한 질문들 포함
- 구체적(Specific), 달성가능(Achievable), 시간제한(Time-bound) 관점에서 질문 구성
"""
            
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0.6
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"경로 선택 응답 생성 중 오류: {e}")
            return "경로 선택을 확인했습니다. 이제 구체적인 목표를 설정해보겠습니다."
    
    async def process_path_selection_node(self, state: ChatState) -> Dict[str, Any]:
        """
        사용자가 선택한 경로를 처리하고 심화 질문을 진행한다.
        """
        print("🛤️ 경로 선택 처리 시작...")
        
        user_question = state.get("user_question", "").strip()
        career_paths = state.get("career_paths_suggested", [])
        
        # 사용자 선택 파싱 - 다양한 형태의 선택을 처리
        selected_path = None
        user_question_upper = user_question.upper()
        
        # 디버깅: 선택 파싱 로직 확인
        print(f"🔍 DEBUG - user_question: '{user_question}'")
        print(f"🔍 DEBUG - career_paths: {career_paths}")
        
        # 1. 번호 기반 선택 처리 ("1번", "2번", "첫번째", "두번째" 등)
        if "1번" in user_question or "1" in user_question or "첫" in user_question or "ONE" in user_question_upper:
            selected_path = career_paths[0] if len(career_paths) > 0 else None
            print(f"🔍 DEBUG - 1번 경로 선택됨: {selected_path}")
        elif "2번" in user_question or "2" in user_question or "둘" in user_question or "TWO" in user_question_upper:
            selected_path = career_paths[1] if len(career_paths) > 1 else None
            print(f"🔍 DEBUG - 2번 경로 선택됨: {selected_path}")
        else:
            # 2. ID나 이름 기반 선택 처리 (기존 로직)
            for i, path in enumerate(career_paths):
                if (path.get("id", "") in user_question_upper or 
                    path.get("name", "") in user_question):
                    selected_path = path
                    print(f"🔍 DEBUG - ID/이름 기반으로 {i+1}번째 경로 선택됨: {selected_path}")
                    break
        
        # 3. 기본값 처리 (선택을 인식하지 못한 경우 첫 번째 경로)
        if not selected_path:
            selected_path = career_paths[0] if career_paths else {"name": "기본 경로", "id": "default_path"}
            print(f"🔍 DEBUG - 기본값으로 첫 번째 경로 선택: {selected_path}")
        
        # 4. selected_path에 path_name 추가 (learning_roadmap에서 사용)
        if selected_path and "path_name" not in selected_path:
            selected_path["path_name"] = selected_path.get("name", "선택된 경로")
        
        user_data = self.graph_builder.get_user_info_from_session(state)
        collected_info = state.get("collected_user_info", {})
        merged_user_data = {**user_data, **collected_info}
        
        # 디버깅: 데이터 확인
        print(f"🔍 DEBUG - path_selection user_data from session: {user_data}")
        print(f"🔍 DEBUG - path_selection collected_info: {collected_info}")
        print(f"🔍 DEBUG - path_selection merged_user_data: {merged_user_data}")
        
        # AI 기반 경로 선택 확인 및 목표 설정 질문 생성
        ai_response = await self._generate_path_selection_response(merged_user_data, selected_path)
        
        # 응답 구성
        deepening_response = {
            "message": ai_response,
            "selected_path": selected_path
        }
        
        # HTML 로그 저장
        save_career_response_to_html("path_selection", deepening_response, state.get("session_id", "unknown"))
        
        return {
            **state,
            "consultation_stage": "deepening",
            "selected_career_path": selected_path,
            "path_name": selected_path.get("path_name") or selected_path.get("name", "선택된 경로"),  # learning_roadmap에서 사용
            "formatted_response": deepening_response,
            "final_response": deepening_response,
            "awaiting_user_input": True,
            "next_expected_input": "goals_and_reasons",
            "processing_log": state.get("processing_log", []) + [f"경로 선택 완료: {selected_path.get('name', '')} (번호: {selected_path.get('number', 'N/A')})"]
        }
