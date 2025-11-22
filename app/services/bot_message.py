# app/services/bot_message.py
"""
* @className : BotMessageService
* @description : 봇 메시지 서비스 모듈
*                AI 봇의 메시지 생성과 관리를 담당하는 서비스입니다.
*                시스템 메시지와 응답 메시지 처리를 담당합니다.
*
"""

from typing import Dict, Any
import os

class BotMessageService:
    """
    봇 메시지 생성 서비스
    """
    
    def __init__(self):
        self.openai_client = None
        self._init_openai()
    
    def _init_openai(self):
        """OpenAI 클라이언트 초기화"""
        try:
            from openai import AsyncOpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.openai_client = AsyncOpenAI(api_key=api_key)
                self.model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
                self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "500"))
                self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.5"))
                print("BotMessageService OpenAI 연결 완료")
            else:
                print("OpenAI API 키가 없습니다. 기본 메시지를 사용합니다.")
        except Exception as e:
            print(f"OpenAI 초기화 실패: {e}")

    async def _generate_welcome_message(self, user_info: Dict[str, Any]) -> str:
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

    async def generate_welcome_message(self, user_info: Dict[str, Any]) -> str:
        """
        사용자를 위한 환영 메시지 생성 (Public API)
        """
        try:
            welcome_message = await self._generate_welcome_message(user_info)
            print(f"BotMessageService 환영 메시지 생성 완료: {welcome_message[:100]}...")
            return welcome_message
        except Exception as e:
            print(f"BotMessageService 환영 메시지 생성 실패: {e}")
            name = user_info.get('name', '사용자')
            return f"안녕하세요 {name}님! SK AX 커리어패스 전문 상담사 G.Navi입니다. 어떤 도움이 필요하신가요?"