# app/graphs/nodes/career_consultation/learning_roadmap.py
"""
학습 로드맵 설계 노드
AI 기반 맞춤형 학습 계획 생성 (사내 교육과정 추천 포함)
"""

import os
from typing import Dict, Any
from app.graphs.state import ChatState
from app.utils.html_logger import save_career_response_to_html


class LearningRoadmapNode:
    """
    AI 기반 학습 로드맵 설계 노드
    """
    
    def __init__(self, graph_builder):
        self.graph_builder = graph_builder
        # 교육과정 검색 기능 활용
        self.data_retrieval_node = graph_builder.data_retrieval_node
    
    async def _generate_ai_learning_roadmap(self, merged_user_data: dict, selected_path: dict, user_goals: str, education_data: dict) -> Dict[str, Any]:
        """AI 기반 개인 맞춤형 학습 로드맵 생성"""
        try:
            from openai import AsyncOpenAI
            
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return {
                    "message": "학습 로드맵 생성 기능이 현재 이용 불가합니다.",
                    "learning_resources": {}
                }
            
            client = AsyncOpenAI(api_key=api_key)
            
            path_name = selected_path.get('name', '선택된 경로')
            
            # 교육과정 데이터 추출
            mysuni_courses = education_data.get('mysuni_courses', [])
            college_courses = education_data.get('college_courses', [])
            
            print(f"🔍 DEBUG - AI 프롬프트용 mySUNI 과정: {len(mysuni_courses)}개")
            print(f"🔍 DEBUG - AI 프롬프트용 College 과정: {len(college_courses)}개")
            
            education_context = ""
            if mysuni_courses or college_courses:
                # 교육과정 정보를 하이퍼링크 포함하여 구조화
                mysuni_info = ""
                if mysuni_courses:
                    mysuni_sample = mysuni_courses[:5]  # 처음 5개만 샘플로 표시
                    # 첫 번째 과정의 데이터 구조 확인을 위한 디버깅
                    if mysuni_sample:
                        print(f"🔍 DEBUG - mySUNI 첫 번째 과정 데이터 구조: {mysuni_sample[0].keys()}")
                        print(f"🔍 DEBUG - mySUNI 첫 번째 과정 샘플: {mysuni_sample[0]}")
                    
                    # URL이 있는 경우 마크다운 링크 형식으로 생성
                    mysuni_formatted = []
                    for course in mysuni_sample:
                        # 여러 필드에서 과정명을 찾아서 추출
                        course_name = (
                            course.get('title') or 
                            course.get('name') or 
                            course.get('course_name') or 
                            course.get('course_title') or
                            course.get('content_title') or
                            course.get('subject') or
                            '과정명 미확인'
                        )
                        course_url = course.get('url', course.get('link', ''))
                        
                        # 과정명이 비어있거나 None인 경우 처리
                        if not course_name or course_name.strip() == '':
                            course_name = '과정명 미확인'
                        
                        # 디버깅: 과정명 추출 결과 확인
                        print(f"🔍 DEBUG - mySUNI 과정명 추출 결과: '{course_name}' (URL: {course_url})")
                        
                        if course_url:
                            mysuni_formatted.append(f"[{course_name}]({course_url})")
                        else:
                            mysuni_formatted.append(course_name)
                    mysuni_info = f"mySUNI 과정 ({len(mysuni_courses)}개 검색됨): " + ", ".join(mysuni_formatted)
                
                college_info = ""
                if college_courses:
                    college_sample = college_courses[:5]  # 처음 5개만 샘플로 표시
                    # 첫 번째 과정의 데이터 구조 확인을 위한 디버깅
                    if college_sample:
                        print(f"🔍 DEBUG - College 첫 번째 과정 데이터 구조: {college_sample[0].keys()}")
                        print(f"🔍 DEBUG - College 첫 번째 과정 샘플: {college_sample[0]}")
                    
                    # URL이 있는 경우 마크다운 링크 형식으로 생성
                    college_formatted = []
                    for course in college_sample:
                        # 여러 필드에서 과정명을 찾아서 추출
                        course_name = (
                            course.get('title') or 
                            course.get('name') or 
                            course.get('course_name') or 
                            course.get('course_title') or
                            course.get('content_title') or
                            course.get('subject') or
                            '과정명 미확인'
                        )
                        course_url = course.get('url', course.get('link', ''))
                        
                        # 과정명이 비어있거나 None인 경우 처리
                        if not course_name or course_name.strip() == '':
                            course_name = '과정명 미확인'
                        
                        # 디버깅: 과정명 추출 결과 확인
                        print(f"🔍 DEBUG - College 과정명 추출 결과: '{course_name}' (URL: {course_url})")
                        
                        if course_url:
                            college_formatted.append(f"[{course_name}]({course_url})")
                        else:
                            college_formatted.append(course_name)
                    college_info = f"College 과정 ({len(college_courses)}개 검색됨): " + ", ".join(college_formatted)
                
                education_context = f"""
**SKAX 사내 교육과정 정보 (총 15개씩 검색):**

{mysuni_info}

{college_info}

**검색 결과 요약:**
- 총 mySUNI 과정: {len(mysuni_courses)}개
- 총 College 과정: {len(college_courses)}개
- 사용자 경로({path_name})에 적합한 과정들을 위 목록에서 선별하여 추천해주세요.

**중요: 위에 제시된 교육과정 중 URL이 포함된 과정들은 반드시 [과정명](URL) 형식의 마크다운 하이퍼링크로 추천해주세요.**
"""
                print(f"🔍 DEBUG - 생성된 education_context 길이: {len(education_context)}")
            else:
                education_context = "사내 교육과정 검색 결과: 현재 이용 가능한 과정이 없습니다."
                print("❌ WARNING - 교육과정 데이터가 없어 기본 메시지 사용")
            
            print(f"🔍 DEBUG - learning_roadmap AI 메서드에 전달된 merged_user_data: {merged_user_data}")
            print(f"🔍 DEBUG - education_context 미리보기: {education_context[:300]}...")
            
            prompt = f"""
당신은 G.Navi의 전문 학습 설계사입니다. {merged_user_data.get('name', '고객')}님의 **{path_name}** 경로 달성을 위한 맞춤형 학습 로드맵을 설계해주세요.

**사용자 프로필:**
- 이름: {merged_user_data.get('name', '고객')}
- 경력: {merged_user_data.get('experience', '정보 없음')}
- 보유 기술: {', '.join(merged_user_data.get('skills', ['정보 없음'])) if merged_user_data.get('skills') and merged_user_data.get('skills') != ['정보 없음'] else '정보 없음'}
- 도메인: {merged_user_data.get('domain', '정보 없음')}
- 목표 경로: {path_name}
- 사용자 목표: {user_goals[:200]}

{education_context}

**응답 형식 (반드시 마크다운 문법을 사용하여 작성):**

## 학습 로드맵 설계

안녕하세요! **{merged_user_data.get('name', '고객')}님**의 개인 데이터와 사내 데이터를 기반으로 **{path_name}** 성장 방향을 계획해보겠습니다.

### 학습 우선순위 및 순서

**핵심 학습 영역 (우선순위 순):**
1. **[첫 번째 영역]** - [간단한 이유와 예상 기간]
2. **[두 번째 영역]** - [간단한 이유와 예상 기간] 
3. **[세 번째 영역]** - [간단한 이유와 예상 기간]

### 사내 교육과정 추천

**SKAX mySUNI 추천 과정:**
- [검색된 mySUNI 과정 중에서 사용자에게 가장 적합한 과정 1-3개를 [과정명](URL) 형식의 하이퍼링크로 추천 및 이유]

**SKAX College 추천 과정:**
- [검색된 College 과정 중에서 사용자에게 가장 적합한 과정 1-3개를 [과정명](URL) 형식의 하이퍼링크로 추천 및 이유]

### 학습 실행 계획

**1-3개월 (기초 구축)**
- [구체적인 학습 활동과 목표]

**4-6개월 (실무 적용)**
- [구체적인 학습 활동과 목표]

--- (이 대시 부분 무조건 포함)
** 다음 단계 : 상담 종합 및 마무리 ** 

**{merged_user_data.get('name', '고객')}님**의 맞춤형 학습 로드맵을 제시해드렸습니다!
오늘 상담을 마무리하시려면 "네" 라고 말씀해주세요!

**성공적인 커리어 성장을 응원합니다! 🚀**

**작성 지침:**
- 반드시 마크다운 문법 사용 (## 제목, ### 소제목, **굵은글씨**, - 리스트)
- 인사말 없이 바로 "## 학습 로드맵 설계"로 시작
- 전체 250-300단어 내외로 간결하고 실용적으로 작성
- 사내 교육과정을 구체적으로 활용한 추천 제공
- 실무에 바로 적용 가능한 구체적인 내용으로 구성
- 우선순위가 명확한 학습 순서 제시
- **교육과정 추천 시 URL이 있는 경우 반드시 [과정명](URL) 형식의 마크다운 하이퍼링크로 작성**
- 하이퍼링크가 클릭 가능하도록 정확한 마크다운 문법 사용
- 마지막에 상담 정리를 위한 유도 질문 포함
"""
            
            # --- 인사말 없이 바로 시작하도록 명확히 안내 ---
            prompt += """

**중요:** 아래 학습 로드맵 응답은 '안녕하세요' 등 인사말 없이 바로 '## 학습 로드맵 설계'로 시작하세요. 첫 문장은 반드시 분석/제안/계획 요약으로 시작해야 합니다.

"""
            
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10000,
                temperature=0.4
            )
            
            ai_content = response.choices[0].message.content.strip()
            
            return {
                "message": ai_content,
                "learning_resources": {
                    "mysuni_courses": mysuni_courses[:10] if mysuni_courses else [],
                    "college_courses": college_courses[:10] if college_courses else [],
                    "focus_areas": ["기초 구축", "실무 적용", "전문성 강화"]
                }
            }
            
        except Exception as e:
            print(f"AI 학습 로드맵 생성 중 오류: {e}")
            return {
                "message": "학습 로드맵을 생성하는 중 문제가 발생했습니다. 다시 시도해주세요.",
                "learning_resources": {}
            }
    
    async def create_learning_roadmap_node(self, state: ChatState) -> Dict[str, Any]:
        """
        사용자 맞춤형 학습 로드맵을 설계한다.
        """
        print("📚 학습 로드맵 설계 시작...")
        
        user_response = state.get("user_question", "").lower()
        selected_path = state.get("selected_career_path", {})
        user_data = self.graph_builder.get_user_info_from_session(state)
        collected_info = state.get("collected_user_info", {})
        merged_user_data = {**user_data, **collected_info}
        
        # path_deepening_info에서 정보 추출
        path_deepening_info = state.get("path_deepening_info", {})
        path_deepening_message = path_deepening_info.get("message", "")
        action_plan_info = path_deepening_info.get("action_plan", {})
        consultation_context = action_plan_info.get("context", {})
        user_goals = consultation_context.get("user_goals", "")
        
        # 디버깅: 데이터 확인
        print(f"🔍 DEBUG - learning_roadmap user_data from session: {user_data}")
        print(f"🔍 DEBUG - learning_roadmap collected_info: {collected_info}")
        print(f"🔍 DEBUG - learning_roadmap merged_user_data: {merged_user_data}")
        print(f"🔍 DEBUG - path_deepening_info 내용 확인: {path_deepening_info.keys() if path_deepening_info else 'None'}")
        
        # path_deepening 정보를 활용한 검색 쿼리 생성
        search_query = ""
        if path_deepening_message:
            # 메시지에서 핵심 키워드 추출 (최대 100자)
            search_query += path_deepening_message[:100]
        
        if user_goals:
            # 사용자 목표 정보 추가
            search_query += " " + user_goals[:100]
        
        if selected_path:
            # 선택한 경로 정보 추가
            path_name = selected_path.get("name", "")
            search_query += " " + path_name
        
        # 검색 쿼리가 비어있으면 사용자 응답을 폴백으로 사용
        if not search_query.strip():
            search_query = user_response
        
        print(f"🔍 DEBUG - 생성된 교육과정 검색 쿼리: '{search_query[:100]}...'")
        
        # 학습 로드맵 요청 여부 확인 (더 포괄적으로 개선)
        roadmap_keywords = [
            "네", "yes", "학습", "로드맵", "교육", "과정", "공부", "배우", "강의", 
            "커리큘럼", "스킬", "능력", "역량", "개발", "향상", "성장", "추천",
            "원해", "달라", "받고", "싶어", "필요", "해줘", "부탁", "요청"
        ]
        
        # 거부 키워드도 확인
        rejection_keywords = ["아니", "안", "필요없", "싫어", "거부", "skip", "생략", "패스"]
        
        wants_roadmap = any(keyword in user_response for keyword in roadmap_keywords)
        rejects_roadmap = any(keyword in user_response for keyword in rejection_keywords)
        
        print(f"🔍 DEBUG - 사용자 응답: '{user_response}'")
        print(f"🔍 DEBUG - 학습 로드맵 요청 감지: {wants_roadmap}")
        print(f"🔍 DEBUG - 학습 로드맵 거부 감지: {rejects_roadmap}")
        
        # 로드맵 요청 키워드 매칭 상세 디버깅
        matched_keywords = [keyword for keyword in roadmap_keywords if keyword in user_response]
        rejected_keywords = [keyword for keyword in rejection_keywords if keyword in user_response]
        print(f"🔍 DEBUG - 매칭된 요청 키워드: {matched_keywords}")
        print(f"🔍 DEBUG - 매칭된 거부 키워드: {rejected_keywords}")
        
        # 기본적으로 path_deepening 이후에는 학습 로드맵을 제공하도록 설정
        consultation_stage = state.get("consultation_stage", "")
        if consultation_stage == "learning_decision":
            if rejects_roadmap:
                print("🔍 DEBUG - 사용자가 명시적으로 학습 로드맵을 거부함")
                wants_roadmap = False
            elif not wants_roadmap:
                print("🔍 DEBUG - consultation_stage가 learning_decision이므로 기본적으로 학습 로드맵 제공")
                wants_roadmap = True
        
        if wants_roadmap:
            # 사내 교육과정 데이터 검색 (mySUNI, College 각각 15개씩)
            print("🔍 DEBUG - 교육과정 검색 시작...")
            print(f"🔍 DEBUG - 현재 state의 키들: {list(state.keys())}")
            
            # 교육과정 검색 개수를 15로 설정
            state["education_search_count"] = 15
            print(f"🔍 DEBUG - education_search_count 설정: {state['education_search_count']}")
            
            # 원래 쿼리 저장
            original_question = state.get("user_question", "")
            
            # path_deepening 기반 검색 쿼리로 임시 대체
            state["user_question"] = search_query
            
            # 데이터 검색 노드 호출
            print("🔍 DEBUG - data_retrieval_node.retrieve_additional_data_node 호출 중...")
            state = self.data_retrieval_node.retrieve_additional_data_node(state)
            print("🔍 DEBUG - data_retrieval_node 호출 완료")
            
            # 원래 쿼리 복원
            state["user_question"] = original_question
            
            # 교육과정 데이터 추출
            education_courses_raw = state.get("education_courses", {})
            print(f"🔍 DEBUG - state에서 가져온 education_courses: {type(education_courses_raw)}")
            print(f"🔍 DEBUG - education_courses 키들: {list(education_courses_raw.keys()) if isinstance(education_courses_raw, dict) else 'dict가 아님'}")
            
            # CareerEnsembleRetrieverAgent에서 반환하는 구조: {"recommended_courses": [], "course_analysis": {}, "learning_path": []}
            recommended_courses = education_courses_raw.get("recommended_courses", []) if isinstance(education_courses_raw, dict) else []
            
            # 교육과정을 소스별로 분류
            mysuni_courses = []  # mySUNI 과정 목록
            college_courses = []  # College 과정 목록
            
            # 과정별 소스 분류 작업
            for course in recommended_courses:  # 추천 과정 목록 순회
                course_source = course.get("source", "").lower()  # 소스 정보 추출
                if "mysuni" in course_source:  # mySUNI 과정인지 확인
                    mysuni_courses.append(course)  # mySUNI 목록에 추가
                elif "college" in course_source:  # College 과정인지 확인
                    college_courses.append(course)  # College 목록에 추가
                # end if (소스 타입 확인)
            # end for (추천 과정 목록 순회)
            
            # 교육과정 데이터 구조 생성
            education_data = {
                "mysuni_courses": mysuni_courses,
                "college_courses": college_courses
            }
            
            # 디버깅: 검색된 교육과정 개수 및 샘플 확인
            print(f"🔍 DEBUG - 전체 검색된 과정 개수: {len(recommended_courses)}")
            print(f"🔍 DEBUG - 분류된 mySUNI 과정 개수: {len(education_data['mysuni_courses'])}")
            print(f"🔍 DEBUG - 분류된 College 과정 개수: {len(education_data['college_courses'])}")
            
            # 검색 결과 샘플 출력
            if recommended_courses:  # 검색 결과가 존재하는지 확인
                print(f"🔍 DEBUG - 첫 번째 과정 샘플: {recommended_courses[0]}")
                print(f"🔍 DEBUG - mySUNI 샘플: {education_data['mysuni_courses'][:2] if education_data['mysuni_courses'] else 'None'}")
                print(f"🔍 DEBUG - College 샘플: {education_data['college_courses'][:2] if education_data['college_courses'] else 'None'}")
            # end if (검색 결과 존재 확인)
            
            # 교육과정 데이터 검증
            if not education_data['mysuni_courses'] and not education_data['college_courses']:  # 교육과정이 없는 경우 확인
                if not recommended_courses:  # 전체 추천 과정이 없는 경우
                    print("❌ WARNING - 교육과정 데이터가 비어있음. 검색 과정에서 문제 발생 가능성")
                else:  # 추천 과정은 있지만 분류되지 않은 경우
                    print("❌ WARNING - 검색된 과정이 있지만 mySUNI/College로 분류되지 않음. source 필드 확인 필요")
                # end if (추천 과정 존재 여부 확인)
            else:  # 교육과정 데이터가 있는 경우
                print(f"✅ SUCCESS - 총 {len(education_data['mysuni_courses']) + len(education_data['college_courses'])}개의 교육과정 데이터 확보")
            # end if (교육과정 데이터 검증)
            
            # AI 기반 학습 로드맵 생성 호출
            roadmap_result = await self._generate_ai_learning_roadmap(
                merged_user_data, selected_path, search_query, education_data
            )  # AI 로드맵 생성 메서드 호출에 search_query 전달
            
            # 학습 로드맵 응답 구성
            roadmap_response = {
                "message": roadmap_result["message"],
                "learning_resources": roadmap_result["learning_resources"]
            }
        else:  # 학습 로드맵을 원하지 않는 경우
            # 학습 로드맵 생략 시 consultation_summary 단계로 이동
            roadmap_response = {
                "message": f"""## 실행 중심 접근

**{merged_user_data.get('name', '고객')}님**께서는 즉시 실행에 집중하기로 하셨습니다. 이제 오늘 상담의 핵심 내용을 정리해드리겠습니다.""",
                "learning_resources": {
                    "focus": "execution_over_learning"
                }
            }
        # end if (학습 로드맵 요청 여부)
        
        # HTML 로그 저장 수행
        save_career_response_to_html("learning_roadmap", roadmap_response, state.get("session_id", "unknown"))  # HTML 로그 저장 함수 호출

        # 학습 로드맵 처리 후 상담 단계 설정
        if wants_roadmap:  # 학습 로드맵을 제공한 경우
            # 학습 로드맵을 제공한 후 사용자 피드백 대기
            next_stage = "summary_request"  # 상담 요약 요청 단계
            awaiting_input = True  # 사용자 입력 대기 상태
            next_expected = "summary_feedback"  # 요약 피드백 단계
        else:  # 학습 로드맵을 생략한 경우
            # 학습 로드맵을 생략한 경우 - consultation_summary 단계로 이동
            next_stage = "summary_request"  # 상담 요약 요청 단계
            awaiting_input = True  # 사용자 입력 대기 상태
            next_expected = "summary_feedback"  # 요약 피드백 단계
        # end if (학습 로드맵 제공 여부에 따른 단계 설정)
 
        # learning_roadmap_info에 결과 저장 (반환 딕셔너리에도 명시적으로 포함)
        return {
            **state,
            "consultation_stage": next_stage,
            "formatted_response": roadmap_response,
            "final_response": roadmap_response,
            "learning_roadmap_info": roadmap_response,  # 명시적으로 포함
            "awaiting_user_input": awaiting_input,
            "next_expected_input": next_expected,
            "career_consultation_completed": False,
            "processing_log": state.get("processing_log", []) + [
                "학습 로드맵 제공 완료 - 사용자 피드백 대기" if wants_roadmap else "학습 로드맵 생략 - 상담 요약 단계로 이동"
            ]
        }
