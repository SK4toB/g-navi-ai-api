# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.v1.api import api_router
from app.config.settings import settings
from app.core.dependencies import get_service_container


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 라이프사이클 관리"""
    # 시작 시
    print("🚀 Career Path Chat API 시작...")
    
    # 세션 자동 정리 시작
    try:
        container = get_service_container()
        chat_service = container.chat_service
        await chat_service.start_auto_cleanup()
        print("✅ 세션 자동 정리 활성화됨")
    except Exception as e:
        print(f"⚠️ 세션 자동 정리 시작 실패: {e}")
    
    yield
    
    # 종료 시
    print("🛑 Career Path Chat API 종료...")
    
    # 세션 자동 정리 중지
    try:
        container = get_service_container()
        chat_service = container.chat_service
        await chat_service.stop_auto_cleanup()
        print("✅ 세션 자동 정리 중지됨")
    except Exception as e:
        print(f"⚠️ 세션 자동 정리 중지 실패: {e}")


app = FastAPI(
    title="Career Path Chat API",
    description="LangGraph 기반 사내 커리어패스 추천 LLM 서비스",
    version="1.0.0",
    docs_url="/ai/docs",           
    redoc_url="/ai/redoc",         
    openapi_url="/ai/openapi.json",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 구체적인 도메인 지정
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(api_router, prefix="/ai")

@app.get("/ai")
async def root():
    return {
        "message": "Career Path Chat API", 
        "version": "1.0.0",
        "description": "사내 커리어패스 추천 채팅 서비스"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8001, 
        reload=True
    )