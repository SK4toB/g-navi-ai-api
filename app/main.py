# app/main.py
"""
* @className : FastAPI Application
* @description : G-Navi AI API 메인 애플리케이션 모듈
*                LangGraph 기반 사내 커리어패스 추천 LLM 서비스의 메인 엔트리 포인트입니다.
*                FastAPI 프레임워크를 사용하여 RESTful API를 제공하고,
*                CORS 미들웨어와 라이프사이클 관리를 포함합니다.
*
*                 주요 기능:
*                - FastAPI 애플리케이션 설정 및 구성
*                - CORS 미들웨어 설정
*                - 애플리케이션 라이프사이클 관리
*                - API 라우터 등록 및 관리
*                - 세션 자동 정리 기능
*
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.v1.api import api_router
from app.config.settings import settings
from dotenv import load_dotenv
import os

# 환경변수 로드 (최상단에 위치)
load_dotenv()

from app.core.dependencies import get_service_container


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    앱 라이프사이클을 관리한다.
    애플리케이션 시작 시 세션 자동 정리를 활성화하고,
    종료 시 자동 정리를 중지합니다.
    
    @param app: FastAPI - FastAPI 애플리케이션 인스턴스
    """
    # 시작 시
    print(" Career Path Chat API 시작...")  # 애플리케이션 시작 로그 출력
    
    # 세션 자동 정리 시작
    try:  # 예외 처리 시작
        container = get_service_container()  # 서비스 컨테이너 조회
        chat_service = container.chat_service  # 채팅 서비스 조회
        await chat_service.start_auto_cleanup()  # 자동 정리 시작
        print(" 세션 자동 정리 활성화됨")  # 성공 로그 출력
    except Exception as e:  # 예외 발생 시
        print(f" 세션 자동 정리 시작 실패: {e}")  # 실패 로그 출력
    
    yield  # 애플리케이션 실행 중
    
    # 종료 시
    print("🛑 Career Path Chat API 종료...")  # 애플리케이션 종료 로그 출력
    
    # 세션 자동 정리 중지
    try:  # 예외 처리 시작
        container = get_service_container()  # 서비스 컨테이너 조회
        chat_service = container.chat_service  # 채팅 서비스 조회
        await chat_service.stop_auto_cleanup()  # 자동 정리 중지
        print(" 세션 자동 정리 중지됨")  # 성공 로그 출력
    except Exception as e:  # 예외 발생 시
        print(f" 세션 자동 정리 중지 실패: {e}")  # 실패 로그 출력


# FastAPI 애플리케이션 생성
app = FastAPI(
    title="Career Path Chat API",  # API 제목
    description="LangGraph 기반 사내 커리어패스 추천 LLM 서비스",  # API 설명
    version="1.0.0",  # API 버전
    docs_url="/ai/docs",  # Swagger UI URL 경로          
    redoc_url="/ai/redoc",  # ReDoc URL 경로        
    openapi_url="/ai/openapi.json",  # OpenAPI 스키마 URL 경로
    lifespan=lifespan  # 라이프사이클 관리자 설정
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,  # CORS 미들웨어 추가
    allow_origins=["*"],  # 모든 도메인 허용 (프로덕션에서는 구체적인 도메인 지정)
    allow_credentials=True,  # 인증 정보 허용
    allow_methods=["*"],  # 모든 HTTP 메서드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)

# API 라우터 등록
app.include_router(api_router, prefix="/ai")  # "/ai" 접두사로 API 라우터 등록

@app.get("/ai")
async def root():
    """
    루트 엔드포인트 - API 기본 정보를 반환한다.
    
    @return dict - API 기본 정보 (메시지, 버전, 설명)
    """
    return {
        "message": "Career Path Chat API",  # API 메시지
        "version": "1.0.0",  # API 버전
        "description": "사내 커리어패스 추천 채팅 서비스"  # API 설명
    }

if __name__ == "__main__":  # 메인 모듈에서 직접 실행하는 경우
    import uvicorn  # ASGI 서버 import
    uvicorn.run(  # 서버 실행
        "main:app",  # 애플리케이션 모듈 및 인스턴스 지정
        host="0.0.0.0",  # 모든 인터페이스에서 접근 허용
        port=8001,  # 포트 번호 8001
        reload=True  # 코드 변경 시 자동 재시작
    )