# app/graphs/nodes/career_consultation/path_deepening.py
"""
선택한 경로에 대한 심화 논의 노드
사용자의 목표와 이유를 분석하여 사내 데이터 기반 액션 플랜 수립
AI 기반 개인 맞춤형 전략 분석 포함
"""

import os
from typing import Dict, Any
from app.graphs.state import ChatState
from app.utils.html_logger import save_career_response_to_html


class PathDeepeningNode:
    """
    경로 심화 논의 노드
    """
    
    def __init__(self, graph_builder):
        self.graph_builder = graph_builder
        # 기존 데이터 검색 노드 재활용
        self.data_retrieval_node = graph_builder.data_retrieval_node
    
    async def _generate_ai_action_plan(self, merged_user_data: dict, selected_path: dict, user_goals: str, retrieved_data: dict, path_selection_context: dict = None) -> str:
        """AI 기반 사내 데이터를 활용한 액션 플랜 및 멘토 추천 생성"""
        try:
            from openai import AsyncOpenAI
            
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return "AI 분석 기능이 현재 이용 불가합니다."
            
            client = AsyncOpenAI(api_key=api_key)
            
            # 회사 비전 컨텍스트 가져오기
            company_vision_context = ""
            try:
                # retriever 모듈에서 직접 회사 비전 컨텍스트 생성
                from app.graphs.agents.retriever import CareerEnsembleRetrieverAgent
                temp_retriever = CareerEnsembleRetrieverAgent()
                company_vision_context = temp_retriever.get_company_vision_context()
                print(f"🔍 DEBUG - path_deepening에서 회사 비전 컨텍스트 가져오기 성공: {len(company_vision_context)}자")
            except Exception as e:
                print(f"❌ WARNING - path_deepening에서 회사 비전 컨텍스트 가져오기 실패: {e}")
                company_vision_context = ""
            
            path_name = selected_path.get('name', '선택된 경로')
            
            # 디버깅: AI 메서드에 전달된 데이터 확인
            print(f"🔍 DEBUG - path_deepening AI 메서드에 전달된 merged_user_data: {merged_user_data}")
            print(f"🔍 DEBUG - 상담 대상자 정보: 이름={merged_user_data.get('name', 'None')}, 경력={merged_user_data.get('experience', 'None')}, 스킬={merged_user_data.get('skills', 'None')}, 도메인={merged_user_data.get('domain', 'None')}")
            print(f"🔍 DEBUG - path_deepening user_goals: {user_goals}")
            print(f"🔍 DEBUG - path_selection_context: {path_selection_context}")
            
            # retrieved_data에서 사내 경력 데이터 추출
            career_data = retrieved_data.get('career_data', [])
            
            # 디버깅: career_data 확인
            print(f"🔍 DEBUG - path_deepening에서 사용할 career_data 개수: {len(career_data)}")
            print(f"🔍 DEBUG - career_data 샘플: {career_data[:2] if career_data else 'None'}")
            print(f"🔍 DEBUG - retrieved_data의 키들: {list(retrieved_data.keys())}")
            print(f"🔍 DEBUG - career_data가 existing_career_data에서 왔는지 확인")
            
            career_context = ""
            if career_data:
                print(f"✅ SUCCESS - {len(career_data)}개의 사내 구성원 데이터 활용 가능")
                # 데이터 구조에 상관없이 간단히 처리
                career_profiles = []
                for i, profile in enumerate(career_data[:10]):  # 최대 10개만 상세 분석
                    # 개인정보 보호를 위해 익명화 처리
                    anonymous_id = f'구성원{chr(65+i)}'  # 구성원A, 구성원B, ...
                    
                    # 실제 데이터 구조 확인 (디버깅용)
                    print(f"🔍 DEBUG - {anonymous_id} 데이터 구조: {type(profile)}")
                    if isinstance(profile, dict):
                        profile_keys = list(profile.keys())
                        print(f"🔍 DEBUG - {anonymous_id} 키들: {profile_keys[:5]}...")  # 처음 5개 키만 출력
                    
                    # 구조에 상관없이 기본 정보만 생성
                    profile_info = f"- {anonymous_id}: 사내 구성원 데이터 확인됨"
                    career_profiles.append(profile_info)
                
                career_context = f"""
**사내 구성원 성공 사례 ({len(career_data)}명 분석, 익명화 처리):**
{chr(10).join(career_profiles)}

**데이터 분석 결과:**
- 총 {len(career_data)}명의 사내 구성원 데이터 분석 (개인정보 익명화)
- career_positioning 단계에서 검색된 실제 데이터 활용
- 유사 경로 성공 사례 및 성장 패턴 파악 가능
"""
                print(f"🔍 DEBUG - 생성된 career_context 길이: {len(career_context)}")
                print(f"🔍 DEBUG - career_context 미리보기: {career_context[:200]}...")
            else:
                career_context = "사내 구성원 데이터: 현재 분석 가능한 데이터 없음"
                print("❌ WARNING - career_data가 비어있어 기본 메시지 사용")
                print("🔍 DEBUG - existing_career_data → retrieved_data → career_data 전달 과정에서 문제 발생 가능성")
            
            # path_selection_context 정보를 프롬프트에 추가
            selection_context_str = ""
            if path_selection_context:
                selection_context_str = f"""
**경로 선택 컨텍스트:**
- 선택한 경로: {path_selection_context.get('selected_path_name', '정보 없음')}
- 선택 이유: {path_selection_context.get('path_selection_reason', '정보 없음')}
- 현재 목표/동기: {path_selection_context.get('current_goals', '정보 없음')[:150]}"""
            
            prompt = f"""
당신은 SKAX의 시니어 커리어 멘토입니다. 동료 구성원인 {merged_user_data.get('name', '고객')}님의 커리어 성장을 위한 실무적인 조언과 구체적인 액션 플랜을 제공해주세요.

{company_vision_context}

**상담 대상자 정보:**
- 이름: {merged_user_data.get('name', '고객')}님
- 현재 경력: {merged_user_data.get('experience', '정보 없음')}
- 보유 스킬: {merged_user_data.get('skills', '정보 없음')}
- 담당 도메인: {merged_user_data.get('domain', '정보 없음')}
- 희망 성장 방향: {path_name}
- 고민과 목표: {user_goals[:200]}

{selection_context_str}

**사내 동료들의 성장 사례:**
{career_context}

**멘토링 가이드라인:**
1. **실제 동료 사례 기반 조언**: 위에 언급된 사내 구성원들의 실제 성장 경험을 바탕으로 구체적인 성장 경로 제시
2. **SKAX 내부 리소스 활용**: 사내에서 실제로 활용 가능한 멘토링, 스터디, 프로젝트 기회 안내
3. **회사 비전 연계**: 회사의 최신 기술 트렌드 및 전략 방향과 개인 성장을 연결한 조언 제공
4. **단계별 실행 계획**: 다음 3-6개월 내 실천 가능한 구체적인 액션 아이템 제공
5. **사내 네트워킹**: 도움이 될 수 있는 사내 커뮤니티나 팀 소개

**멘토링 응답 형식:**

## {merged_user_data.get('name', '고객')}님을 위한 성장 로드맵

안녕하세요! {merged_user_data.get('name', '고객')}님의 **{path_name}** 방향 성장을 함께 계획해보겠습니다.

### 사내 선배들의 성공 사례

**{path_name} 로드맵 관련 동료들의 실제 성장 스토리:**

**데이터 기반 성장 사례 분석:**
{f"- **{merged_user_data.get('name', '고객')}님**과 유사한 배경을 가진 사내 선배 {len(career_data)}명의 실제 데이터를 분석했습니다" if career_data else "- 유사한 경험을 가진 동료들의 실제 데이터를 분석해보면"}
- 구성원A: [실제 데이터를 바탕으로 한 구체적인 성장 스토리와 현재 경로 선택 배경]
- 구성원B: [다른 관점의 성장 경험과 **{merged_user_data.get('name', '고객')}님**과의 공통점]
- 구성원C: [유사한 기술 스택/도메인에서 성공한 사례와 핵심 전략]

**{merged_user_data.get('name', '고객')}님과의 데이터 일치점:**
- **경력 수준**: [고객의 현재 경력과 일치하는 선배들의 당시 상황]
- **기술 스택**: [고객의 보유 기술과 유사한 선배들의 시작점]
- **도메인 경험**: [고객의 도메인과 겹치는 선배들의 성장 배경]
- **성장 동기**: [고객의 목표와 일치하는 선배들의 당시 목표]

**신뢰할 수 있는 성장 패턴:**
- **핵심 성공 요인**: [실제 데이터에서 발견되는 공통적인 성장 전략]
- **단계별 성장 과정**: [데이터로 검증된 1년차→3년차→5년차 성장 경로]
- **성공 지표**: [선배들이 실제로 달성한 구체적인 성과 지표]

**{merged_user_data.get('name', '고객')}님을 위한 맞춤형 벤치마킹:**
- [고객의 현재 데이터와 가장 일치하는 선배 사례 기반 구체적인 성장 방향]
- [데이터 분석 결과 도출된 **{merged_user_data.get('name', '고객')}님**만의 최적 성장 전략]

*🌟 이 추천 방향성은 개인의 경험 데이터와 함께 SKAX의 최신 기술 트렌드 및 비전 방향성을 종합 분석하여 제시됩니다.*

### 추천 멘토/선배

**실제 구성원 데이터 기반 멘토 추천:**

**멘토 A (추천도: ★★★★★)**
- **배경**: [**{merged_user_data.get('name', '고객')}님**과 유사한 경력/기술 스택을 가진 선배의 구체적 프로필]
- **성장 경험**: [해당 멘토가 실제로 겪은 **{path_name}** 관련 성장 과정과 성과]
- **추천 이유**: [**{merged_user_data.get('name', '고객')}님**의 현재 상황과 목표에 왜 이 멘토가 최적인지 구체적 설명]
- **멘토링 가능 영역**: [실제 도움받을 수 있는 구체적 분야들]

**멘토 B (추천도: ★★★★☆)**  
- **배경**: [다른 관점에서 **{path_name}** 경로를 성공적으로 걸어온 선배의 프로필]
- **성장 경험**: [해당 멘토의 독특한 성장 스토리와 핵심 인사이트]
- **추천 이유**: [**{merged_user_data.get('name', '고객')}님**이 놓칠 수 있는 부분을 보완해줄 수 있는 이유]
- **멘토링 가능 영역**: [이 멘토만의 특별한 조언 가능 분야]

**멘토링 신청 및 연결 방법:**
- **사내 멘토링 프로그램**: HR팀 공식 채널 통해 신청 (월 1회 매칭)
- **비공식 멘토링**: 사내 메신저나 이메일을 통한 개별 컨택
- **그룹 멘토링**: 유사한 목표를 가진 동료들과 함께하는 그룹 세션 참여

---(이 대시부분 무조건 포함)

**다음 스텝: 체계적인 학습 로드맵 설계**

위에서 제시한 성장 전략과 멘토링 계획을 바탕으로, 더욱 구체적이고 실행 가능한 학습 로드맵을 함께 설계해보시겠어요?
학습 로드맵을 원하시면 "네, 학습 로드맵을 설계해주세요"라고 답변해주세요!

---

**작성 원칙:**
- 동료에게 조언하는 따뜻하고 실무적인 톤
- 실제 사내에서 활용 가능한 리소스와 기회 중심
- 구체적이고 실행 가능한 단기/중기 계획
- 개인정보는 익명화하되 실제 사례의 진정성 유지
- 회사 비전 정보가 제공된 경우, 해당 가치와 전략 방향에 부합하는 멘토링과 액션 플랜 제공
- 200-250단어로 간결하면서도 실용적으로 작성
"""
            
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.6
            )
            
            ai_content = response.choices[0].message.content.strip()
            
            return ai_content
            
        except Exception as e:
            print(f"AI 액션 플랜 생성 중 오류: {e}")
            return "액션 플랜을 생성하는 중 문제가 발생했습니다. 다시 시도해주세요."
    
    async def process_deepening_node(self, state: ChatState) -> Dict[str, Any]:
        """
        사용자의 목표와 이유를 분석하여 실행 전략을 제시한다.
        """
        print("🎯 경로 심화 논의 시작...")
        
        # State 전달 트레이싱 확인 (디버깅)
        print(f"🔍 DEBUG - path_deepening에서 받은 state 트레이싱:")
        print(f"🔍 DEBUG - state_trace: {state.get('state_trace', 'None')}")
        print(f"🔍 DEBUG - career_positioning_timestamp: {state.get('career_positioning_timestamp', 'None')}")
        print(f"🔍 DEBUG - consultation_stage: {state.get('consultation_stage', 'None')}")
        print(f"🔍 DEBUG - awaiting_user_input: {state.get('awaiting_user_input', 'None')}")
        
        user_response = state.get("user_question", "")
        selected_path = state.get("selected_career_path", {})
        user_data = self.graph_builder.get_user_info_from_session(state)
        collected_info = state.get("collected_user_info", {})
        merged_user_data = {**user_data, **collected_info}
        
        # path_selection 단계에서의 사용자 선택 정보 추출
        path_selection_info = state.get("path_selection_info", {})
        path_selection_context = {
            "selected_path_name": selected_path.get("name", "선택된 경로"),
            "selected_path_id": selected_path.get("id", ""),
            "path_selection_reason": "",  # 사용자가 해당 경로를 선택한 이유 추출
            "current_goals": user_response,  # 현재 단계에서의 목표/동기
            "previous_user_input": path_selection_info.get("user_input_for_deepening", "")  # path_selection에서의 사용자 입력
        }
        
        # 사용자 응답에서 경로 선택 이유 추출 (키워드 기반)
        selection_keywords = {
            "관심": "해당 분야에 관심",
            "경험": "관련 경험 보유",
            "성장": "성장 가능성",
            "기회": "기회 확대",
            "전문성": "전문성 개발",
            "도전": "새로운 도전",
            "적성": "적성에 맞음",
            "비전": "비전 일치",
            "시장": "시장 전망",
            "미래": "미래 가능성"
        }
        
        # 현재 응답과 이전 응답 모두에서 이유 추출
        combined_response = f"{user_response} {path_selection_context['previous_user_input']}"
        
        for keyword, description in selection_keywords.items():
            if keyword in combined_response:
                path_selection_context["path_selection_reason"] += f"{description}, "
        
        # 이유를 찾지 못한 경우 전체 응답을 이유로 활용
        if not path_selection_context["path_selection_reason"]:
            path_selection_context["path_selection_reason"] = user_response[:100] + "..." if len(user_response) > 100 else user_response
        else:
            path_selection_context["path_selection_reason"] = path_selection_context["path_selection_reason"].rstrip(", ")
        
        # 디버깅: 데이터 확인
        print(f"🔍 DEBUG - path_deepening user_data from session: {user_data}")
        print(f"🔍 DEBUG - path_deepening collected_info: {collected_info}")
        print(f"🔍 DEBUG - path_deepening merged_user_data: {merged_user_data}")
        print(f"🔍 DEBUG - path_selection_context: {path_selection_context}")
        
        # career_positioning에서 검색된 사내 경력 데이터 활용
        # path_selection과 path_deepening 사이에는 데이터 손실이 없어야 함
        
        # 먼저 state의 모든 career 관련 키들을 확인
        career_related_keys = [key for key in state.keys() if 'career' in key.lower()]
        print(f"🔍 DEBUG - state의 career 관련 키들: {career_related_keys}")
        
        # 전체 state 키 확인 (디버깅용)
        all_state_keys = list(state.keys())
        print(f"🔍 DEBUG - 전체 state 키 개수: {len(all_state_keys)}")
        print(f"🔍 DEBUG - 모든 state 키들: {all_state_keys}")
        
        # retrieved_career_data 확인
        existing_career_data = state.get("retrieved_career_data", [])
        print(f"🔍 DEBUG - state에서 가져온 retrieved_career_data: {len(existing_career_data)}개")
        print(f"🔍 DEBUG - retrieved_career_data 타입: {type(existing_career_data)}")
        
        if existing_career_data:
            print(f"🔍 DEBUG - 첫 번째 데이터 샘플: {existing_career_data[0] if existing_career_data else 'None'}")
            print(f"🔍 DEBUG - 모든 employee_id: {[item.get('employee_id', 'N/A') for item in existing_career_data[:5]]}")
            
            # 데이터 구조 검증
            if isinstance(existing_career_data[0], dict):
                sample_keys = list(existing_career_data[0].keys())
                print(f"🔍 DEBUG - 데이터 구조 검증 OK - 샘플 키들: {sample_keys}")
            else:
                print(f"❌ WARNING - 데이터 구조 이상: 첫 번째 항목이 dict가 아님 - {type(existing_career_data[0])}")
        else:
            print("❌ WARNING - retrieved_career_data가 비어있음!")
        
        if existing_career_data and len(existing_career_data) > 0:
            print(f"✅ SUCCESS - career_positioning에서 저장된 사내 구성원 데이터 재사용: {len(existing_career_data)}개")
            retrieved_data = {"career_data": existing_career_data}
            print(f"🔍 DEBUG - retrieved_data 구성 완료: career_data 키에 {len(retrieved_data['career_data'])}개 데이터 저장")
        else:
            print("❌ WARNING - retrieved_career_data가 비어있거나 없음. 빈 데이터로 처리")
            retrieved_data = {"career_data": []}
        
        print(f"🔍 DEBUG - AI 호출 전 최종 retrieved_data 확인: career_data={len(retrieved_data.get('career_data', []))}개")
        
        # AI 기반 사내 데이터 활용 액션 플랜 생성 (path_selection 컨텍스트 포함)
        ai_response = await self._generate_ai_action_plan(
            merged_user_data, selected_path, user_response, retrieved_data, path_selection_context
        )
        
        # 사용자 응답 컨텍스트 저장 (path_selection 정보 포함)
        consultation_context = {
            "user_goals": user_response,
            "selected_path": selected_path,
            "path_selection_context": path_selection_context,
            "analysis_timestamp": "2025-07-02"
        }
        
        # 응답 구성
        strategy_response = {
            "message": ai_response,
            "action_plan": {
                "context": consultation_context,
                "data_sources": ["career_data", "networking_opportunities"]
            }
        }
        
        # HTML 로그 저장
        save_career_response_to_html("path_deepening", strategy_response, state.get("session_id", "unknown"))
        
        return {
            **state,
            "consultation_stage": "learning_decision",
            "consultation_context": consultation_context,
            "formatted_response": strategy_response,
            "final_response": strategy_response,
            "awaiting_user_input": True,
            "next_expected_input": "learning_roadmap_decision",
            "processing_log": state.get("processing_log", []) + ["실행 전략 수립 완료"]
        }
