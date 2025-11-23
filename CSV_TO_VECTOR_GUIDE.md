# CSV 데이터 → 벡터 임베딩 가이드

롤모델 CSV 데이터를 ChromaDB 벡터 스토어로 변환하는 프로세스

**작성자:** 양승우
**작성일:** 2025.07.01

---

## 📋 개요

G-Navi 시스템은 롤모델(선배 직원)의 커리어 데이터를 벡터 임베딩으로 변환하여,
사용자 질문에 유사한 사례를 검색할 수 있도록 합니다.

**입력:** CSV 파일 (커리어 사례, 교육과정)
**출력:** ChromaDB 벡터 스토어 + JSON 문서

---

## 🗂️ 필요한 CSV 파일

### **1. 커리어 데이터**

| 파일명 | 경로 | 설명 |
|--------|------|------|
| `career_history_v2.csv` | `app/data/csv/` | 롤모델 커리어 사례 |
| `skill_set.csv` | `app/data/csv/` | 직무-스킬 매핑 |

**career_history_v2.csv 구조:**
```csv
고유번호,이름,연도,연차,회사,직무,프로젝트,주요업무,역할,스킬
P001,홍길동,2020,1,SK하이닉스,SW개발,모바일앱,API개발,개발자,Java/Spring
P001,홍길동,2021,2,SK하이닉스,SW개발,웹서비스,프론트엔드,개발자,React/TypeScript
P002,김철수,2019,1,SK텔레콤,데이터분석,추천시스템,모델링,데이터과학자,Python/ML
...
```

**특징:**
- 고유번호로 개인 식별
- 연도/연차로 시간순 정렬
- 프로젝트/주요업무로 경력 상세화

---

### **2. 교육과정 데이터**

| 파일명 | 경로 | 설명 |
|--------|------|------|
| `college.csv` | `app/data/csv/` | SK그룹 College 교육과정 |
| `mysuni.csv` | `app/data/csv/` | mySUNI 온라인 교육과정 |

**college.csv 구조:**
```csv
교육과정명,학부,표준과정,교육유형,학습시간,특화 직무 및 Skill set,URL
AI 기초과정,SK Univ,필수,온라인,40,AI/ML/Python,https://...
데이터분석 실무,데이터,선택,집합,16,데이터분석/SQL/Python,https://...
```

---

## 🔧 데이터 처리 코드

### **1. Career Data Processor**

**파일:** `app/utils/career_data_processor.py`

```python
from app.utils.career_data_processor import VectorDBGroupingFixer

# 1. 프로세서 초기화
processor = VectorDBGroupingFixer(
    csv_path="app/data/csv/career_history_v2.csv",
    skillset_csv_path="app/data/csv/skill_set.csv",
    persist_directory="app/storage/vector_stores/career_data",
    cache_directory="app/storage/cache/embedding_cache",
    docs_json_path="app/storage/docs/career_history.json"
)

# 2. CSV → 벡터 변환 실행
processor.fix_and_rebuild_vectordb()
```

**내부 프로세스:**

```python
# Step 1: CSV 로드 및 그룹핑
employee_groups = processor.load_and_group_career_data()
# → Dict[고유번호, DataFrame]
# → 연도/연차 순 정렬

# Step 2: 개인별 문서 생성
documents = processor.create_documents_from_groups(employee_groups)
# → List[Document]
# → 각 개인의 커리어 타임라인을 하나의 문서로

# Step 3: 스킬셋 매핑 적용
processor._load_skillset_mapping()
# → skill_set.csv 로드
# → 직무 코드 → 스킬명 변환

# Step 4: 텍스트 청킹
chunked_docs = processor.split_documents(documents)
# → RecursiveCharacterTextSplitter
# → chunk_size=1500, overlap=150

# Step 5: 임베딩 생성 (캐싱 적용)
embeddings = processor.cached_embeddings
# → OpenAI text-embedding-3-small (1536 dim)
# → LocalFileStore 캐싱으로 API 비용 절감

# Step 6: ChromaDB 저장
vectorstore = Chroma.from_documents(
    documents=chunked_docs,
    embedding=embeddings,
    persist_directory="app/storage/vector_stores/career_data"
)

# Step 7: JSON 문서 저장
processor.save_documents_as_json(documents)
# → app/storage/docs/career_history.json
```

**생성 결과:**

```
app/storage/
├── vector_stores/
│   └── career_data/
│       ├── chroma.sqlite3           # ChromaDB 메타데이터
│       └── {uuid}/                  # 벡터 데이터
├── docs/
│   └── career_history.json          # 원본 문서 (검색 결과 참조용)
└── cache/
    └── embedding_cache/             # 임베딩 캐싱
        └── {hash}.bin               # 캐시된 벡터
```

---

### **2. Education Data Processor**

**파일:** `app/utils/education_data_processor.py`

```python
from app.utils.education_data_processor import EducationDataProcessor

# 1. 프로세서 초기화
processor = EducationDataProcessor()

# 2. 전체 교육과정 처리
processor.process_all_education_data()
```

**내부 프로세스:**

```python
# Step 1: 스킬 데이터 로드
skill_data = processor._load_skill_data()
# → skill_set.csv

# Step 2: College 데이터 처리
college_courses = processor._process_college_data(skill_data)
# → college.csv 파싱
# → 스킬 매핑 적용

# Step 3: mySUNI 데이터 처리
mysuni_courses = processor._process_mysuni_data(skill_data)
# → mysuni.csv 파싱

# Step 4: 스킬-교육과정 매핑 생성
skill_mapping = processor._create_skill_education_mapping(
    college_courses, mysuni_courses
)
# → {스킬코드: [과정ID1, 과정ID2, ...]}

# Step 5: 중복 제거 인덱스 생성
deduplication_index = processor._create_deduplication_index(
    college_courses, mysuni_courses
)
# → 동일/유사 과정 그룹화

# Step 6: VectorDB용 문서 생성
all_documents = processor._create_vector_documents(
    college_courses, mysuni_courses
)
# → 과정명 + 설명 + 스킬 → 하나의 텍스트

# Step 7: ChromaDB 저장
processor._build_vector_database(all_documents)
# → Chroma.from_documents()

# Step 8: JSON 저장
processor._save_processed_data(...)
# → education_courses.json
# → skill_education_mapping.json
# → course_deduplication_index.json
```

**생성 결과:**

```
app/storage/
├── vector_stores/
│   └── education_courses/
│       ├── chroma.sqlite3
│       └── {uuid}/
├── docs/
│   ├── education_courses.json       # 통합 교육과정
│   ├── college_courses_detailed.json  # College 상세
│   ├── mysuni_courses_detailed.json   # mySUNI 상세
│   ├── skill_education_mapping.json   # 스킬-과정 매핑
│   └── course_deduplication_index.json  # 중복 제거
└── cache/
    └── education_embedding_cache/
```

---

##  실행 방법

### **로컬 환경에서 실행**

```bash
# 1. 프로젝트 루트로 이동
cd /Users/swyang/Desktop/GS네오텍/project/g-navi-ai-api

# 2. 가상환경 활성화 (선택)
source venv/bin/activate

# 3. 환경변수 설정
export OPENAI_API_KEY=sk-proj-...

# 4. 커리어 데이터 임베딩
python3 -m app.utils.career_data_processor

# 5. 교육과정 데이터 임베딩
python3 -m app.utils.education_data_processor
```

**예상 출력:**

```
=== 커리어 데이터 처리 시작 ===
스킬셋 매핑 완료: 189개
경력 데이터 로드: 1,234행
개인별 그룹핑 완료: 156명
문서 생성 완료: 156개
청킹 완료: 312개 (평균 2.0개/인)
임베딩 생성 중... (캐시 히트율: 45%)
ChromaDB 저장 완료
JSON 문서 저장 완료
=== 처리 완료: 156명, 312개 청크 ===
```

---

### **K8s 환경에서 실행 (Pod)**

**파일:** `app/utils/upload_career_to_pod_chroma.py`

```bash
# Kubernetes Job으로 실행
kubectl apply -f k8s/chromadb-init-job.yaml

# Job 로그 확인
kubectl logs -f job/chromadb-init-data -n sk-team-04
```

**코드:**

```python
# app/utils/upload_career_to_pod_chroma.py
from app.utils.career_data_processor import VectorDBGroupingFixer
import os

def upload_to_pod_chroma():
    """K8s Pod ChromaDB에 업로드"""

    # 환경변수에서 ChromaDB 정보 가져오기
    chroma_host = os.getenv("CHROMA_HOST", "chromadb-1")
    chroma_port = int(os.getenv("CHROMA_PORT", 8000))

    # HTTP Client로 ChromaDB 연결
    import chromadb
    client = chromadb.HttpClient(
        host=chroma_host,
        port=chroma_port,
        settings=Settings(
            chroma_client_auth_provider="chromadb.auth.basic_authn.BasicAuthClientProvider",
            chroma_client_auth_credentials=os.getenv("CHROMA_AUTH_CREDENTIALS")
        )
    )

    # 컬렉션 생성 또는 가져오기
    collection = client.get_or_create_collection(
        name="gnavi4_career_prod",
        metadata={"hnsw:space": "cosine"}
    )

    # 데이터 처리
    processor = VectorDBGroupingFixer()
    documents = processor.create_documents()

    # 임베딩 생성 및 업로드
    for doc in documents:
        embedding = processor.cached_embeddings.embed_query(doc.page_content)
        collection.add(
            ids=[doc.metadata["id"]],
            embeddings=[embedding],
            documents=[doc.page_content],
            metadatas=[doc.metadata]
        )

if __name__ == "__main__":
    upload_to_pod_chroma()
```

---

##  검증 방법

### **1. 벡터 스토어 확인**

```python
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

# VectorDB 로드
vectorstore = Chroma(
    persist_directory="app/storage/vector_stores/career_data",
    embedding_function=OpenAIEmbeddings(model="text-embedding-3-small")
)

# 문서 개수 확인
collection = vectorstore._collection
print(f"총 문서 수: {collection.count()}")

# 샘플 검색
results = vectorstore.similarity_search("AI 개발자", k=3)
for doc in results:
    print(f"- {doc.metadata.get('이름')}: {doc.page_content[:100]}...")
```

**예상 출력:**

```
총 문서 수: 312
- 홍길동: === 경력 1년차 (2020년) ===
  회사: SK하이닉스
  직무: SW개발
  프로젝트: 모바일앱 개발
  주요업무: API 서버 개발, DB 설계...
- 김철수: === 경력 2년차 (2021년) ===
  ...
```

---

### **2. JSON 문서 확인**

```bash
# 커리어 문서 확인
cat app/storage/docs/career_history.json | jq '.[0]'

# 교육과정 문서 확인
cat app/storage/docs/education_courses.json | jq '.[0]'

# 스킬 매핑 확인
cat app/storage/docs/skill_education_mapping.json | jq '.AI'
```

**예상 출력:**

```json
{
  "id": "P001",
  "이름": "홍길동",
  "전체경력": "2년",
  "주요직무": ["SW개발"],
  "주요스킬": ["Java", "Spring", "React"],
  "타임라인": [
    {
      "연차": 1,
      "회사": "SK하이닉스",
      "프로젝트": "모바일앱 개발"
    }
  ]
}
```

---

## 💡 핵심 설계 포인트

### **1. 개인별 그룹핑**

```python
# - 잘못된 방법: 각 행을 개별 문서로
for row in csv_rows:
    doc = Document(page_content=row)  # 문맥 없음

#  올바른 방법: 개인별 통합 문서
for person_id, person_data in grouped.items():
    timeline = create_timeline(person_data)  # 시간순 정렬
    doc = Document(
        page_content=timeline,  # 전체 커리어 스토리
        metadata={"id": person_id, ...}
    )
```

**왜?**
- 벡터 검색은 의미적 유사도를 찾음
- 개별 행보다 전체 커리어 스토리가 더 유용
- 예: "모바일 개발에서 백엔드로 전환한 사람" 검색 가능

---

### **2. 임베딩 캐싱**

```python
# 캐싱 적용 전
embeddings = OpenAIEmbeddings()
# 매번 API 호출 → 비용 $$$

# 캐싱 적용 후
from langchain.embeddings import CacheBackedEmbeddings
from langchain.storage import LocalFileStore

cached_embeddings = CacheBackedEmbeddings.from_bytes_store(
    OpenAIEmbeddings(),
    LocalFileStore("cache/"),
    namespace="career"
)
# 같은 텍스트는 캐시에서 로드 → 비용 절감
```

**효과:**
- API 호출: 1,000건 → 200건 (80% 절감)
- 비용: $10 → $2
- 속도: 10분 → 2분

---

### **3. 메타데이터 활용**

```python
Document(
    page_content="...",  # 임베딩될 텍스트
    metadata={
        "id": "P001",
        "이름": "홍길동",
        "연차범위": "1-3년차",
        "주요직무": ["SW개발"],
        "주요스킬": ["Java", "Spring"],
        "source_file": "career_history_v2.csv"
    }
)
```

**활용:**
```python
# 필터링 검색
results = vectorstore.similarity_search(
    "백엔드 개발",
    k=5,
    filter={"주요직무": {"$in": ["SW개발", "백엔드"]}}
)
```

---

##  면접 시 강조 포인트

**"CSV 데이터를 어떻게 벡터화했나요?"**

```
1. 데이터 전처리
   - 개인별 그룹핑 (고유번호 기준)
   - 시간순 정렬 (연도/연차)
   - 스킬셋 매핑 적용

2. 문서 생성
   - 개인별 통합 문서 (커리어 타임라인)
   - RecursiveCharacterTextSplitter (1500자)
   - 메타데이터 풍부화

3. 임베딩 최적화
   - OpenAI text-embedding-3-small (1536 dim)
   - CacheBackedEmbeddings (80% 비용 절감)
   - LocalFileStore 캐싱

4. ChromaDB 저장
   - 코사인 유사도 검색
   - 메타데이터 필터링 지원
   - JSON 백업 (검색 결과 참조용)
```

---

**"왜 개인별로 그룹핑했나요?"**

```
벡터 검색의 특성 때문입니다.

예를 들어:
- 질문: "모바일 개발에서 백엔드로 전환한 선배 사례"
- 각 행 개별 검색: 모바일 OR 백엔드 (문맥 없음)
- 개인별 통합: 모바일 → 백엔드 전환 스토리 (문맥 有)

→ 개인별 통합 문서가 의미적으로 더 유사함
```

---

**작성자:** 양승우
**최종 수정일:** 2025.07.01
