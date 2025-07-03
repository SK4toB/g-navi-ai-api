# app/graphs/nodes/career_consultation/career_positioning.py
"""
커리어 포지셔닝 및 시장 분석 노드
기존의 intent_analysis + data_retrieval + response_formatting 노드를 재활용
AI 답변을 활용한 개인 맞춤형 분석 추가
"""

import os
from typing import Dict, Any
from app.graphs.state import ChatState
from app.utils.html_logger import save_career_response_to_html
from app.graphs.agents.mermaid_agent import MermaidDiagramAgent


class CareerPositioningNode:
    """
    커리어 포지셔닝 노드 - 기존 노드들을 재활용하여 포지셔닝 분석 수행
    """
    
    def __init__(self, graph_builder):
        self.graph_builder = graph_builder
        # 기존 노드들 재활용
        self.intent_analysis_node = graph_builder.intent_analysis_node
        self.data_retrieval_node = graph_builder.data_retrieval_node
        self.response_formatting_node = graph_builder.response_formatting_node
        # Mermaid 다이어그램 에이전트 추가
        self.mermaid_agent = MermaidDiagramAgent()
    
    async def _generate_ai_career_analysis(self, merged_user_data: dict, retrieved_data: dict) -> Dict[str, Any]:
        """AI를 활용한 개인 맞춤형 커리어 분석 및 방향성 제안"""
        try:
            # 디버깅: AI 메서드에 전달된 데이터 확인
            print(f"🔍 DEBUG - AI 메서드에 전달된 merged_user_data: {merged_user_data}")
            print(f"🔍 DEBUG - retrieved_data keys: {list(retrieved_data.keys()) if retrieved_data else 'None'}")
            
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
                # retriever 모듈에서 직접 회사 비전 컨텍스트 생성
                from app.graphs.agents.retriever import CareerEnsembleRetrieverAgent
                temp_retriever = CareerEnsembleRetrieverAgent()
                company_vision_context = temp_retriever.get_company_vision_context()
                print(f"🔍 DEBUG - 회사 비전 컨텍스트 가져오기 성공: {len(company_vision_context)}자")
            except Exception as e:
                print(f"❌ WARNING - 회사 비전 컨텍스트 가져오기 실패: {e}")
                company_vision_context = ""
            
            # 병합된 사용자 정보를 바탕으로 AI 프롬프트 구성
            skills_str = ", ".join(merged_user_data.get('skills', ['정보 없음']))
            print(f"🔍 DEBUG - skills_str 생성: {skills_str}")
            
            # retrieved_data에서 사내 경력 데이터 추출
            career_data = retrieved_data.get('career_data', [])
            career_context = ""
            
            if career_data:
                career_context = f"사내 경력 데이터 (최대 15명까지): {str(career_data)[:2000]}"
                print(f"🔍 DEBUG - career_context 길이: {len(career_context)}")
                print(f"🔍 DEBUG - career_data 개수: {len(career_data)}")
            else:
                print("🔍 DEBUG - career_data가 비어있음")
            
            print(f"🔍 DEBUG - 프롬프트에 사용될 이름: {merged_user_data.get('name', '고객')}")
            print(f"🔍 DEBUG - 프롬프트에 사용될 경력: {merged_user_data.get('experience', '정보 없음')}")
            print(f"🔍 DEBUG - 프롬프트에 사용될 도메인: {merged_user_data.get('domain', '정보 없음')}")
            
            prompt = f"""
당신은 G.Navi의 전문 커리어 상담사입니다. 사내 구성원 데이터(최대 15명)를 기반으로 {merged_user_data.get('name', '고객')}님의 커리어 포지셔닝을 분석하고 개인화된 방향성을 제안해주세요.

{company_vision_context}

**사용자 프로필:**
- 이름: {merged_user_data.get('name', '고객')}
- 경력: {merged_user_data.get('experience', '정보 없음')}
- 보유 기술: {skills_str}
- 도메인: {merged_user_data.get('domain', '정보 없음')}

**사내 구성원 성장 경로 데이터 (최대 15명):**
{career_context}

**응답 형식 (반드시 마크다운 문법을 사용하여 이 구조를 정확히 따라주세요):**

## 종합 역량 분석 및 성장 방향성

현재 수행 경험과 학습 이력을 분석한 결과, **[구체적인 강점 영역]** 역량에 강점이 있는 것으로 판단되며, **[추천 성장 방향]** 확장을 통해 지식과 경험을 넓혀 나갈 것을 추천합니다.

현재 보유한 경험과 역량을 기반으로 **[1번 또는 2번 방향성 중 하나의 구체적인 추천 경로]**로의 성장 경로를 추천합니다. 유사 경력 경로를 밟은 사내 구성원들의 데이터를 분석해보니, [구체적인 성장 조건이나 기간, 필요 역량]이면 **[목표 레벨]**로 성장이 가능합니다. 이 때, **[핵심 성공 요인들]**이 성장에 도움이 됩니다.

*이 추천 방향성은 개인의 역량 데이터와 함께 회사의 최신 기술 트렌드 및 비전에 부합하는 방향을 종합 분석하여 제시됩니다.*

## 추천 커리어 경로

### 1. [구체적인 방향성 제목]
- **핵심**: [이 경로의 핵심 가치와 특징을 간단명료하게]
- **데이터 분석**: [사내 구성원들의 성장 데이터 분석 결과, 구체적인 성장 조건, 필요 기간, 핵심 역량, 성공률 등을 수치와 함께 제시]

### 2. [구체적인 방향성 제목]
- **핵심**: [이 경로의 핵심 가치와 특징을 간단명료하게]
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
- "이 추천 방향성은 개인의 역량 데이터와 함께 회사의 최신 기술 트렌드 및 비전에 부합하는 방향을 종합 분석하여 제시됩니다." 문장을 반드시 포함
- 정확히 2개의 방향성만 제시 (### 1. 과 ### 2. 형식으로)
- 전체 280-320단어 내외로 명확하고 구체적인 톤 유지
- "~합니다", "~됩니다" 등 단정적이고 전문적인 어투 사용
- 구체적인 숫자, 기간, 레벨, 조건 등을 명시하여 신뢰도 제고
- 집단 데이터 분석 결과로 나타난 공통 성장 패턴, 핵심 역량, 성공 요인을 구체적으로 제시
- "이 때, **[구체적 조건]**이 성장에 도움이 됩니다" 형식으로 추가 조건 명시
- 개인의 현재 역량과 상황을 반영한 맞춤형 제안
- 선택 안내에서 1번 또는 2번 경로 선택을 명시하여 고객이 쉽게 응답할 수 있도록 안내
- 회사 비전 정보가 제공된 경우, 해당 가치와 전략 방향에 부합하는 커리어 경로를 우선적으로 제안
"""
            
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.7
            )
            
            ai_content = response.choices[0].message.content.strip()
            print(f"🔍 DEBUG - AI 응답 내용: {ai_content[:200]}...")
            
            # AI 응답을 파싱하여 커리어 방향성 추출 (개선된 방식)
            career_paths = []
            lines = ai_content.split('\n')
            
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
                    print(f"🔍 DEBUG - 파싱된 경로 {path_number}: {career_path}")
            
            # 파싱 결과가 없으면 기본 경로 생성
            if not career_paths:
                print("🔍 DEBUG - 경로 파싱 실패, 기본 경로 생성")
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
            
            print(f"🔍 DEBUG - 최종 career_paths: {career_paths}")
            
            return {
                "message": ai_content,
                "career_paths": career_paths
            }
            
        except Exception as e:
            print(f"AI 분석 생성 중 오류: {e}")
            return {
                "message": "AI 분석을 생성하는 중 문제가 발생했습니다. 다시 시도해주세요.",
                "career_paths": []
            }
    
    async def _generate_career_path_diagram(self, ai_result: Dict[str, Any], user_data: Dict[str, Any], state: ChatState) -> str:
        """
        AI가 생성한 커리어 방향성 정보를 기반으로 커리어 전환 경로 Mermaid 다이어그램 생성
        
        Args:
            ai_result: AI가 생성한 커리어 분석 결과
            user_data: 사용자 정보
            state: 현재 상태
            
        Returns:
            str: Mermaid 다이어그램 코드 (빈 문자열이면 생성 실패)
        """
        try:
            print("🎨 커리어 전환 경로 다이어그램 생성 시작...")
            
            # 커리어 전환 경로에 특화된 컨텍스트 구성
            career_transition_context = f"""
커리어 전환 경로 시각화 요청:

현재 사용자 상황:
- 이름: {user_data.get('name', '사용자')}
- 현재 경력: {user_data.get('experience', '정보 없음')}
- 보유 기술: {', '.join(user_data.get('skills', ['정보 없음']))}
- 도메인: {user_data.get('domain', '정보 없음')}

AI 분석 결과 (커리어 방향성):
{ai_result['message']}

시각화 요구사항:
1. 현재 포지션에서 제안된 2-3가지 커리어 방향으로의 전환 경로를 보여주는 다이어그램
2. 각 경로별 핵심 단계와 필요한 역량 개발 과정을 포함
3. 사내 사례에서 언급된 실제 전환 경로를 참고하여 구성
4. flowchart 또는 timeline 형태로 전환 과정을 명확히 표현
5. 현재 → 중간 단계 → 목표 포지션의 흐름을 시각적으로 표현

다이어그램 유형: 커리어 전환 경로 (Career Transition Path)
"""
            
            # 사용자 질문 정보 가져오기 (커리어 전환 컨텍스트 추가)
            user_question = state.get("current_question", "커리어 전환 경로 분석")
            
            # 의도 분석 정보 가져오기
            intent_analysis = state.get("intent_analysis", {})
            # 커리어 전환에 특화된 의도 정보 추가
            intent_analysis["career_transition_focus"] = True
            intent_analysis["diagram_type"] = "career_path_transition"
            
            # MermaidDiagramAgent를 사용하여 커리어 전환 경로 다이어그램 생성
            mermaid_code = self.mermaid_agent.generate_diagram(
                formatted_content=career_transition_context,
                user_question=user_question,
                intent_analysis=intent_analysis,
                user_data=user_data
            )
            
            if mermaid_code:
                print(f"✅ 커리어 전환 경로 다이어그램 생성 완료 ({len(mermaid_code)}자)")
                return mermaid_code
            else:
                print("⚠️ 커리어 전환 경로 다이어그램 생성 실패")
                return ""
                
        except Exception as e:
            print(f"❌ 커리어 전환 다이어그램 생성 중 오류: {e}")
            return ""
    
    async def career_positioning_node(self, state: ChatState) -> Dict[str, Any]:
        """
        현재 데이터를 기반으로 포지셔닝 및 시장 분석을 수행하고
        사용자 맞춤형 경로 2~3가지를 제시한다.
        """
        print("🎯 커리어 포지셔닝 분석 시작...")
        
        # 1. 기존 의도 분석 노드 활용
        state = self.intent_analysis_node.analyze_intent_node(state)
        
        # 2. 기존 데이터 검색 노드 활용 (사내 경력 데이터 15명까지 수집)
        # 커리어 검색 개수를 15로 설정
        state["career_search_count"] = 15
        print(f"🔍 DEBUG - career_search_count 설정: {state['career_search_count']}")
        state = self.data_retrieval_node.retrieve_additional_data_node(state)
        
        # career_cases를 올바른 형태로 변환
        career_cases = state.get("career_cases", [])
        print(f"🔍 DEBUG - career_positioning에서 검색된 career_cases: {len(career_cases)}개")
        print(f"🔍 DEBUG - career_cases 타입: {type(career_cases)}")
        
        # career_cases가 비어있는 경우 처리
        if not career_cases:
            print("❌ WARNING - career_cases가 비어있음! 데이터 검색에 실패했을 가능성")
            print(f"🔍 DEBUG - state에서 data_retrieval_node 실행 후 확인:")
            print(f"🔍 DEBUG - state keys: {list(state.keys())}")
            
            # 다른 키들도 확인해보기
            for key in ['career_data', 'career_results', 'search_results']:
                if key in state:
                    print(f"🔍 DEBUG - state['{key}']: {type(state[key])}, 길이: {len(state[key]) if hasattr(state[key], '__len__') else 'N/A'}")
        
        # LangChain Document 객체에서 메타데이터 추출하여 구조화된 데이터로 변환
        structured_career_data = []
        for i, case in enumerate(career_cases):
            print(f"🔍 DEBUG - 처리 중인 case {i+1}: {type(case)}")
            if hasattr(case, 'metadata'):
                metadata = case.metadata
                print(f"🔍 DEBUG - case {i+1} metadata keys: {list(metadata.keys()) if metadata else 'None'}")
                # 메타데이터 구조에 상관없이 기본 정보만 저장
                career_info = {
                    "data_source": "career_case",
                    "case_id": f"case_{i+1}",
                    "metadata": metadata,  # 원본 메타데이터 전체 저장
                    "document_type": "career_data"
                }
                structured_career_data.append(career_info)
                print(f"🔍 DEBUG - 구조화된 데이터 추가: case_{i+1} (메타데이터 키 개수: {len(metadata.keys()) if metadata else 0})")
            elif hasattr(case, 'page_content'):
                # Document 객체의 경우
                career_info = {
                    "data_source": "document",
                    "case_id": f"case_{i+1}",
                    "page_content": case.page_content[:200] if case.page_content else "",
                    "document_type": "career_data"
                }
                structured_career_data.append(career_info)
                print(f"🔍 DEBUG - Document 객체 추가: case_{i+1} (content 길이: {len(case.page_content) if case.page_content else 0})")
            else:
                print(f"❌ WARNING - case {i+1}에 metadata나 page_content 속성이 없음: {case}")
                # 기본 정보라도 저장
                career_info = {
                    "data_source": "unknown",
                    "case_id": f"case_{i+1}",
                    "raw_data": str(case)[:100],
                    "document_type": "career_data"
                }
                structured_career_data.append(career_info)
        
        print(f"✅ career_positioning에서 구조화된 사내 구성원 데이터: {len(structured_career_data)}개")
        
        # 구조화된 데이터의 샘플 확인 (디버깅)
        if structured_career_data:
            print(f"🔍 DEBUG - structured_career_data 샘플: {structured_career_data[0]}")
            print(f"🔍 DEBUG - 모든 employee_id: {[item.get('metadata', {}).get('employee_id', 'Unknown') for item in structured_career_data]}")
        else:
            print("❌ WARNING - structured_career_data가 비어있음! Mock 데이터 생성")
            # 검색에 실패한 경우 기본 mock 데이터 생성 (테스트용)
            structured_career_data = [
                {
                    "experience": "3년차 백엔드 개발자",
                    "skills": ["Python", "Django", "AWS"],
                    "domain": "핀테크",
                    "career_path": "시니어 개발자 → 테크리드",
                    "employee_id": "Mock_001"
                },
                {
                    "experience": "5년차 데이터 분석가",
                    "skills": ["Python", "SQL", "Tableau"],
                    "domain": "마케팅",
                    "career_path": "데이터 분석가 → 데이터 사이언티스트",
                    "employee_id": "Mock_002"
                },
                {
                    "experience": "4년차 프론트엔드 개발자",
                    "skills": ["React", "TypeScript", "Next.js"],
                    "domain": "이커머스",
                    "career_path": "주니어 개발자 → 프론트엔드 리드",
                    "employee_id": "Mock_003"
                }
            ]
            print(f"🔧 FALLBACK - Mock 데이터 생성 완료: {len(structured_career_data)}개")
        
        # retrieved_data 구성
        retrieved_data = {
            "career_data": structured_career_data,  # 구조화된 데이터 사용
            "education_courses": state.get("education_courses", {}),
            "news_data": state.get("news_data", []),
            "past_conversations": state.get("past_conversations", [])
        }
        
        print(f"🔍 DEBUG - retrieved_data 구성: career_data={len(retrieved_data['career_data'])}개")
        
        # 3. 사용자 정보 병합 (기존 정보 + 수집된 정보)
        user_data = self.graph_builder.get_user_info_from_session(state)
        collected_info = state.get("collected_user_info", {})
        merged_user_data = {**user_data, **collected_info}
        
        # 디버깅: 실제 데이터 확인
        print(f"🔍 DEBUG - user_data from session: {user_data}")
        print(f"🔍 DEBUG - collected_info from state: {collected_info}")
        print(f"🔍 DEBUG - merged_user_data: {merged_user_data}")
        
        # 4. AI 기반 커리어 분석 및 방향성 제안 (사내 데이터 활용)
        ai_result = await self._generate_ai_career_analysis(merged_user_data, retrieved_data)
        
        # 5. Mermaid 다이어그램 생성 (커리어 방향성 시각화)
        mermaid_diagram = await self._generate_career_path_diagram(ai_result, merged_user_data, state)
        
        # 6. 응답 구성
        positioning_response = {
            "message": ai_result["message"],
            "career_paths": ai_result["career_paths"],
            "mermaid_diagram": mermaid_diagram if mermaid_diagram else None
        }
        
        # HTML 로그 저장
        save_career_response_to_html("career_positioning", positioning_response, state.get("session_id", "unknown"))

        # 최종 저장 전 데이터 확인 (디버깅)
        print(f"🔍 DEBUG - state에 저장할 retrieved_career_data: {len(structured_career_data)}개")
        print(f"🔍 DEBUG - 저장될 데이터 타입: {type(structured_career_data)}")
        if structured_career_data:
            print(f"🔍 DEBUG - 첫 번째 데이터 구조: {list(structured_career_data[0].keys())}")
            print(f"🔍 DEBUG - 샘플 employee_id들: {[item.get('employee_id', 'N/A') for item in structured_career_data[:3]]}")
        else:
            print("❌ WARNING - structured_career_data가 비어있음!")
            
        # 반환할 state 구성
        final_state = {
            **state,
            "consultation_stage": "path_selection",
            "career_paths_suggested": positioning_response["career_paths"],
            "formatted_response": positioning_response,
            "final_response": positioning_response,
            "awaiting_user_input": True,
            "next_expected_input": "career_path_choice",
            "collected_user_info": collected_info,
            "retrieved_career_data": structured_career_data,  # 구조화된 사내 구성원 데이터 저장
            "processing_log": state.get("processing_log", []) + ["커리어 포지셔닝 분석 완료"]
        }
        
        # 반환 직전 final_state에서 retrieved_career_data 재확인
        print(f"🔍 DEBUG - final_state에서 retrieved_career_data 확인: {len(final_state.get('retrieved_career_data', []))}개")
        print(f"🔍 DEBUG - final_state의 주요 키들: {list(final_state.keys())}")
        print(f"🔍 DEBUG - awaiting_user_input: {final_state.get('awaiting_user_input')}")
        print(f"🔍 DEBUG - consultation_stage: {final_state.get('consultation_stage')}")
        
        # State 전달 체크를 위한 고유 식별자 추가
        import time
        final_state["career_positioning_timestamp"] = time.time()
        final_state["state_trace"] = final_state.get("state_trace", []) + [f"career_positioning_completed_{int(time.time())}"]
        
        print(f"🔍 DEBUG - state_trace 추가됨: {final_state.get('state_trace')}")
        print(f"🔍 DEBUG - career_positioning_timestamp: {final_state.get('career_positioning_timestamp')}")
        
        return final_state
    
    # 기존 템플릿 헬퍼 메서드들 제거됨 - AI가 모든 분석을 담당
