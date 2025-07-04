# app/graphs/nodes/career_consultation/user_info_collection.py
"""
사용자 정보 수집 노드
부족한 정보(연차, 기술스택, 도메인)를 사용자로부터 수집
AI 기반 개인화된 질문 생성
"""

import os
from typing import Dict, Any, List
from app.graphs.state import ChatState
from app.utils.html_logger import save_career_response_to_html


class UserInfoCollectionNode:
    """
    사용자 정보 수집 노드
    """
    
    def __init__(self, graph_builder):
        self.graph_builder = graph_builder
    
    async def _generate_personalized_question(self, field: str, user_name: str, context: str = "") -> str:
        """AI 기반 개인화된 정보 수집 질문 생성"""
        try:
            from openai import AsyncOpenAI
            
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return self._get_info_request_message(field, user_name, is_first_request=True)
            
            client = AsyncOpenAI(api_key=api_key)
            
            field_descriptions = {
                'level': '경력 레벨 정보 (CL1~CL5)',
                'skills': '기술 스택과 역량',
                'domain': '업무 도메인과 전문 분야'
            }
            
            prompt = f"""
커리어 상담사로서 {user_name}님에게 {field_descriptions.get(field, field)} 정보를 수집하는 질문을 작성해주세요.

상황: 전문적인 커리어 상담 세션 진행 중
대상: {user_name}님
필요 정보: {field_descriptions.get(field, field)}
추가 컨텍스트: {context}

다음 요구사항을 만족하는 질문을 작성해주세요:
1. 친근하면서도 전문적인 톤
2. 구체적이고 답변하기 쉬운 형태
3. 100-150단어 이내
4. 예시를 포함하여 답변 가이드 제공

질문만 작성하고 다른 설명은 생략해주세요.
"""
            
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.4
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"개인화 질문 생성 중 오류: {e}")
            return self._get_info_request_message(field, user_name, is_first_request=True)
    
    def _check_missing_info(self, user_data: Dict[str, Any]) -> List[str]:
        """
        사용자 데이터에서 부족한 정보를 확인한다.
        
        @param user_data: 사용자 프로필 데이터
        @return: 부족한 정보 필드 리스트
        """
        missing_fields = []
        print(f'check_missing_info: {user_data}')
        
        # 먼저 중첩된 필드에서 정보를 추출
        if 'projects' in user_data:
            user_data = self._extract_nested_fields(user_data)
            print(f"🔍 중첩 필드 추출 후 user_data: {user_data}")
        
        # 레벨 확인 - CL1~CL5 레벨 정보인지 검증
        level = user_data.get('level')
        print(f"🔍 레벨 체크: level = {level}, type = {type(level)}")
        
        # 레벨 정보가 유효한지 검증 (CL1~CL5 형태)
        is_valid_level = False
        
        if level is not None:
            if isinstance(level, str):
                level_upper = level.upper().strip()
                # CL1~CL5 패턴 확인
                valid_levels = ['CL1', 'CL2', 'CL3', 'CL4', 'CL5']
                is_valid_level = level_upper in valid_levels
                print(f"🔍 레벨 검증: {level} → {level_upper}, 유효: {is_valid_level}")
            
        if not is_valid_level:
            missing_fields.append('level')
            print(f"❌ 레벨 부족 (유효하지 않은 정보: {level})")
        else:
            print(f"✅ 레벨 있음: {level}")
            # 레벨을 연차로 매핑하여 experience 필드에 저장
            user_data['experience'] = self._map_level_to_experience(level)
            print(f"🔍 매핑된 연차: {user_data['experience']}")
        
        # 기술스택 확인  
        skills = user_data.get('skills', [])
        print(f"🔍 스킬 체크: skills = {skills}, type = {type(skills)}, len = {len(skills) if skills else 0}")
        
        # 스킬 데이터가 문자열인 경우 리스트로 변환
        if isinstance(skills, str) and skills.strip():
            skills_list = [skill.strip() for skill in skills.split(',') if skill.strip()]
            print(f"🔍 문자열 스킬을 리스트로 변환: {skills_list}")
            skills = skills_list
        
        if not skills or len(skills) == 0:
            missing_fields.append('skills')
            print(f"❌ 스킬 부족")
        else:
            print(f"✅ 스킬 있음: {skills}")
        
        # 도메인 확인
        domain = user_data.get('domain')
        print(f"🔍 도메인 체크: domain = {domain}, type = {type(domain)}")
        
        # 도메인이 리스트인 경우 첫 번째 값 사용
        if isinstance(domain, list) and len(domain) > 0:
            domain = domain[0]
            print(f"🔍 리스트 도메인의 첫 번째 값 사용: {domain}")
        
        if not domain or (isinstance(domain, str) and domain.strip() == ''):
            missing_fields.append('domain')
            print(f"❌ 도메인 부족")
        else:
            print(f"✅ 도메인 있음: {domain}")
            
        print(f"🔍 최종 부족한 필드: {missing_fields}")
        return missing_fields
    
    def _extract_nested_fields(self, user_data: dict) -> dict:
        """간단한 중첩 필드 추출 (projects의 첫 번째 항목에서만)"""
        if 'projects' not in user_data or not user_data['projects'] or len(user_data['projects']) == 0:
            print(f"🔍 projects가 없거나 비어있음: {user_data.get('projects', 'None')}")
            return user_data
            
        # 첫 번째 프로젝트에서만 정보 추출
        try:
            project = user_data['projects'][0] if isinstance(user_data['projects'], list) else user_data['projects']
            
            if not isinstance(project, dict):
                print(f"🔍 첫 번째 project가 dict가 아님: {type(project)}")
                return user_data
                
            # skills 추출 (최상위에 없을 때만)
            if not user_data.get('skills') and 'skills' in project:
                user_data['skills'] = project['skills']
                print(f"🔍 projects에서 skills 추출: {project['skills']}")
                
            # domain 추출 (최상위에 없을 때만)  
            if not user_data.get('domain') and 'domain' in project:
                user_data['domain'] = project['domain']
                print(f"🔍 projects에서 domain 추출: {project['domain']}")
                
        except (IndexError, KeyError, TypeError) as e:
            print(f"🔍 projects 필드 추출 중 오류 (무시하고 진행): {e}")
            
        return user_data
    
    def _get_info_request_message(self, field: str, user_name: str, is_first_request: bool = True) -> str:
        """
        정보 요청 메시지를 생성한다.
        
        @param field: 요청할 정보 필드
        @param user_name: 사용자 이름  
        @param is_first_request: 첫 번째 요청인지 여부 (True: 상세 메시지, False: 간단 메시지)
        @return: 요청 메시지
        """
        if is_first_request:
            # 첫 번째 요청 시 상세한 메시지
            messages = {
                'level': f"""안녕하세요 {user_name}님! 전문 커리어 컨설팅을 시작하겠습니다.

정확한 분석을 위해 현재 경력 레벨을 확인하겠습니다.

경력 레벨을 알려주세요:

레벨 구분 가이드
- CL1: 1~3년 (주니어 레벨)
- CL2: 4~6년 (중급 레벨)
- CL3: 7~9년 (시니어 레벨)
- CL4: 10~12년 (전문가 레벨)
- CL5: 13년 이상 (리더 레벨)

입력 예시: "CL1", "CL2", "CL3", "CL4", "CL5"

정확한 레벨 정보는 맞춤형 커리어 전략 수립에 필수적입니다.""",

                'skills': f"""{user_name}님의 전문 역량 분석을 위한 정보가 필요합니다.

보유 기술스택 및 핵심 스킬을 알려주세요:

기술 분야별 예시
- 개발: Java, Spring Boot, React, Python, AWS
- 데이터: SQL, Python, Tableau, Excel, 통계분석
- 기획: 요구사항 분석, 프로젝트 관리, 사용자 조사
- 마케팅: Google Analytics, 퍼포먼스 마케팅, 콘텐츠 기획
- 디자인: Figma, Photoshop, UI/UX 설계

입력 방법: 기술명을 쉼표로 구분
예시: "Java, Spring, MySQL, AWS" 또는 "기획, 데이터분석, SQL, 엑셀"

보유 스킬은 강점 분석과 성장 방향 설정의 핵심 지표입니다.""",

                'domain': f"""마지막으로 업무 도메인 전문성 파악이 필요합니다.

현재 담당하시는 업무 분야나 도메인을 알려주세요:

도메인 분류 예시
- 비즈니스 도메인: 전자상거래, 금융/핀테크, 게임, 교육, 헬스케어
- 기술 도메인: 백엔드 개발, 프론트엔드, 데이터 엔지니어링, DevOps
- 직무 도메인: 상품 기획, 마케팅, 영업, 인사, 재무

업무 특성 예시
- "B2C 이커머스 플랫폼 백엔드 개발"
- "핀테크 앱 사용자 경험 기획"  
- "게임 서비스 데이터 분석"
- "교육 콘텐츠 마케팅"

입력 예시: "전자상거래", "핀테크 앱 개발", "게임 기획", "교육 서비스"

도메인 전문성은 커리어 경로 설정의 중요한 기준점입니다."""
            }
        else:
            # 후속 요청 시 간단한 메시지
            messages = {
                'level': f"""{user_name}님의 경력 레벨을 알려주세요.

입력 예시: "CL1", "CL2", "CL3", "CL4", "CL5"

정확한 레벨 정보는 맞춤형 커리어 전략 수립에 필수적입니다.""",

                'skills': f"""{user_name}님의 보유 기술스택 및 핵심 스킬을 알려주세요.

입력 방법: 기술명을 쉼표로 구분
예시: "Java, Spring, MySQL, AWS" 또는 "기획, 데이터분석, SQL, 엑셀"

보유 스킬은 강점 분석과 성장 방향 설정의 핵심 지표입니다.""",

                'domain': f"""{user_name}님의 현재 담당하시는 업무 분야나 도메인을 알려주세요.

입력 예시: "전자상거래", "핀테크 앱 개발", "게임 기획", "교육 서비스"

도메인 전문성은 커리어 경로 설정의 중요한 기준점입니다."""
            }
        
        return messages.get(field, f"{field} 정보를 알려주세요.")
    
    def _normalize_user_data(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        사용자 데이터를 정규화한다 (특히 level 필드)
        
        @param user_data: 원본 사용자 데이터
        @return: 정규화된 사용자 데이터
        """
        normalized_data = user_data.copy()
        
        # level 필드 정규화 및 experience 필드 생성
        level = normalized_data.get('level')
        if level is not None:
            if isinstance(level, str):
                # 레벨을 대문자로 정규화
                normalized_level = level.upper().strip()
                normalized_data['level'] = normalized_level
                
                # 레벨을 연차로 매핑하여 experience 필드 생성
                normalized_data['experience'] = self._map_level_to_experience(normalized_level)
                print(f"🔍 레벨 정규화: {level} → {normalized_level}, 연차: {normalized_data['experience']}")
        
        return normalized_data

    async def collect_user_info_node(self, state: ChatState) -> Dict[str, Any]:
        """
        부족한 사용자 정보를 수집한다. (간단화된 버전)
        """
        print("📋 사용자 정보 수집 시작...")
        
        # state에서 기본 사용자 데이터 가져오기
        user_data = state.get("user_data", {})
        collected_info = state.get("collected_user_info", {})
        
        # 수집된 정보로 기본 데이터 업데이트
        user_data.update(collected_info)
        
        # 사용자 데이터 정규화 (특히 experience 필드)
        user_data = self._normalize_user_data(user_data)
        
        print(f"🔍 정규화된 사용자 데이터: {user_data}")
        
        # 부족한 정보 확인 (_check_missing_info에서 중첩 필드 추출도 함께 처리)
        missing_fields = self._check_missing_info(user_data)
        print(f"🔍 부족한 필드: {missing_fields}")
        
        if not missing_fields:
            # 모든 정보가 수집되었으면 커리어 포지셔닝으로 진행
            print("✅ 모든 정보 수집 완료 - 포지셔닝 단계로 진행")
            return {
                **state,
                "consultation_stage": "positioning_ready",
                "user_data": user_data,  # 최종 사용자 데이터 저장
                "info_collection_stage": "complete",
                "awaiting_user_input": False,
                "processing_log": state.get("processing_log", []) + ["사용자 정보 수집 완료"]
            }
        
        # 첫 번째 부족한 정보에 대해 질문 생성
        current_field = missing_fields[0]
        user_name = user_data.get('name', '고객')
        
        request_message = self._get_info_request_message(current_field, user_name, is_first_request=False)
        response_data = {"message": request_message}
        
        # HTML 로그 저장
        save_career_response_to_html("user_info_collection", response_data, state.get("session_id", "unknown"))
        
        return {
            **state,
            "consultation_stage": "collecting_info",
            "missing_info_fields": missing_fields,
            "info_collection_stage": current_field,
            "formatted_response": response_data,
            "final_response": response_data,
            "awaiting_user_input": True,
            "next_expected_input": f"user_{current_field}",
            "processing_log": state.get("processing_log", []) + [f"{current_field} 정보 요청"]
        }
    
    async def process_user_info_node(self, state: ChatState) -> Dict[str, Any]:
        """
        사용자가 제공한 정보를 처리한다. (간단화된 버전)
        """
        print("📝 사용자 정보 처리 중...")
        
        user_response = state.get("user_question", "").strip()
        current_field = state.get("info_collection_stage", "")
        collected_info = state.get("collected_user_info", {})
        
        # 사용자 응답 검증
        if len(user_response) < 1:
            error_response = {"message": "정보를 입력해주세요! 간단히라도 적어주시면 됩니다."}
            return {
                **state,
                "formatted_response": error_response,
                "final_response": error_response,
                "awaiting_user_input": True
            }
        
        # 필드별 정보 처리 및 정규화
        if current_field == "level":
            # 레벨 정보 정규화
            level_input = user_response.upper().strip()
            valid_levels = ['CL1', 'CL2', 'CL3', 'CL4', 'CL5']
            if level_input in valid_levels:
                collected_info["level"] = level_input
                # 레벨을 연차로 매핑
                collected_info["experience"] = self._map_level_to_experience(level_input)
            else:
                # 유효하지 않은 레벨인 경우 그대로 저장하고 다시 요청
                collected_info["level"] = user_response
                
        elif current_field == "skills":
            skills_list = [skill.strip() for skill in user_response.split(',') if skill.strip()]
            collected_info["skills"] = skills_list
            
        elif current_field == "domain":
            collected_info["domain"] = user_response.strip()
        
        # state의 user_data에 수집된 정보 반영
        user_data = state.get("user_data", {})
        user_data.update(collected_info)
        
        # 사용자 데이터 정규화 (특히 experience 필드)
        user_data = self._normalize_user_data(user_data)
        
        # 여전히 부족한 정보가 있는지 확인
        missing_fields = self._check_missing_info(user_data)
        
        if not missing_fields:
            # 모든 정보가 수집되었으면 포지셔닝 분석으로 진행
            print("✅ 모든 필수 정보 수집 완료 - 포지셔닝 분석 준비")
            return {
                **state,
                "user_data": user_data,  # 업데이트된 사용자 데이터
                "collected_user_info": collected_info,
                "consultation_stage": "positioning_ready",
                "info_collection_stage": "complete",
                "awaiting_user_input": False,
                "processing_log": state.get("processing_log", []) + [
                    f"{current_field} 정보 수집 완료: {user_response[:20]}...", 
                    "모든 필수 정보 수집 완료"
                ]
            }
        else:
            # 아직 부족한 정보가 있으면 계속 수집
            print(f"📋 추가 정보 수집 필요: {missing_fields}")
            
            # 다음 정보 요청 메시지 생성
            next_field = missing_fields[0]
            user_name = user_data.get('name', '고객')
            next_request_message = self._get_info_request_message(next_field, user_name, is_first_request=False)
            response_data = {"message": next_request_message}
            
            # HTML 로그 저장
            save_career_response_to_html("user_info_collection", response_data, state.get("session_id", "unknown"))
            
            return {
                **state,
                "user_data": user_data,  # 업데이트된 사용자 데이터
                "collected_user_info": collected_info,
                "consultation_stage": "collecting_info",
                "missing_info_fields": missing_fields,
                "info_collection_stage": next_field,  # 다음 필드로 업데이트
                "formatted_response": response_data,
                "final_response": response_data,
                "awaiting_user_input": True,
                "next_expected_input": f"user_{next_field}",
                "processing_log": state.get("processing_log", []) + [
                    f"{current_field} 정보 수집 완료: {user_response[:20]}...",
                    f"{next_field} 정보 요청"
                ]
            }
    
    def _map_level_to_experience(self, level: str) -> str:
        """
        CL 레벨을 연차 정보로 매핑한다.
        
        @param level: CL1, CL2, CL3, CL4, CL5 등의 레벨
        @return: 연차 정보 문자열
        """
        level_mapping = {
            "CL1": "1~3년",
            "CL2": "4~6년", 
            "CL3": "7~9년",
            "CL4": "10~12년",
            "CL5": "13년 이상"
        }
        
        if level and level.upper() in level_mapping:
            mapped_experience = level_mapping[level.upper()]
            print(f"🔍 레벨 매핑: {level} → {mapped_experience}")
            return mapped_experience
        else:
            print(f"🔍 알 수 없는 레벨: {level}")
            return level if level else "레벨 정보 없음"
