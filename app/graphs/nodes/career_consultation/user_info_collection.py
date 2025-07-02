# app/graphs/nodes/career_consultation/user_info_collection.py
"""
사용자 정보 수집 노드
부족한 정보(연차, 기술스택, 도메인)를 사용자로부터 수집
"""

from typing import Dict, Any, List
from app.graphs.state import ChatState


class UserInfoCollectionNode:
    """
    사용자 정보 수집 노드
    """
    
    def __init__(self, graph_builder):
        self.graph_builder = graph_builder
    
    def _check_missing_info(self, user_data: Dict[str, Any]) -> List[str]:
        """
        사용자 데이터에서 부족한 정보를 확인한다.
        
        @param user_data: 사용자 프로필 데이터
        @return: 부족한 정보 필드 리스트
        """
        missing_fields = []
        
        # 연차 확인
        experience = user_data.get('experience')
        if not experience or (isinstance(experience, str) and experience.strip() == ''):
            missing_fields.append('experience')
        
        # 기술스택 확인  
        skills = user_data.get('skills', [])
        if not skills or len(skills) == 0:
            missing_fields.append('skills')
        
        # 도메인 확인
        domain = user_data.get('domain')
        if not domain or (isinstance(domain, str) and domain.strip() == ''):
            missing_fields.append('domain')
            
        return missing_fields
    
    def _get_info_request_message(self, field: str, user_name: str) -> str:
        """
        전문적이고 체계적인 정보 요청 메시지를 생성한다.
        
        @param field: 요청할 정보 필드
        @param user_name: 사용자 이름
        @return: 요청 메시지
        """
        messages = {
            'experience': f"""👋 안녕하세요 {user_name}님! **전문 커리어 컨설팅**을 시작하겠습니다.

**정확한 분석을 위해 현재 경력 수준을 확인하겠습니다.**

**💼 총 경력 연차**를 알려주세요:

**📊 경력 구분 가이드**
- **0-1년**: 신입/인턴 (예: "신입", "1년차")
- **2-3년**: 주니어 (예: "2년", "3년차") 
- **4-7년**: 미드레벨 (예: "5년", "6년 3개월")
- **8년 이상**: 시니어+ (예: "10년", "12년차")

**입력 예시**: "5년", "3년차", "신입", "7년 6개월"

*정확한 연차 정보는 맞춤형 커리어 전략 수립에 필수적입니다.*""",

            'skills': f"""📝 {user_name}님의 **전문 역량 분석**을 위한 정보가 필요합니다.

**🛠️ 보유 기술스택 및 핵심 스킬**을 알려주세요:

**기술 분야별 예시**
- **개발**: Java, Spring Boot, React, Python, AWS
- **데이터**: SQL, Python, Tableau, Excel, 통계분석
- **기획**: 요구사항 분석, 프로젝트 관리, 사용자 조사
- **마케팅**: Google Analytics, 퍼포먼스 마케팅, 콘텐츠 기획
- **디자인**: Figma, Photoshop, UI/UX 설계

**입력 방법**: 기술명을 쉼표로 구분
**예시**: "Java, Spring, MySQL, AWS" 또는 "기획, 데이터분석, SQL, 엑셀"

*보유 스킬은 강점 분석과 성장 방향 설정의 핵심 지표입니다.*""",

            'domain': f"""🎯 마지막으로 **업무 도메인 전문성** 파악이 필요합니다.

**🏢 현재 담당 업무 분야**를 알려주세요:

**도메인 분류 예시**
- **비즈니스 도메인**: 전자상거래, 금융/핀테크, 게임, 교육, 헬스케어
- **기술 도메인**: 백엔드 개발, 프론트엔드, 데이터 엔지니어링, DevOps
- **직무 도메인**: 상품 기획, 마케팅, 영업, 인사, 재무

**업무 특성 예시**
- "B2C 이커머스 플랫폼 백엔드 개발"
- "핀테크 앱 사용자 경험 기획"  
- "게임 서비스 데이터 분석"
- "교육 콘텐츠 마케팅"

**입력 예시**: "전자상거래", "핀테크 앱 개발", "게임 기획", "교육 서비스"

*도메인 전문성은 커리어 경로 설정의 중요한 기준점입니다.*"""
        }
        
        return messages.get(field, f"{field} 정보를 알려주세요.")
    
    async def collect_user_info_node(self, state: ChatState) -> Dict[str, Any]:
        """
        부족한 사용자 정보를 수집한다.
        """
        print("📋 사용자 정보 수집 시작...")
        
        user_data = self.graph_builder.get_user_info_from_session(state)
        user_name = user_data.get('name', '고객')
        
        # 현재 수집된 정보와 기존 정보 합치기
        collected_info = state.get("collected_user_info", {})
        merged_user_data = {**user_data, **collected_info}
        
        # 부족한 정보 확인
        missing_fields = self._check_missing_info(merged_user_data)
        
        if not missing_fields:
            # 모든 정보가 수집되었으면 커리어 포지셔닝으로 진행
            return {
                **state,
                "consultation_stage": "positioning_ready",
                "collected_user_info": collected_info,
                "missing_info_fields": [],
                "info_collection_stage": "complete",
                "processing_log": state.get("processing_log", []) + ["사용자 정보 수집 완료"]
            }
        
        # 첫 번째 부족한 정보에 대해 질문
        current_field = missing_fields[0]
        request_message = self._get_info_request_message(current_field, user_name)
        
        return {
            **state,
            "consultation_stage": "collecting_info",
            "missing_info_fields": missing_fields,
            "info_collection_stage": current_field,
            "formatted_response": {"message": request_message},
            "awaiting_user_input": True,
            "next_expected_input": f"user_{current_field}",
            "processing_log": state.get("processing_log", []) + [f"{current_field} 정보 요청"]
        }
    
    async def process_user_info_node(self, state: ChatState) -> Dict[str, Any]:
        """
        사용자가 제공한 정보를 처리한다.
        """
        print("📝 사용자 정보 처리 중...")
        
        user_response = state.get("user_question", "").strip()
        current_field = state.get("info_collection_stage", "")
        collected_info = state.get("collected_user_info", {})
        
        # 사용자 응답 검증
        if len(user_response) < 1:
            return {
                **state,
                "formatted_response": {
                    "message": "정보를 입력해주세요! 간단히라도 적어주시면 됩니다. 😊"
                },
                "awaiting_user_input": True
            }
        
        # 필드별 정보 처리
        if current_field == "experience":
            # 연차 정보 추출 및 정규화
            import re
            numbers = re.findall(r'\d+', user_response)
            if numbers:
                collected_info["experience"] = f"{numbers[0]}년"
            elif "신입" in user_response:
                collected_info["experience"] = "신입"
            else:
                collected_info["experience"] = user_response
                
        elif current_field == "skills":
            # 기술스택을 리스트로 변환
            skills_list = [skill.strip() for skill in user_response.split(',')]
            collected_info["skills"] = skills_list
            
        elif current_field == "domain":
            collected_info["domain"] = user_response
        
        # 업데이트된 정보로 다시 수집 프로세스 실행
        return {
            **state,
            "collected_user_info": collected_info,
            "consultation_stage": "collecting_info",  # 다시 수집 프로세스로
            "processing_log": state.get("processing_log", []) + [f"{current_field} 정보 수집 완료: {user_response[:20]}..."]
        }
