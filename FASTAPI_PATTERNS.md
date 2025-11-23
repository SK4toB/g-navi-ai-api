# FastAPI 프로젝트 구조 패턴 가이드

실전에서 사용하는 FastAPI 프로젝트 구조와 Best Practices

---

## 🏗️ 일반적인 FastAPI 프로젝트 구조 패턴

### **패턴 1: Small Project (단순)**

```
my-api/
├── main.py              # FastAPI 앱 + 라우터
├── models.py            # Pydantic 모델
├── database.py          # DB 연결
├── requirements.txt
└── .env
```

**적합한 경우:** MVP, 프로토타입, 단순 API

---

### **패턴 2: Medium Project (모듈화)**

```
my-api/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI 앱
│   ├── config.py        # 설정
│   ├── models/          # Pydantic 모델
│   ├── routers/         # API 라우터
│   ├── services/        # 비즈니스 로직
│   └── database.py      # DB 설정
├── tests/
├── requirements.txt
└── .env
```

**적합한 경우:** 중규모 API, 마이크로서비스

---

### **패턴 3: Large Project (엔터프라이즈)**

```
my-api/
├── app/
│   ├── main.py
│   ├── core/            # 핵심 설정
│   │   ├── config.py
│   │   ├── security.py
│   │   └── dependencies.py
│   ├── api/             # API 레이어
│   │   ├── deps.py
│   │   └── v1/
│   │       ├── api.py
│   │       └── endpoints/
│   ├── models/          # 도메인 모델
│   ├── schemas/         # Pydantic 스키마
│   ├── services/        # 비즈니스 로직
│   ├── repositories/    # 데이터 접근
│   └── utils/           # 유틸리티
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── alembic/             # DB 마이그레이션
├── scripts/             # 스크립트
├── requirements.txt
└── docker-compose.yml
```

**적합한 경우:** 대규모 시스템, 복잡한 도메인

---

##  G-Navi AI API 구조 선택 이유

G-Navi는 **패턴 3 (Large Project) + AI 특화 구조**를 사용합니다.

```
g-navi-ai-api/
├── app/
│   ├── main.py              # FastAPI 엔트리포인트
│   ├── config/              # 설정 관리
│   ├── core/                # 핵심 기능
│   ├── api/                 # API 레이어
│   │   └── v1/
│   │       └── endpoints/
│   ├── models/              # Pydantic 모델
│   ├── services/            # 비즈니스 로직
│   ├── graphs/              # 🆕 LangGraph 워크플로우 (AI 특화)
│   │   ├── agents/          # 🆕 AI 에이전트
│   │   └── nodes/           # 🆕 워크플로우 노드
│   └── utils/               # 유틸리티
├── k8s/                     # Kubernetes 배포
└── requirements.txt
```

**왜 이 구조를 선택했는가?**

1. **복잡한 AI 워크플로우**
   - `graphs/`: LangGraph 전용 디렉토리
   - 일반 API와 분리하여 관리 용이

2. **확장성**
   - API 버전 관리 (`v1/`, `v2/`)
   - 새로운 엔드포인트 추가 용이

3. **유지보수성**
   - 계층별 책임 명확
   - 테스트 용이

---

## 📂 디렉토리별 역할 상세

### **1. `app/main.py` - FastAPI 앱 엔트리포인트**

```python
from fastapi import FastAPI
from app.api.v1.api import api_router
from app.core.config import settings

app = FastAPI(
    title="G-Navi AI API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 라우터 등록
app.include_router(api_router, prefix="/api/v1")

# 이벤트 핸들러
@app.on_event("startup")
async def startup_event():
    # 초기화 로직
    pass

@app.on_event("shutdown")
async def shutdown_event():
    # 정리 로직
    pass
```

**역할:**
- FastAPI 앱 초기화
- 라우터 등록
- 미들웨어 설정
- 라이프사이클 이벤트

---

### **2. `app/config/` - 설정 관리**

```python
# app/config/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """환경변수 기반 설정"""

    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "G-Navi AI API"

    # OpenAI
    OPENAI_API_KEY: str

    # ChromaDB
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000

    # Storage
    APP_STORAGE_PVC_PATH: str = "/mnt/gnavi"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

**패턴:**
- Pydantic Settings로 타입 안전성
- `.env` 파일 자동 로드
- 환경별 설정 분리 가능

---

### **3. `app/core/` - 핵심 기능**

```python
# app/core/dependencies.py
from fastapi import Depends, HTTPException
from typing import Optional

async def get_current_user(
    token: str = Depends(oauth2_scheme)
) -> User:
    """현재 사용자 가져오기 (의존성 주입)"""
    user = await verify_token(token)
    if not user:
        raise HTTPException(status_code=401)
    return user

# app/core/security.py
def verify_password(plain: str, hashed: str) -> bool:
    """비밀번호 검증"""
    pass

def get_password_hash(password: str) -> str:
    """비밀번호 해싱"""
    pass
```

**역할:**
- 인증/인가
- 의존성 주입
- 공통 유틸리티

---

### **4. `app/api/` - API 레이어**

```python
# app/api/v1/api.py
from fastapi import APIRouter
from app.api.v1.endpoints import message, conversation, health

api_router = APIRouter()

api_router.include_router(
    message.router,
    prefix="/message",
    tags=["message"]
)

api_router.include_router(
    conversation.router,
    prefix="/conversation",
    tags=["conversation"]
)

# app/api/v1/endpoints/message.py
from fastapi import APIRouter, Depends
from app.models.message import MessageRequest, MessageResponse
from app.services.chat_service import ChatService

router = APIRouter()

@router.post("/", response_model=MessageResponse)
async def send_message(
    request: MessageRequest,
    chat_service: ChatService = Depends()
):
    """메시지 전송"""
    return await chat_service.send_message(request)
```

**구조:**
```
api/
├── deps.py              # API 레벨 의존성
└── v1/                  # API v1
    ├── api.py           # 라우터 통합
    └── endpoints/       # 개별 엔드포인트
        ├── message.py
        ├── conversation.py
        └── health.py
```

**패턴:**
- **버전별 분리**: v1, v2 독립적 관리
- **엔드포인트 분리**: 각 도메인별 라우터
- **태그 사용**: Swagger 문서 그룹화

---

### **5. `app/models/` - Pydantic 모델**

```python
# app/models/message.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class MessageRequest(BaseModel):
    """메시지 요청 모델"""
    session_id: str = Field(..., description="세션 ID")
    user_id: int = Field(..., gt=0, description="사용자 ID")
    message: str = Field(..., min_length=1, description="메시지 내용")
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "abc123",
                "user_id": 1,
                "message": "커리어 전환 방법이 궁금해요"
            }
        }

class MessageResponse(BaseModel):
    """메시지 응답 모델"""
    message_id: str
    response: str
    sources: list[str] = []
    created_at: datetime

    class Config:
        from_attributes = True
```

**역할:**
- 요청/응답 검증
- 타입 안전성
- 자동 문서화

**패턴:**
- Request/Response 모델 분리
- Field로 검증 규칙 명시
- Config로 Swagger 예시 제공

---

### **6. `app/services/` - 비즈니스 로직**

```python
# app/services/chat_service.py
from typing import Optional
from app.models.message import MessageRequest, MessageResponse
from app.graphs.graph_builder import ChatGraphBuilder

class ChatService:
    """채팅 서비스"""

    def __init__(self):
        self.graph = ChatGraphBuilder().build_graph()

    async def send_message(
        self,
        request: MessageRequest
    ) -> MessageResponse:
        """메시지 전송 및 AI 응답 생성"""

        # 1. 입력 검증
        self._validate_input(request)

        # 2. Graph 실행
        result = await self.graph.ainvoke({
            "session_id": request.session_id,
            "user_message": request.message,
        })

        # 3. 응답 생성
        return MessageResponse(
            message_id=result["message_id"],
            response=result["final_response"],
            sources=result.get("sources", []),
            created_at=datetime.now()
        )

    def _validate_input(self, request: MessageRequest):
        """입력 검증"""
        if len(request.message) > 1000:
            raise ValueError("Message too long")
```

**패턴:**
- **단일 책임**: 하나의 도메인만 관리
- **의존성 주입**: 생성자로 의존성 받기
- **에러 처리**: 비즈니스 예외 정의

---

### **7. `app/graphs/` - AI 워크플로우 (G-Navi 특화)**

```python
# app/graphs/graph_builder.py
from langgraph.graph import StateGraph
from app.graphs.state import ChatState
from app.graphs.nodes.intent_analysis import IntentAnalysisNode

class ChatGraphBuilder:
    """LangGraph 워크플로우 빌더"""

    def build_graph(self) -> StateGraph:
        workflow = StateGraph(ChatState)

        # 노드 추가
        workflow.add_node("analyze_intent", IntentAnalysisNode())
        workflow.add_node("retrieve_data", DataRetrievalNode())

        # 엣지 추가
        workflow.add_edge("analyze_intent", "retrieve_data")

        return workflow.compile()
```

**구조:**
```
graphs/
├── graph_builder.py     # 워크플로우 빌더
├── state.py             # 상태 정의
├── agents/              # AI 에이전트
│   ├── retriever.py
│   └── analyzer.py
└── nodes/               # 워크플로우 노드
    ├── intent_analysis.py
    └── data_retrieval.py
```

**왜 분리했는가?**
- AI 로직의 복잡도가 높음
- 일반 API 로직과 독립적
- LangGraph 특화 구조 필요

---

### **8. `app/utils/` - 유틸리티**

```python
# app/utils/text_processor.py
def clean_text(text: str) -> str:
    """텍스트 정제"""
    pass

# app/utils/embeddings.py
def generate_embedding(text: str) -> list[float]:
    """임베딩 생성"""
    pass
```

**역할:**
- 재사용 가능한 함수
- 도메인 독립적 기능

---

## 🔄 Request Flow (요청 흐름)

### 전체 플로우 예시

```
1. HTTP Request
   ↓
2. FastAPI Router (app/api/v1/endpoints/message.py)
   - 요청 검증 (Pydantic)
   - 의존성 주입
   ↓
3. Service Layer (app/services/chat_service.py)
   - 비즈니스 로직 실행
   ↓
4. Graph Layer (app/graphs/graph_builder.py)
   - LangGraph 워크플로우 실행
   ↓
5. Agent Layer (app/graphs/agents/retriever.py)
   - AI 작업 수행
   ↓
6. Data Layer (ChromaDB, PostgreSQL)
   - 데이터 저장/조회
   ↓
7. Response
   - Pydantic 모델로 직렬화
   - HTTP 응답 반환
```

---

## 📋 Best Practices

### **1. 의존성 주입 활용**

```python
# - 나쁜 예
@router.post("/message")
async def send_message(request: MessageRequest):
    service = ChatService()  # 매번 생성
    return await service.send_message(request)

#  좋은 예
@router.post("/message")
async def send_message(
    request: MessageRequest,
    service: ChatService = Depends(get_chat_service)
):
    return await service.send_message(request)
```

### **2. 환경변수 관리**

```python
# - 나쁜 예
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

#  좋은 예
from app.config.settings import settings
api_key = settings.OPENAI_API_KEY  # 타입 안전, 검증됨
```

### **3. 에러 처리**

```python
# app/core/exceptions.py
class BusinessException(Exception):
    """비즈니스 예외"""
    pass

# app/api/v1/endpoints/message.py
from fastapi import HTTPException

@router.post("/message")
async def send_message(request: MessageRequest):
    try:
        return await service.send_message(request)
    except BusinessException as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### **4. 로깅**

```python
import logging

logger = logging.getLogger(__name__)

@router.post("/message")
async def send_message(request: MessageRequest):
    logger.info(f"Received message from user {request.user_id}")
    try:
        result = await service.send_message(request)
        logger.info(f"Message processed successfully")
        return result
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        raise
```

---

##  면접 시 설명 포인트

**"FastAPI 프로젝트 구조를 어떻게 설계했나요?"**

```
1. 계층형 아키텍처
   - API, Service, Graph, Agent 레이어 분리
   - 각 레이어의 책임 명확화

2. 도메인 중심 설계
   - graphs/: AI 워크플로우 (핵심 도메인)
   - api/: HTTP 인터페이스
   - services/: 비즈니스 로직

3. 확장 가능한 구조
   - 버전별 API 분리 (v1, v2)
   - 노드 기반 워크플로우 (추가/수정 용이)

4. 표준 패턴 준수
   - FastAPI Best Practices
   - Clean Architecture 원칙
   - SOLID 원칙
```

---

**작성자:** 양승우
**최종 수정일:** 2025.07.01
