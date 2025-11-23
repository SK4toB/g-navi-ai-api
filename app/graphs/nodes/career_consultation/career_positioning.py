# app/graphs/nodes/career_consultation/career_positioning.py
"""
커리어 포지셔닝 및 시장 분석 노드 (Agent 기반)
기존 노드 대신 Agent를 직접 활용하여 간결한 구조로 변경
"""

import os
import json
from typing import Dict, Any
from app.graphs.state import ChatState
from app.utils.html_logger import save_career_response_to_html


class CareerPositioningNode:
    """
    커리어 포지셔닝 노드 - Agent 기반 간결한 구조
    """
    
    def __init__(self, graph_builder):
        self.graph_builder = graph_builder
        # Agent들을 직접 사용
        from app.graphs.agents.analyzer import IntentAnalysisAgent
        from app.graphs.agents.retriever import CareerEnsembleRetrieverAgent
        from app.graphs.agents.formatter import ResponseFormattingAgent
        from app.graphs.agents.mermaid_agent import MermaidDiagramAgent
        
        self.intent_agent = IntentAnalysisAgent()
        self.retriever_agent = CareerEnsembleRetrieverAgent()
        self.formatter_agent = ResponseFormattingAgent()
        self.mermaid_agent = MermaidDiagramAgent()
    
    async def _generate_ai_career_analysis(self, merged_user_data: dict, retrieved_data: dict) -> Dict[str, Any]:
        """AI를 활용한 개인 맞춤형 커리어 분석 및 방향성 제안"""
        try:
            from openai import AsyncOpenAI
            
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return {
                    "message": "AI 분석 기능이 현재 이용 불가합니다.",
                    "career_paths": []
                }
            
            client = AsyncOpenAI(api_key=api_key)
            
            # 회사 비전 컨텍스트 가져오기
            company_vision_context = ""
            try:
                company_vision_context = self.retriever_agent.get_company_vision_context()
            except Exception as e:
                print(f"- WARNING - 회사 비전 컨텍스트 가져오기 실패: {e}")
                company_vision_context = ""
            
            # 사용자 정보 문자열 생성
            skills_str = ", ".join(merged_user_data.get('skills', ['정보 없음']))
            career_data = retrieved_data.get('career_data', [])
            
            # 커리어 데이터 컨텍스트 생성
            career_context = ""
            if career_data:
                career_context = f"사내 경력 데이터 (최대 30명): {str(career_data)}"
                print(f" DEBUG - 생성된 career_context 길이: {len(career_context)}")
            
            prompt = f"""
당신은 G.Navi의 전문 커리어 상담사입니다. 사내 구성원 데이터(최대 30명)를 기반으로 {merged_user_data.get('name', '고객')}님의 커리어 포지셔닝을 분석하고 개인화된 방향성을 제안해주세요.

{company_vision_context}

**중요: 위에 제시된 회사 비전 및 전략 방향성을 반드시 고려하여 커리어 경로를 제안하세요. 개인의 역량과 회사의 미래 비전이 일치하는 방향으로 성장 경로를 설계해야 합니다.**

**사용자 프로필:**
- 이름: {merged_user_data.get('name', '고객')}
- 경력: {merged_user_data.get('experience', '정보 없음')}
- 보유 기술: {skills_str}
- 도메인: {merged_user_data.get('domain', '정보 없음')}

**사내 구성원 성장 경로 데이터 (최대 30명):**
{career_context}

**응답 형식 (반드시 마크다운 문법을 사용하여 이 구조를 정확히 따라주세요):**

## 종합 역량 분석 및 성장 방향성

현재 수행 경험과 학습 이력을 분석한 결과, **[구체적인 강점 영역]** 역량에 강점이 있는 것으로 판단되며, **[추천 성장 방향]** 확장을 통해 지식과 경험을 넓혀 나갈 것을 추천합니다.

현재 보유한 경험과 역량을 기반으로 **회사의 비전과 전략 방향성에 부합**하는 방향을 종합 분석하여 **[1번 또는 2번 방향성 중 하나의 구체적인 추천 경로]**로의 성장 경로를 추천합니다. 유사 경력 경로를 밟은 사내 구성원들의 데이터를 분석해보니, [구체적인 성장 조건이나 기간, 필요 역량]이면 **[목표 레벨]**로 성장이 가능합니다. 이 때, **[핵심 성공 요인들]**이 성장에 도움이 됩니다.

## 추천 커리어 경로

### 1. [구체적인 방향성 제목]
- **핵심**: [이 경로의 핵심 가치와 특징을 간단명료하게]
- **회사 비전 연계**: [위에서 제시된 회사 비전 및 전략과 이 경로가 어떻게 연결되는지 구체적으로 설명]
- **데이터 분석**: [사내 구성원들의 성장 데이터 분석 결과, 구체적인 성장 조건, 필요 기간, 핵심 역량, 성공률 등을 수치와 함께 제시]

### 2. [구체적인 방향성 제목]
- **핵심**: [이 경로의 핵심 가치와 특징을 간단명료하게]
- **회사 비전 연계**: [위에서 제시된 회사 비전 및 전략과 이 경로가 어떻게 연결되는지 구체적으로 설명]
- **데이터 분석**: [사내 구성원들의 성장 데이터 분석 결과, 구체적인 성장 조건, 필요 기간, 핵심 역량, 성공률 등을 수치와 함께 제시]

## 선택 안내

위 방향성 중에서 **{merged_user_data.get('name', '고객')}님**의 현재 상황과 목표에 가장 적합한 경로를 선택해 주세요. 각 방향성은 사내 구성원들의 실제 성장 데이터를 바탕으로 검증된 경로입니다.

**어떤 경로를 선택하시겠습니까?**
- "1번 경로를 선택합니다"
- "2번 경로를 선택합니다"
위와 같이 번호를 명시하여 답변해 주시기 바랍니다.

**작성 지침:**
- 반드시 마크다운 문법을 사용하여 응답 (## 제목, ### 소제목, **굵은글씨**, - 리스트 등)
- 인사말 없이 바로 "## 종합 역량 분석 및 성장 방향성" 제목으로 시작
- 첫 번째 문단에서 "현재 수행 경험과 학습 이력을 분석한 결과"로 시작하여 강점 영역 분석
- 두 번째 문단에서 "현재 보유한 경험과 역량을 기반으로 **[1번 또는 2번 중 하나의 구체적 경로]**로의 성장 경로를 추천합니다"로 연결
- 추천하는 구체적 경로는 반드시 아래 1번 또는 2번 방향성 중 하나여야 함
- "유사 경력 경로를 밟은 사내 구성원들의 데이터를 분석해보니" 문장을 반드시 포함
- 정확히 2개의 방향성만 제시 (### 1. 과 ### 2. 형식으로)
- **각 경로마다 반드시 "회사 비전 연계" 항목을 포함하여 위에서 제시된 회사 비전/전략과의 구체적 연결점 설명**
- 전체 400-500단어 내외로 명확하고 구체적인 톤 유지
- "~합니다", "~됩니다" 등 단정적이고 전문적인 어투 사용
- 구체적인 숫자, 기간, 레벨, 조건 등을 명시하여 신뢰도 제고
- 집단 데이터 분석 결과로 나타난 공통 성장 패턴, 핵심 역량, 성공 요인을 구체적으로 제시
- "이 때, **[구체적 조건]**이 성장에 도움이 됩니다" 형식으로 추가 조건 명시
- 개인의 현재 역량과 상황을 반영한 맞춤형 제안
- 선택 안내에서 1번 또는 2번 경로 선택을 명시하여 고객이 쉽게 응답할 수 있도록 안내
- **회사 비전 컨텍스트를 적극 활용하여 회사의 미래 방향성과 개인 성장이 일치하는 경로를 우선 제안**
- **회사 비전에서 언급된 핵심 키워드나 전략 방향을 각 커리어 경로 설명에 직접 반영**
"""
            
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.4
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # AI 응답에서 커리어 경로 정보 추출 (텍스트 파싱)
            career_paths = []
            lines = ai_response.split('\n')
            
            print(" DEBUG - 텍스트에서 경로 추출 시작")
            # ### 1. 또는 ### 2. 형태의 경로 제목을 찾아서 파싱
            for i, line in enumerate(lines):
                stripped_line = line.strip()
                
                # "### 1." 또는 "### 2." 패턴 찾기
                if stripped_line.startswith('### 1.') or stripped_line.startswith('### 2.'):
                    path_number = "1" if "1." in stripped_line else "2"
                    path_title = stripped_line.replace('### ' + path_number + '.', '').strip()
                    
                    # 다음 몇 줄에서 설명 찾기
                    description_lines = []
                    for j in range(i + 1, min(i + 5, len(lines))):
                        if lines[j].strip() and not lines[j].startswith('###') and not lines[j].startswith('##'):
                            description_lines.append(lines[j].strip())
                    
                    description = ' '.join(description_lines)[:200]  # 최대 200자
                    
                    career_path = {
                        "id": f"path_{path_number}",
                        "name": path_title,
                        "description": description,
                        "path_name": path_title,  # learning_roadmap에서 사용
                        "number": path_number
                    }
                    career_paths.append(career_path)
                    print(f" DEBUG - 파싱된 경로 {path_number}: {career_path}")
            
            # 파싱 결과가 없으면 기본 경로 생성
            if not career_paths:
                print(" DEBUG - 경로 파싱 실패, 기본 경로 생성")
                career_paths = [
                    {
                        "id": "path_1",
                        "name": "첫 번째 제안 경로",
                        "description": "AI가 제안한 첫 번째 커리어 방향성",
                        "path_name": "첫 번째 제안 경로",
                        "number": "1"
                    },
                    {
                        "id": "path_2", 
                        "name": "두 번째 제안 경로",
                        "description": "AI가 제안한 두 번째 커리어 방향성",
                        "path_name": "두 번째 제안 경로",
                        "number": "2"
                    }
                ]
            
            print(f" DEBUG - 최종 career_paths: {career_paths}")
            
            return {
                "message": ai_response,
                "career_paths": career_paths
            }
            
        except Exception as e:
            print(f"- AI 커리어 분석 실패: {e}")
            return {
                "message": "커리어 분석 중 오류가 발생했습니다. 다시 시도해주세요.",
                "career_paths": []
            }
    
    async def _generate_career_path_diagram(self, ai_result: dict, merged_user_data: dict, state: ChatState) -> str:
        """
        AI가 생성한 커리어 방향성 정보를 기반으로 커리어 전환 경로 Mermaid 다이어그램 생성
        """
        try:
            print(" 커리어 전환 경로 다이어그램 생성 시작...")
            
            # 커리어 전환 경로에 특화된 컨텍스트 구성
            career_transition_context = f"""
커리어 전환 경로 시각화 요청:

현재 사용자 상황:
- 이름: {merged_user_data.get('name', '사용자')}
- 현재 경력: {merged_user_data.get('experience', '정보 없음')}
- 보유 기술: {', '.join(merged_user_data.get('skills', ['정보 없음']))}
- 도메인: {merged_user_data.get('domain', '정보 없음')}

AI 분석 결과 (커리어 방향성):
{ai_result['message']}

시각화 요구사항:
1. 현재 포지션에서 제안된 2가지 커리어 방향으로의 전환 경로를 보여주는 다이어그램
2. 각 경로별 핵심 단계와 필요한 역량 개발 과정을 포함
3. 사내 사례에서 언급된 실제 전환 경로를 참고하여 구성
4. flowchart 형태로 전환 과정을 명확히 표현
5. 현재 → 중간 단계 → 목표 포지션의 흐름을 시각적으로 표현

다이어그램 유형: 커리어 전환 경로 (Career Transition Path)
"""
            
            # 사용자 질문 정보 가져오기
            user_question = state.get("current_question", "커리어 전환 경로 분석")
            
            # MermaidDiagramAgent를 사용하여 커리어 전환 경로 다이어그램 생성
            mermaid_code = self.mermaid_agent.generate_diagram(
                formatted_content=career_transition_context,
                user_question=user_question,
                intent_analysis={"career_transition_focus": True, "diagram_type": "career_path_transition"},
                user_data=merged_user_data
            )
            
            if mermaid_code:
                print(f" 커리어 전환 경로 다이어그램 생성 완료 ({len(mermaid_code)}자)")
                return mermaid_code
            else:
                print(" 커리어 전환 경로 다이어그램 생성 실패")
                return ""
                
        except Exception as e:
            print(f"- 커리어 전환 다이어그램 생성 중 오류: {e}")
            return ""

    async def analyze_career_positioning(self, state: ChatState) -> Dict[str, Any]:
        """
        Agent 기반 커리어 포지셔닝 분석 (간결한 버전)
        """
        print(" 커리어 포지셔닝 분석 시작...")
        
        # 1. 사용자 정보 병합
        user_data = self.graph_builder.get_user_info_from_session(state)
        collected_info = state.get("collected_user_info", {})
        merged_user_data = {**user_data, **collected_info}
        
        # 2. Agent 기반 의도 분석
        try:
            intent_analysis = self.intent_agent.analyze_intent_and_context(
                user_question="커리어 포지셔닝 분석",
                user_data=merged_user_data,
                chat_history=state.get("chat_history", [])
            )
        except Exception as e:
            print(f"- Intent 분석 실패: {e}")
            intent_analysis = {"keywords": [], "intent": "career_guidance"}
        
        # 3. Agent 기반 데이터 검색
        try:
            search_results = self.retriever_agent.retrieve(
                query=f"커리어 포지셔닝 {merged_user_data.get('domain', '')} {' '.join(merged_user_data.get('skills', []))}",
                k=20
            )
            # retrieve 메서드는 Document 객체들을 반환하므로 메타데이터 추출
            structured_career_data = []
            for i, doc in enumerate(search_results):
                if hasattr(doc, 'metadata'):
                    career_info = {
                        "experience": doc.metadata.get("experience", "정보 없음"),
                        "skills": doc.metadata.get("skills", []),
                        "domain": doc.metadata.get("domain", "정보 없음"),
                        "career_path": doc.metadata.get("career_path", "정보 없음"),
                        "employee_id": doc.metadata.get("employee_id", f"emp_{i+1}"),
                        "document_type": "career_data"
                    }
                    structured_career_data.append(career_info)
        except Exception as e:
            print(f"- 데이터 검색 실패: {e}")
            structured_career_data = []
        
        # 4. AI 기반 커리어 분석
        ai_result = await self._generate_ai_career_analysis(merged_user_data, {"career_data": structured_career_data})
        message_content = ai_result["message"]
        
        # 5. Mermaid 다이어그램 생성
        mermaid_diagram = ""
        try:
            mermaid_diagram = await self._generate_career_path_diagram(ai_result, merged_user_data, state)
        except Exception as e:
            print(f"- Mermaid 다이어그램 생성 실패: {e}")
            mermaid_diagram = ""
            
        # 6. 다이어그램을 마크다운 응답에 통합
        if mermaid_diagram and mermaid_diagram.strip():
            # 다이어그램 섹션 생성
            diagram_section = f"""

---

```mermaid
{mermaid_diagram.strip()}
```

*위 다이어그램은 경로 전환 과정을 구조적으로 시각화한 것입니다.*

---
"""
            # 적절한 위치 찾기
            lines = message_content.split('\n')
            insert_index = len(lines)
            
            # "선택 안내" 섹션 전에 다이어그램 삽입
            for i, line in enumerate(lines):
                if "## 선택 안내" in line or "어떤 경로를 선택하시겠습니까" in line:
                    insert_index = i
                    break
            
            # 다이어그램 삽입
            if insert_index < len(lines):
                lines.insert(insert_index, diagram_section)
            else:
                # 적당한 위치가 없으면 마지막에 추가
                lines.append(diagram_section)
                
            # "선택 안내" 섹션이 다이어그램 다음에 오도록 재배치
            message_content = '\n'.join(lines)
            print(f" 다이어그램이 응답에 통합되었습니다. ({len(mermaid_diagram)}자)")
        
        # 7. 응답 구성
        positioning_response = {
            "message": message_content,
            "career_paths": ai_result["career_paths"],
        }
        
        # HTML 로그 저장 - 여기서만 mermaid_diagram 포함
        save_career_response_to_html("career_positioning", {
            "message": message_content,
            "career_paths": ai_result["career_paths"],
            "mermaid_diagram": mermaid_diagram
        }, state.get("session_id", "unknown"))
        
        return {
            **state,
            "consultation_stage": "path_selection",
            "career_paths_suggested": positioning_response["career_paths"],
            "formatted_response": positioning_response,
            "final_response": positioning_response,
            "bot_message": message_content,  # 다이어그램이 통합된 메시지를 botMessage로 설정
            "awaiting_user_input": True,
            "next_expected_input": "career_path_choice",
            "collected_user_info": collected_info,
            "retrieved_career_data": structured_career_data,
            "processing_log": state.get("processing_log", []) + ["커리어 포지셔닝 분석 완료"]
        }
