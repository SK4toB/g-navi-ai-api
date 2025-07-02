# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.config.settings import settings
from dotenv import load_dotenv
import os

# 환경변수 로드 (최상단에 위치)
load_dotenv()

app = FastAPI(
    title="Career Path Chat API",
    description="LangGraph 기반 사내 커리어패스 추천 LLM 서비스",
    version="1.0.0",
    docs_url="/ai/docs",           
    redoc_url="/ai/redoc",         
    openapi_url="/ai/openapi.json"
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