# # app/main.py
# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from app.api.v1.api import api_router
# from app.config.settings import settings

# app = FastAPI(
#     title="Career Path Chat API",
#     description="LangGraph 기반 사내 커리어패스 추천 LLM 서비스",
#     version="1.0.0"
# )

# # CORS 설정
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # 프로덕션에서는 구체적인 도메인 지정
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # API 라우터 등록
# # app.include_router(api_router, prefix="/api/v1")
# app.include_router(api_router, prefix="/ai")

# @app.get("/")
# async def root():
#     return {
#         "message": "Career Path Chat API", 
#         "version": "1.0.0",
#         "description": "사내 커리어패스 추천 채팅 서비스"
#     }

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(
#         "main:app", 
#         host="0.0.0.0", 
#         port=8001, 
#         reload=True
#     )

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from api.v1.api import api_router
from api.v1.endpoints.simple_chat import router as simple_chat_router
from config.settings import settings

# 간단한 RAG 시스템 초기화
@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # 시작 시 초기화
    print("🚀 지나비 프로젝트 시작 중...")
    
    # ChromaDB 연결 확인
    try:
        from services.vector_db_service import collection
        vector_count = collection.count()
        print(f"✅ ChromaDB 연결 완료 - 총 {vector_count}개의 벡터 확인")
    except Exception as e:
        print(f"❌ ChromaDB 연결 실패: {e}")
    
    # OpenAI 서비스 초기화 확인
    from services.openai_service import OpenAIService
    try:
        openai_service = OpenAIService()
        print("✅ OpenAI 서비스 초기화 완료")
    except Exception as e:
        print(f"❌ OpenAI 서비스 초기화 실패: {e}")
    
    # RAG 서비스 초기화
    try:
        from services.rag_service import RAGService
        rag_service = RAGService()
        print("✅ RAG 서비스 초기화 완료")
    except Exception as e:
        print(f"❌ RAG 서비스 초기화 실패: {e}")
    
    yield
    
    # 종료 시 정리
    print("👋 지나비 프로젝트 종료 중...")

# FastAPI 앱 생성
app = FastAPI(
    title="지나비 프로젝트 API",
    description="AI 기반 구성원 경력개발지원 시스템 (RAG 기반)",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS if hasattr(settings, 'ALLOWED_HOSTS') else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 기존 API 라우터 등록
app.include_router(api_router, prefix="/api/v1")

# 간단한 RAG 채팅 라우터 추가
app.include_router(simple_chat_router, prefix="/api/v1", tags=["Simple RAG Chat"])

# 헬스 체크 엔드포인트
@app.get("/")
async def root():
    """루트 엔드포인트 - 헬스 체크"""
    return {
        "message": "지나비 프로젝트 RAG 시스템이 정상 동작 중입니다.",
        "version": "1.0.0",
        "features": ["구성원 성장 이력 기반 상담", "벡터 검색", "AI 답변 생성"],
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    """상세 헬스 체크"""
    try:
        # ChromaDB 상태 확인
        from services.vector_db_service import collection
        vector_count = collection.count()
        
        # OpenAI 서비스 확인
        from services.openai_service import OpenAIService
        openai_service = OpenAIService()
        
        # RAG 서비스 확인
        from services.rag_service import RAGService
        rag_service = RAGService()
        
        return {
            "status": "healthy",
            "services": {
                "chromadb": "connected",
                "openai": "connected", 
                "rag": "ready",
                "api": "running"
            },
            "data": {
                "total_vectors": vector_count,
                "collection": "mentor_history"
            },
            "timestamp": "2025-06-05T00:00:00Z"
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"서비스 상태 확인 중 오류 발생: {str(e)}"
        )

# 개발 서버 실행
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )