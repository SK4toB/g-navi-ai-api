# G-Navi AI API 아키텍처 및 디렉토리 구조

FastAPI 기반 AI 백엔드 서비스 구조 설명

**작성자:** 양승우
**작성일:** 2025.07.01

---

## 📁 디렉토리 구조 (Directory Structure)

```
g-navi-ai-api/
├── app/                          # 메인 애플리케이션 코드
│   ├── main.py                   # FastAPI 앱 엔트리포인트
│   ├── config/                   # 설정 관리
│   │   └── settings.py           # 환경변수, 설정값
│   ├── core/                     # 핵심 기능
│   │   └── dependencies.py       # 의존성 주입
│   ├── api/                      # API 라우터
│   │   ├── deps.py               # API 의존성
│   │   └── v1/                   # API v1 엔드포인트
│   │       ├── api.py            # 라우터 통합
│   │       └── endpoints/        # 개별 엔드포인트
│   │           ├── message.py    # 메시지 전송
│   │           ├── conversation.py
│   │           ├── health.py     # Health Check
│   │           ├── embedding.py  # 임베딩 생성
│   │           └── ...
│   ├── models/                   # Pydantic 모델
│   │   ├── chat.py               # 채팅 모델
│   │   └── message.py            # 메시지 모델
│   ├── services/                 # 비즈니스 로직
│   │   ├── chat_service.py       # 채팅 관리
│   │   ├── bot_message.py        # 봇 응답 생성
│   │   ├── message_processor.py  # 메시지 처리
│   │   └── chroma_service.py     # ChromaDB 연동
│   ├── graphs/                   # LangGraph 워크플로우
│   │   ├── graph_builder.py      # 그래프 빌더
│   │   ├── state.py              # 상태 정의
│   │   ├── agents/               # 에이전트 구현
│   │   │   ├── retriever.py      # 검색 에이전트
│   │   │   ├── analyzer.py       # 의도 분석
│   │   │   ├── formatter.py      # 응답 포맷팅
│   │   │   └── k8s_chroma_adapter.py
│   │   └── nodes/                # 워크플로우 노드
│   │       ├── intent_analysis.py
│   │       ├── data_retrieval.py
│   │       ├── response_formatting.py
│   │       └── career_consultation/  # 커리어 상담
│   │           ├── career_positioning.py
│   │           ├── path_selection.py
│   │           └── learning_roadmap.py
│   └── utils/                    # 유틸리티
│       ├── career_data_processor.py
│       ├── education_data_processor.py
│       └── upload_*_to_pod_chroma.py
├── k8s/                          # Kubernetes 배포 설정
│   ├── deployment.yaml
│   └── service.yaml
├── requirements.txt              # Python 의존성
├── Dockerfile                    # 컨테이너 이미지 빌드
└── README.md                     # 프로젝트 문서

```

---

## 🏛️ 아키텍처 패턴

### 1. **계층형 아키텍처 (Layered Architecture)**

```
┌─────────────────────────────────────────┐
│         API Layer (FastAPI)             │  ← HTTP 요청 처리
├─────────────────────────────────────────┤
│       Service Layer (Services)          │  ← 비즈니스 로직
├─────────────────────────────────────────┤
│    Graph Layer (LangGraph Workflow)     │  ← AI 워크플로우
├─────────────────────────────────────────┤
│     Agent Layer (Retriever, etc)        │  ← AI 에이전트
├─────────────────────────────────────────┤
│   Data Layer (ChromaDB, PostgreSQL)     │  ← 데이터 저장
└─────────────────────────────────────────┘
```

---

##  주요 컴포넌트 설명

### **1. API Layer (`app/api/`)**

FastAPI 라우터와 엔드포인트 정의

**디자인 패턴:**
- **Router Pattern**: 버전별 API 분리 (v1, v2)
- **Dependency Injection**: FastAPI의 `Depends()` 활용

**주요 파일:**

```python
# app/api/v1/api.py
from fastapi import APIRouter
from app.api.v1.endpoints import message, conversation, health

api_router = APIRouter()
api_router.include_router(message.router, prefix="/message", tags=["message"])
api_router.include_router(conversation.router, prefix="/conversation", tags=["conversation"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
```

**엔드포인트 예시:**

| Endpoint | Method | 설명 |
|----------|--------|------|
| `/api/v1/message` | POST | 메시지 전송 및 AI 응답 |
| `/api/v1/conversation/{id}` | GET | 대화 내역 조회 |
| `/api/v1/health` | GET | 헬스체크 |
| `/api/v1/embedding` | POST | 텍스트 임베딩 생성 |

**특징:**
- RESTful API 설계
- Pydantic 모델로 요청/응답 검증
- Swagger 자동 문서화 (`/docs`)

---

### **2. Service Layer (`app/services/`)**

비즈니스 로직과 외부 시스템 연동

**주요 서비스:**

#### **A. ChatService** (`chat_service.py`)
```python
class ChatService:
    """
    채팅 세션 관리 및 메시지 처리

    책임:
    - 세션 생성/삭제
    - 메시지 히스토리 관리
    - Graph 워크플로우 실행
    """

    async def send_message(self, session_id: str, message: str):
        # 1. 세션 검증
        # 2. Graph 실행
        # 3. 응답 반환
```

#### **B. MessageProcessor** (`message_processor.py`)
```python
class MessageProcessor:
    """
    메시지 전처리 및 후처리

    책임:
    - 입력 메시지 정제
    - 컨텍스트 준비
    - 응답 포맷팅
    """
```

#### **C. ChromaService** (`chroma_service.py`)
```python
class ChromaService:
    """
    ChromaDB 연동

    책임:
    - 벡터 저장/검색
    - 컬렉션 관리
    """
```

**패턴:**
- **Service Layer Pattern**: 비즈니스 로직 캡슐화
- **Repository Pattern**: 데이터 접근 추상화

---

### **3. Graph Layer (`app/graphs/`)**

LangGraph 기반 AI 워크플로우

**핵심 개념:**
```python
# app/graphs/graph_builder.py
class ChatGraphBuilder:
    """
    LangGraph 워크플로우 빌더

    플로우:
    1. message_check → 메시지 검증
    2. analyze_intent → 의도 분석
    3. retrieve_data → 데이터 검색
    4. format_response → 응답 생성
    """

    def build_graph(self) -> StateGraph:
        workflow = StateGraph(ChatState)

        # 노드 추가
        workflow.add_node("message_check", MessageCheckNode())
        workflow.add_node("analyze_intent", IntentAnalysisNode())
        workflow.add_node("retrieve_data", DataRetrievalNode())

        # 엣지 추가 (플로우 정의)
        workflow.add_edge("message_check", "analyze_intent")
        workflow.add_conditional_edges(
            "analyze_intent",
            self._determine_flow,
            {"general": "retrieve_data", "consultation": "collect_user_info"}
        )

        return workflow.compile()
```

**State 관리:**
```python
# app/graphs/state.py
class ChatState(TypedDict):
    """워크플로우 전체에서 공유되는 상태"""

    session_id: str
    user_message: str
    intent_analysis: Dict[str, Any]
    retrieved_data: List[Document]
    final_response: str
    metadata: Dict[str, Any]
```

---

### **4. Agents (`app/graphs/agents/`)**

AI 기능을 수행하는 에이전트

#### **A. Retriever Agent** (`retriever.py`)
```python
class CareerEnsembleRetrieverAgent:
    """
    하이브리드 검색 에이전트

    기능:
    - 벡터 검색 (ChromaDB)
    - 키워드 검색 (BM25)
    - Ensemble 결합
    """

    def retrieve(self, query: str, k: int = 5):
        # 1. 벡터 검색
        vector_results = self.vectorstore.similarity_search(query, k)

        # 2. BM25 검색
        bm25_results = self.bm25_retriever.get_relevant_documents(query)

        # 3. Ensemble (가중치 0.5:0.5)
        return self.ensemble_retriever.invoke(query)
```

#### **B. Analyzer Agent** (`analyzer.py`)
```python
class IntentAnalysisAgent:
    """
    사용자 의도 분석 에이전트

    분류:
    - 일반 질문
    - 커리어 상담
    - 교육과정 문의
    """
```

#### **C. Formatter Agent** (`formatter.py`)
```python
class ResponseFormattingAgent:
    """
    응답 포맷팅 에이전트

    기능:
    - 프롬프트 생성
    - 컨텍스트 삽입
    - 마크다운 변환
    """
```

---

### **5. Nodes (`app/graphs/nodes/`)**

워크플로우의 개별 단계

**노드 구조:**
```python
# 노드 베이스 패턴
class BaseNode:
    def __call__(self, state: ChatState) -> ChatState:
        # 1. 입력 검증
        # 2. 로직 실행
        # 3. 상태 업데이트
        return updated_state
```

**노드 분류:**

| 노드 | 역할 |
|------|------|
| `message_check.py` | 입력 메시지 검증 |
| `intent_analysis.py` | 의도 분석 |
| `data_retrieval.py` | RAG 데이터 검색 |
| `response_formatting.py` | 응답 생성 |
| `diagram_generation.py` | Mermaid 다이어그램 생성 |

**커리어 상담 노드:**
```
career_consultation/
├── career_positioning.py   # 커리어 포지셔닝 분석
├── path_selection.py        # 경로 선택
├── path_deepening.py        # 심화 논의
├── learning_roadmap.py      # 학습 로드맵
└── consultation_summary.py  # 상담 요약
```

---

### **6. Models (`app/models/`)**

Pydantic 모델 정의

```python
# app/models/message.py
from pydantic import BaseModel

class MessageRequest(BaseModel):
    """메시지 요청 모델"""
    session_id: str
    user_id: int
    message: str
    metadata: Optional[Dict[str, Any]] = None

class MessageResponse(BaseModel):
    """메시지 응답 모델"""
    message_id: str
    response: str
    sources: List[str] = []
    metadata: Dict[str, Any] = {}
```

**특징:**
- 타입 안정성
- 자동 검증
- JSON 직렬화/역직렬화

---

### **7. Utils (`app/utils/`)**

데이터 처리 및 초기화 유틸리티

```python
# app/utils/career_data_processor.py
class CareerDataProcessor:
    """
    커리어 데이터 처리 및 벡터화

    기능:
    - CSV 파일 로드
    - 텍스트 전처리
    - OpenAI 임베딩 생성
    - ChromaDB 저장
    """

    def process_and_store(self, csv_path: str):
        # 1. CSV 로드
        df = pd.read_csv(csv_path)

        # 2. 텍스트 생성
        documents = self._create_documents(df)

        # 3. 임베딩 생성 (캐싱)
        embeddings = self._generate_embeddings(documents)

        # 4. ChromaDB 저장
        self._store_to_chromadb(documents, embeddings)
```

---

## 🔄 요청 처리 흐름 (Request Flow)

### 일반 대화 플로우

```
1. 사용자 요청
   ↓
2. FastAPI Endpoint (/api/v1/message)
   ↓
3. ChatService.send_message()
   ↓
4. Graph 실행 시작
   ├─ MessageCheckNode: 입력 검증
   ├─ IntentAnalysisNode: 의도 분석
   ├─ DataRetrievalNode: RAG 검색
   │   ├─ CareerRetriever: 커리어 사례 검색
   │   └─ EducationRetriever: 교육과정 검색
   ├─ ResponseFormattingNode: 프롬프트 생성
   ├─ OpenAIResponseNode: GPT-4o 호출
   └─ DiagramGenerationNode: 다이어그램 생성 (선택)
   ↓
5. 응답 반환
```

### 커리어 상담 플로우

```
1. 사용자 요청 (커리어 상담)
   ↓
2. Intent Analysis → "career_consultation"
   ↓
3. 커리어 상담 노드 순차 실행
   ├─ UserInfoCollectionNode: 사용자 정보 수집
   ├─ CareerPositioningNode: 현재 위치 분석
   ├─ PathSelectionNode: 경로 선택
   ├─ PathDeepeningNode: 경로 심화
   ├─ LearningRoadmapNode: 학습 계획
   └─ ConsultationSummaryNode: 상담 요약
   ↓
4. 응답 반환
```

---

##  설계 원칙

### 1. **관심사 분리 (Separation of Concerns)**
- API, Service, Graph, Agent 레이어 분리
- 각 레이어는 독립적 책임

### 2. **의존성 역전 (Dependency Inversion)**
```python
# - 나쁜 예: 직접 의존
class ChatService:
    def __init__(self):
        self.chromadb = ChromaDB()  # 강결합

#  좋은 예: 추상화에 의존
class ChatService:
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store  # 느슨한 결합
```

### 3. **단일 책임 원칙 (Single Responsibility)**
- 각 노드는 하나의 작업만 수행
- Service는 하나의 도메인만 관리

### 4. **개방-폐쇄 원칙 (Open-Closed)**
```python
# 새로운 노드 추가 시 기존 코드 수정 불필요
workflow.add_node("new_feature", NewFeatureNode())
workflow.add_edge("intent_analysis", "new_feature")
```

---

##  의존성 관리

### **requirements.txt 구조**

```txt
# FastAPI 프레임워크
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0

# AI/ML
openai==1.3.0
langchain==0.1.0
langgraph==0.0.20
chromadb==0.4.24

# 데이터 처리
pandas==2.1.3
numpy==1.26.2

# 벡터 검색
sentence-transformers==2.2.2

# 유틸리티
python-dotenv==1.0.0
aiohttp==3.9.0
```

---

## 🔐 환경변수 관리

```python
# app/config/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Keys
    OPENAI_API_KEY: str

    # ChromaDB
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    CHROMA_AUTH_CREDENTIALS: str = ""

    # Storage
    APP_STORAGE_PVC_PATH: str = "/mnt/gnavi"

    class Config:
        env_file = ".env"

settings = Settings()
```

---

##  테스트 구조 (권장)

```
tests/
├── unit/                     # 단위 테스트
│   ├── test_agents.py
│   ├── test_nodes.py
│   └── test_services.py
├── integration/              # 통합 테스트
│   ├── test_graph_flow.py
│   └── test_api_endpoints.py
└── e2e/                      # E2E 테스트
    └── test_chat_scenario.py
```

---

## 💡 면접 시 강조 포인트

**"디렉토리 구조를 어떻게 설계했나요?"**

```
1. 계층형 아키텍처 채택
   - API → Service → Graph → Agent
   - 각 레이어는 독립적 책임

2. 도메인 기반 분류
   - graphs/: AI 워크플로우 로직
   - services/: 비즈니스 로직
   - api/: HTTP 인터페이스

3. 확장 가능한 구조
   - 새로운 노드 추가 용이
   - 버전별 API 분리 (v1, v2)

4. 유지보수성 고려
   - 파일명으로 역할 명확화
   - 관련 코드 그룹화
```

---

**작성자:** 양승우
**최종 수정일:** 2025.07.01
