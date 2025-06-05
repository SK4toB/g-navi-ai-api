# app/services/chat_service.py

from typing import Dict, Any
import os
from app.graphs.graph_builder import ChatGraphBuilder

class ChatService:
    """
    지속적인 채팅 서비스
    채팅방 생성 시 LangGraph 시작, 사용자 입력마다 resume
    """
    def __init__(self):
        self.graph_builder = ChatGraphBuilder()
        self.active_sessions = {}  # room_id -> {graph, thread_id, state}
        self.openai_client = None
        self._init_openai()
        print("ChatService 초기화")
    
    def _init_openai(self):
        """OpenAI 클라이언트 초기화 (초기 메시지용)"""
        try:
            from openai import AsyncOpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.openai_client = AsyncOpenAI(api_key=api_key)
                self.model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
                self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "1000"))
                self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
                print("ChatService OpenAI 연결")
        except Exception as e:
            print(f"OpenAI 초기화 실패: {e}")
    
    async def create_chat_session(self, room_id: str, user_info: Dict[str, Any]) -> str:
        """
        채팅 세션 생성 및 LangGraph 시작
        """
        print("services/chat_service.py: create_chat_session")
        print(f"지속적 채팅 세션 생성: {room_id}")
        
        # 1. LangGraph 빌드
        compiled_graph = await self.graph_builder.build_persistent_chat_graph(room_id, user_info)
        
        # 2. 세션 시작 (첫 번째 실행 - user_input_wait까지)
        thread_id = f"thread_{room_id}"
        config = {"configurable": {"thread_id": thread_id}}
        
        # 초기 상태로 그래프 시작
        initial_state = {
            "user_message": "",  # 초기에는 빈 메시지
            "user_id": user_info.get("user_id", ""),
            "room_id": room_id,
            "user_info": user_info,
            # 나머지 필드들 초기화
            "intent": None,
            "embedding_vector": None,
            "memory_results": None,
            "similarity_score": None,
            "profiling_data": None,
            "connection_suggestions": None,
            "final_response": None
        }
        
        print(f"초기 그래프 실행 (user_input_wait까지)")
        
        # 첫 실행 (user_input_wait에서 중단됨)
        result = await compiled_graph.ainvoke(initial_state, config)
        
        print(f"그래프가 user_input_wait에서 중단됨")
        print(f"중단 상태: {list(result.keys())}")
        
        # 세션 정보 저장
        self.active_sessions[room_id] = {
            "graph": compiled_graph,
            "thread_id": thread_id,
            "config": config,
            "user_info": user_info
        }
        
        print(f"LangGraph 세션 시작 완료: {room_id}")
        
        # 3. 환영 메시지 생성 (별도로)
        initial_message = await self._generate_welcome_message(user_info)
        
        return initial_message
    
    async def send_message(self, room_id: str, user_id: str, message: str) -> str:
        """
        실행 중인 LangGraph에 메시지 전송 (Resume)
        """
        print(f"services/chat_service.py: send_message")
        print(f"LangGraph Resume 시작: {room_id}")
        
        if room_id not in self.active_sessions:
            raise ValueError(f"활성화된 세션이 없습니다: {room_id}")
        
        session = self.active_sessions[room_id]
        graph = session["graph"]
        config = session["config"]
        user_info = session.get("user_info", {})
        
        try:
            print(f"입력 메시지: {message}")
            
            # 사용자 메시지로 상태 업데이트하여 Resume
            updated_state = {
                "user_message": message,
                "user_id": user_id,
                "room_id": room_id,
                "user_info": user_info
            }
            
            print(f"그래프 Resume 실행...")
            
            # LangGraph Resume (중단점에서 재개 → 다음 중단점까지)
            result = await graph.ainvoke(updated_state, config)
            
            print(f"그래프 Resume 완료")
            print(f"Resume 결과 키들: {list(result.keys())}")
            
            # 최종 응답 추출
            final_response = result.get("final_response", "응답을 생성할 수 없습니다.")
            
            if final_response is None:
                print("final_response가 None입니다!")
                print(f"result 전체 내용: {result}")
                final_response = "응답을 생성할 수 없습니다."
            
            print(f"최종 응답 추출: {str(final_response)[:100]}...")
            return final_response
    
            
        except Exception as e:
            print(f"Resume 처리 실패: {e}")
            import traceback
            print(f"상세 에러: {traceback.format_exc()}")
            return f"죄송합니다. 메시지 처리 중 오류가 발생했습니다: {str(e)}"
    
    async def close_chat_session(self, room_id: str):
        """채팅 세션 종료"""
        if room_id in self.active_sessions:
            del self.active_sessions[room_id]
            print(f"지속적 채팅 세션 종료: {room_id}")
    
    def get_session_status(self, room_id: str) -> Dict[str, Any]:
        """세션 상태 조회"""
        if room_id in self.active_sessions:
            return {
                "room_id": room_id,
                "status": "active",
                "thread_id": self.active_sessions[room_id]["thread_id"]
            }
        return {"room_id": room_id, "status": "inactive"}
    
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