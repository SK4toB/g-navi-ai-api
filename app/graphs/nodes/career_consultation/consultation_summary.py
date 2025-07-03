# app/graphs/nodes/career_consultation/consultation_summary.py
"""
상담 요약 및 동기부여 마무리 노드
AI 기반 개인화된 동기부여 메시지 생성
"""

import os
from typing import Dict, Any
from app.graphs.state import ChatState
from app.utils.html_logger import save_career_response_to_html


class ConsultationSummaryNode:
    """
    상담 요약 및 마무리 노드
    """
    
    def __init__(self, graph_builder):
        self.graph_builder = graph_builder
    
    async def _generate_consultation_summary(self, merged_user_data: dict, selected_path: dict, consultation_context: dict, processing_log: list) -> str:
        """AI 기반 상담 요약 및 격려 메시지 생성"""
        try:
            from openai import AsyncOpenAI
            
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return f"""## 상담 요약

{merged_user_data.get('name', '고객')}님의 커리어 상담이 완료되었습니다.

**선택된 경로**: {selected_path.get('name', '목표 경로')}
**목표**: {consultation_context.get('user_goals', '설정된 목표')[:200]}

체계적인 계획을 바탕으로 꾸준히 실행해나가시면 반드시 목표를 달성하실 수 있습니다. 응원합니다!"""
            
            client = AsyncOpenAI(api_key=api_key)
            
            skills_str = ", ".join(merged_user_data.get('skills', ['정보 없음']))
            path_name = selected_path.get('name', '선택된 경로')
            user_goals = consultation_context.get('user_goals', '커리어 성장 목표')
            
            # 디버깅: AI 메서드에 전달된 데이터 확인
            print(f"🔍 DEBUG - consultation_summary AI 메서드에 전달된 데이터")
            print(f"   - name: {merged_user_data.get('name')}")
            print(f"   - path_name: {path_name}")
            print(f"   - user_goals: {user_goals[:100]}...")
            print(f"   - processing_log: {processing_log}")
            
            prompt = f"""
당신은 G.Navi의 전문 커리어 상담사입니다. {merged_user_data.get('name', '고객')}님과의 상담이 완료되었습니다. 

**상담 내용 요약:**
- 이름: {merged_user_data.get('name', '고객')}
- 경력: {merged_user_data.get('experience', '정보 없음')}
- 보유 기술: {skills_str}
- 도메인: {merged_user_data.get('domain', '정보 없음')}
- 선택한 경로: {path_name}
- 설정한 목표: {user_goals}

**상담 진행 과정:**
{', '.join(processing_log)}

**요청사항:**
1. 상담 내용의 핵심 요약 (선택한 경로, 주요 결정사항, 향후 계획)
2. 개인 맞춤형 격려 메시지

**응답 형식 (반드시 마크다운 문법을 사용하여 작성해주세요):**

## 상담 요약 완료

### 📋 상담 핵심 내용

**선택된 경로**: {path_name}
**핵심 결정사항**: [상담을 통해 결정된 주요 내용들]
**향후 계획**: [다음 단계 액션 플랜 요약]

### 💪 마무리 격려 메시지

[{merged_user_data.get('name', '고객')}님에게 보내는 개인 맞춤형 격려와 응원 메시지]

**작성 지침:**
- 반드시 마크다운 문법 사용 (## 제목, ### 소제목, **굵은글씨** 등)
- 인사말 없이 바로 "## 상담 요약 완료"로 시작
- 전체 150-200단어 내외로 간결하게 작성
- 상담의 핵심 내용을 정확히 요약
- 따뜻하고 전문적인 격려 메시지로 마무리
- 구체적이고 실행 가능한 내용 위주
"""
            
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
                temperature=0.5
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"AI 상담 요약 생성 중 오류: {e}")
            return f"""## 상담 요약

**{merged_user_data.get('name', '고객')}님**의 커리어 상담이 성공적으로 완료되었습니다.

**선택된 경로**: {selected_path.get('name', '목표 경로')}
**목표**: {consultation_context.get('user_goals', '설정된 목표')[:200]}

체계적인 계획을 바탕으로 꾸준히 실행해나가시면 반드시 목표를 달성하실 수 있습니다. 응원합니다!"""
    
    async def create_consultation_summary_node(self, state: ChatState) -> Dict[str, Any]:
        """
        상담 내용을 요약하고 격려 메시지로 마무리한다.
        """
        print("📝 상담 요약 및 마무리...")
        
        selected_path = state.get("selected_career_path", {})
        consultation_context = state.get("consultation_context", {})
        user_data = self.graph_builder.get_user_info_from_session(state)
        collected_info = state.get("collected_user_info", {})
        merged_user_data = {**user_data, **collected_info}
        processing_log = state.get("processing_log", [])
        
        # 디버깅: 데이터 확인
        print(f"🔍 DEBUG - consultation_summary user_data from session: {user_data}")
        print(f"🔍 DEBUG - consultation_summary collected_info: {collected_info}")
        print(f"🔍 DEBUG - consultation_summary merged_user_data: {merged_user_data}")
        
        # AI 기반 상담 요약 생성
        summary_message = await self._generate_consultation_summary(
            merged_user_data, selected_path, consultation_context, processing_log
        )
        
        # 간결한 요약 응답 구성
        summary_response = {
            "message": summary_message,
            "summary": {
                "consultation_type": "career_consultation",
                "selected_path": selected_path.get('name', '선택된 경로'),
                "user_goals": consultation_context.get('user_goals', '설정된 목표'),
                "completed_stages": processing_log
            }
        }
    
        # HTML 로그 저장
        save_career_response_to_html("consultation_summary", summary_response, state.get("session_id", "unknown"))
    
        return {
            **state,
            "consultation_stage": "completed",
            "formatted_response": summary_response,
            "final_response": summary_response,
            "awaiting_user_input": False,
            "processing_log": processing_log + ["커리어 상담 완료"]
        }
