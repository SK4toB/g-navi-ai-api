# Python 버전
FROM python:3.10-slim

WORKDIR /app

# # 시스템 의존성 설치 (필요시)
# RUN apt-get update && apt-get install -y \
#     curl \
#     && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY app/ ./app/

# .env 파일 복사 (선택사항 - 환경변수로 대체 권장)
# COPY .env .

# 포트를 FastAPI 기본 포트에 맞게 변경
EXPOSE 8001

# # 헬스체크 추가
# HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
#     CMD curl -f http://localhost:8001/health || exit 1

# # 비루트 사용자 생성 (보안)
# RUN adduser --disabled-password --gecos '' appuser
# RUN chown -R appuser:appuser /app
# USER appuser

# 애플리케이션 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]