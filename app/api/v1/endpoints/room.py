# app/api/v1/endpoints/room.py

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
import uuid
from datetime import datetime

from app.models.chat import ChatRoomCreate, ChatRoomResponse, MessageCreate, MessageResponse
from app.services.openai_service import OpenAIService

router = APIRouter()

# 의존성 주입
def get_openai_service():
    return OpenAIService()

# 채팅방 생성 및 초기 메시지 전송 엔드포인트
@router.post("/rooms", response_model=ChatRoomResponse)
async def create_chat_room(
    room_data: ChatRoomCreate,
    openai_service: OpenAIService = Depends(get_openai_service)
):
    """
    채팅방 생성 및 초기 AI 메시지 생성
    SpringBoot에서 user_info와 함께 호출
    """
    print(f"채팅방 생성 요청 받음: user_id={room_data.user_id}")
    print(f"사용자 정보: {room_data.user_info}")

    try:
        room_id = str(uuid.uuid4())
        print(f"채팅방 ID 생성: {room_id}")
        
        # 사용자 정보를 바탕으로 초기 인사 메시지 생성
        user_info = room_data.user_info
        name = user_info.get('name', '사용자')
        projects = user_info.get('projects', [])

        # 프로젝트에서 스킬과 경험 정보 추출
        all_skills = set()
        domains = []
        roles = []

        # 프로젝트 정보 포맷팅 및 데이터 추출
        projects_text = ""
        if projects:
            formatted_projects = []
            for project in projects[:3]:  # 최대 3개만 표시
                project_name = project.get('project_name', '프로젝트명 미상')
                domain = project.get('domain', '도메인 미상')
                role = project.get('role', '역할 미상')
                scale = project.get('scale', '미기입')
                project_skills = project.get('skills', [])
                
                # 통계용 데이터 수집
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
        
        # 도메인/역할 경험 통계 생성
        from collections import Counter
        domain_counts = Counter(domains)
        role_counts = Counter(roles)
        
        # 가장 많은 경험의 도메인/역할 찾기
        primary_domain = domain_counts.most_common(1)[0][0] if domain_counts else "미분류"
        primary_role = role_counts.most_common(1)[0][0] if role_counts else "미분류"
        
        # 경험 통계 텍스트 생성
        domain_text = ', '.join([f"{domain}({count}회)" for domain, count in domain_counts.items()]) if domain_counts else "도메인 경험 정보가 없습니다."
        role_text = ', '.join([f"{role}({count}회)" for role, count in role_counts.items()]) if role_counts else "역할 경험 정보가 없습니다."
        
        # 더 상세한 프롬프트 구성
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
        
        print("OpenAI 응답 생성 중...")
        initial_message = await openai_service.generate_response(enhanced_prompt)
        print(f"AI 응답 생성 완료: {initial_message[:100]}...")
        
        return ChatRoomResponse(
            room_id=room_id,
            user_id=room_data.user_id,
            created_at=datetime.utcnow(),
            initial_message=initial_message
        )
        
    except Exception as e:
        print(f"채팅방 생성 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"채팅방 생성 실패: {str(e)}")