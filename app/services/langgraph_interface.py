# app/services/langgraph_interface.py

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
import os

class LangGraphService(ABC):
    """LangGraph 서비스 인터페이스 (팀원이 구현할 부분)"""
    
    @abstractmethod
    async def generate_initial_message(
        self, 
        room_id: str, 
        user_info: Dict[str, Any], 
        is_new_room: bool
    ) -> str:
        """초기 메시지 생성"""
        pass
    
    @abstractmethod
    async def process_user_message(
        self, 
        room_id: str, 
        user_id: str, 
        message: str
    ) -> Dict[str, Any]:
        """사용자 메시지 처리하여 AI 응답 생성"""
        pass

class MockLangGraphService(LangGraphService):
    """임시 구현 (OpenAI 직접 포함, 나중에 실제 LangGraph로 교체)"""
    
    def __init__(self):
        # OpenAI 클라이언트 직접 초기화
        try:
            from openai import AsyncOpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.openai_client = AsyncOpenAI(api_key=api_key)
                self.model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
                self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "1000"))
                self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
                print("MockLangGraphService - OpenAI 직접 연결 완료")
            else:
                print("OPENAI_API_KEY 환경변수 없음")
                self.openai_client = None
        except Exception as e:
            print(f"OpenAI 초기화 실패: {e}")
            self.openai_client = None
    
    async def generate_initial_message(
        self, 
        room_id: str, 
        user_info: Dict[str, Any], 
        is_new_room: bool
    ) -> str:
        """OpenAI를 활용한 초기 메시지 생성"""
        print(f"[Mock] LangGraph 초기 메시지 생성 중... room_id={room_id}")
        
        if is_new_room:
            return await self._generate_welcome_message_with_openai(user_info)
        else:
            return await self._generate_reconnect_message(user_info)
    
    async def _generate_welcome_message_with_openai(self, user_info: Dict[str, Any]) -> str:
        """OpenAI를 활용한 환영 메시지 생성"""
        name = user_info.get('name', '사용자')
        projects = user_info.get('projects', [])

        # 프로젝트 분석 로직 (기존과 동일)
        all_skills = set()
        domains = []
        roles = []

        projects_text = ""
        if projects:
            formatted_projects = []
            for project in projects[:3]:
                project_name = project.get('project_name', '프로젝트명 미상')
                domain = project.get('domain', '도메인 미상')
                role = project.get('role', '역할 미상')
                scale = project.get('scale', '미기입')
                project_skills = project.get('skills', [])
                
                domains.append(domain)
                roles.append(role)
                all_skills.update(project_skills)
                
                project_info = f"• {project_name} ({domain} 도메인)"
                project_info += f" - {role} 역할 ({scale} 규모)"
                if project_skills:
                    project_info += f" - {len(project_skills)}개 기술 활용"
                formatted_projects.append(project_info)
            
            if len(projects) > 3:
                formatted_projects.append(f"... 외 {len(projects) - 3}개 프로젝트")
            
            projects_text = '\n'.join(formatted_projects)
        else:
            projects_text = "진행한 프로젝트 정보가 없습니다."
        
        from collections import Counter
        domain_counts = Counter(domains)
        role_counts = Counter(roles)
        
        primary_domain = domain_counts.most_common(1)[0][0] if domain_counts else "미분류"
        primary_role = role_counts.most_common(1)[0][0] if role_counts else "미분류"
        
        domain_text = ', '.join([f"{domain}({count}회)" for domain, count in domain_counts.items()]) if domain_counts else "도메인 경험 정보가 없습니다."
        role_text = ', '.join([f"{role}({count}회)" for role, count in role_counts.items()]) if role_counts else "역할 경험 정보가 없습니다."
        
        # OpenAI 프롬프트 (기존과 동일)
        enhanced_prompt = f"""
        다음은 새로 만난 사용자의 상세 정보입니다:
        
        === 기본 정보 ===
        이름: {name}
        총 프로젝트 경험: {len(projects)}개
        주요 도메인: {primary_domain}
        주요 역할: {primary_role}
        
        === 프로젝트 경험 ===
        {projects_text}
        
        === 보유 스킬 ===
        {', '.join(list(all_skills)[:10])}{'...' if len(all_skills) > 10 else ''}
        
        === 도메인별 경험 ===
        {domain_text}
        
        === 역할별 경험 ===
        {role_text}
        
        당신은 SK AX 사내 커리어패스 전문 상담사 "G.Navi"입니다. 위 정보를 바탕으로 다음 조건에 맞는 개인화된 인사 메시지를 생성해주세요:
        
        1. 친근하고 전문적인 톤으로 작성
        2. 2-3문장으로 간결하게 구성
        3. 사용자의 주요 경험이나 스킬을 자연스럽게 언급
        4. 어떤 도움을 줄 수 있는지 구체적으로 제시
        5. 한국어로 작성
        
        예시 스타일: "안녕하세요 [이름]님! [주요 경험/스킬 언급]. [제공 가능한 도움 제시]"
        """
        
        # OpenAI API 직접 호출
        if self.openai_client:
            try:
                print("OpenAI 응답 생성 중...")
                response = await self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "당신은 도움이 되고 친근한 AI 어시스턴트입니다. 한국어로 응답해주세요."
                        },
                        {
                            "role": "user",
                            "content": enhanced_prompt
                        }
                    ],
                    max_tokens=self.max_tokens,
                    temperature=self.temperature
                )
                
                initial_message = response.choices[0].message.content.strip()
                print(f"OpenAI 응답 생성 완료: {initial_message[:100]}...")
                return initial_message
                
            except Exception as e:
                print(f"OpenAI 응답 생성 실패: {e}")
                # 폴백 메시지
                return f"안녕하세요 {name}님! SK AX 커리어패스 전문 상담사 G.Navi입니다. 어떤 도움이 필요하신가요?"
        else:
            # OpenAI 없을 때 기본 메시지
            if projects:
                return f"안녕하세요 {name}님! {primary_domain} 분야에서 {primary_role}로 활동하고 계시는군요. SK AX 커리어패스 전문 상담사 G.Navi입니다. 어떤 도움이 필요하신가요?"
            else:
                return f"안녕하세요 {name}님! SK AX 커리어패스 전문 상담사 G.Navi입니다. 커리어에 대해 궁금한 점이 있으시면 언제든 말씀해주세요!"
    
    async def _generate_reconnect_message(self, user_info: Dict[str, Any]) -> str:
        """재접속 메시지 생성"""
        name = user_info.get('name', '사용자')
        return f"다시 만나서 반갑습니다, {name}님! 이전 대화를 이어가겠습니다. 오늘은 어떤 도움이 필요하신가요?"
    
    async def process_user_message(
        self, 
        room_id: str, 
        user_id: str, 
        message: str
    ) -> Dict[str, Any]:
        """OpenAI를 활용한 메시지 처리"""
        print(f"🤖 [Mock] LangGraph 메시지 처리 중... message={message[:30]}...")
        
        if self.openai_client:
            try:
                response = await self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "당신은 SK AX 사내 커리어패스 전문 상담사입니다. 친근하고 전문적인 톤으로 커리어 관련 조언을 제공해주세요."
                        },
                        {
                            "role": "user",
                            "content": message
                        }
                    ],
                    max_tokens=self.max_tokens,
                    temperature=self.temperature
                )
                
                ai_response = response.choices[0].message.content.strip()
                
                return {
                    "content": ai_response,
                    "metadata": {
                        "processing_method": "mock_langgraph_with_openai",
                        "timestamp": datetime.utcnow().isoformat(),
                        "confidence": 0.8
                    }
                }
                
            except Exception as e:
                print(f"❌ OpenAI 메시지 처리 실패: {e}")
                return {
                    "content": "죄송합니다. 일시적인 오류가 발생했습니다. 다시 시도해주세요.",
                    "metadata": {
                        "processing_method": "fallback",
                        "error": str(e)
                    }
                }
        else:
            # OpenAI 없을 때 기본 응답
            return {
                "content": f"'{message}'에 대해 말씀해주셨군요. 더 구체적으로 설명해주시면 더 나은 조언을 드릴 수 있습니다.",
                "metadata": {
                    "processing_method": "fallback_no_openai"
                }
            }