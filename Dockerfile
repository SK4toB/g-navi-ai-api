# FastAPI 멀티스테이지 Dockerfile
FROM python:3.10-slim as builder

# 빌드 단계에서 필요한 패키지 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 의존성 파일만 먼저 복사 (캐시 최적화)
COPY requirements.txt .

# 의존성 설치
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 프로덕션 스테이지
FROM python:3.10-slim

# 런타임에 필요한 최소 패키지만 설치
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 작업 디렉토리 설정
WORKDIR /app

# 빌더 스테이지에서 설치된 패키지 복사
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 애플리케이션 코드 복사
COPY app/ ./app/

# 환경변수 설정
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 비루트 사용자 생성 (보안)
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app

USER appuser

# 포트 노출
EXPOSE 8001

# 헬스체크
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# 애플리케이션 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]