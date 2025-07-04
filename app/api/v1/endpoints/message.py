# app/api/v1/endpoints/message.py
"""
* @className : Message API Endpoints
* @description : 메시지 처리 API 엔드포인트 모듈
*                사용자 메시지를 처리하는 REST API를 제공합니다.
*                메시지 전송과 AI 응답 생성을 담당합니다.
*
* @modification : 2025.07.01(이재원) 최초생성
*
* @author 이재원
* @Date 2025.07.01
* @version 1.0
* @see FastAPI, MessageProcessor
*  == 개정이력(Modification Information) ==
*  
*   수정일        수정자        수정내용
*   ----------   --------     ---------------------------
*   2025.07.01   이재원       최초 생성
*  
* Copyright (C) by G-Navi AI System All right reserved.
"""

from fastapi import APIRouter, HTTPException, Depends, Path
from datetime import datetime
import time

from app.api.deps import get_chat_service
from app.services.chat_service import ChatService
from app.models.message import (
    MessageSend, MessageResponse, SessionStatus, 
    SessionCloseResponse, SessionDebugInfo
)

router = APIRouter()

@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def send_message(
    request: MessageSend,
    conversation_id: str = Path(..., description="채팅방 ID"),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    실행 중인 LangGraph에 메시지 전송
    채팅방이 생성되어 LangGraph가 실행 중인 상태에서 호출
    """
    start_time = time.time()
    
    try:  # 메시지 전송 처리 시작
        print(f"메시지 전송: conversation_id={conversation_id}, member_id={request.member_id}")
        
        # LangGraph Resume 실행 (중단점에서 재개)
        bot_message = await chat_service.send_message(  # 채팅 서비스 메시지 전송 호출
            conversation_id=conversation_id,
            member_id=request.member_id,
            message_text=request.message_text
        )
        
        end_time = time.time()
        processing_time = int((end_time - start_time) * 1000)  # 처리 시간 계산 (밀리초)
        
        print(f"메시지 응답 생성 완료, 메시지 처리 시간: {processing_time}ms")
        
        # TODO: MongoDB에 대화 내역 저장 (나중에 추가)
        
        return MessageResponse(  # 응답 객체 반환
            conversationId=conversation_id,
            memberId=request.member_id,
            messageText=request.message_text,
            botMessage=bot_message,
            timestamp=datetime.utcnow()
        )
        
    except ValueError as e:  # 값 오류 처리 (세션 없음)
        # 세션이 없는 경우
        print(f"세션 없음: {str(e)}")
        raise HTTPException(status_code=404, detail=f"채팅방을 찾을 수 없습니다: {conversation_id}")  # HTTP 404 예외 발생
    
    except Exception as e:  # 기타 예외 처리
        # 기타 처리 오류
        print(f"메시지 처리 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"메시지 처리 실패: {str(e)}")  # HTTP 500 예외 발생


@router.get("/{conversation_id}/status", response_model=SessionStatus)
async def get_session_status(
    conversation_id: str = Path(..., description="채팅방 ID"),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    LangGraph 세션 상태 확인
    채팅방이 활성화되어 있는지 확인
    """
    try:  # 세션 상태 확인 처리 시작
        print(f"세션 상태 확인: conversation_id={conversation_id}")
        
        status_info = chat_service.get_session_status(conversation_id)  # 채팅 서비스 상태 확인 호출
        
        print(f"세션 상태: {status_info}")
        
        return SessionStatus(**status_info)  # 세션 상태 응답 반환
        
    except Exception as e:  # 예외 처리
        print(f"세션 상태 확인 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"상태 확인 실패: {str(e)}")  # HTTP 500 예외 발생

@router.delete("/{conversation_id}", response_model=SessionCloseResponse)
async def close_session(
    conversation_id: str = Path(..., description="채팅방 ID"),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    LangGraph 세션 종료
    메모리에서 세션 정보 제거
    """
    try:  # 세션 종료 처리 시작
        print(f"세션 종료 요청: conversation_id={conversation_id}")
        
        await chat_service.close_chat_session(conversation_id)  # 채팅 서비스 세션 종료 호출
        
        print(f"세션 종료 완료: {conversation_id}")
        
        return SessionCloseResponse(
            message=f"채팅방 {conversation_id} 세션이 종료되었습니다.",
            conversationId=conversation_id,
            closed_at=datetime.utcnow()
        )
        
    except Exception as e:
        print(f"세션 종료 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"세션 종료 실패: {str(e)}")

# 개발/디버깅용 엔드포인트
@router.get("/{conversation_id}/debug", response_model=SessionDebugInfo)
async def debug_session(
    conversation_id: str = Path(..., description="채팅방 ID"),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    개발용: 세션 상세 정보 확인
    """
    try:
        if conversation_id in chat_service.active_sessions:
            session = chat_service.active_sessions[conversation_id]
            return SessionDebugInfo(
                conversationId=conversation_id,
                status="active",
                thread_id=session["thread_id"],
                graph_compiled=session["graph"] is not None,
                config=session["config"],
                total_active_sessions=len(chat_service.active_sessions)
            )
        else:
            return SessionDebugInfo(
                conversationId=conversation_id,
                status="not_found",
                total_active_sessions=len(chat_service.active_sessions)
            )
    except Exception as e:
        return SessionDebugInfo(
            conversationId=conversation_id,
            error=str(e)
        )