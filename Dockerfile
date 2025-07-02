# 최적화된 메인 애플리케이션 Dockerfile
ARG BASE_IMAGE_TAG=latest
FROM amdp-registry.skala-ai.com/skala25a/sk-gnavi4-ai-base:${BASE_IMAGE_TAG}

# 애플리케이션 코드 복사
COPY app/ ./app/

# 소유권 변경
RUN chown -R appuser:appuser /app

# 비루트 사용자로 전환
USER appuser

# 포트 노출
EXPOSE 8001

# 헬스체크
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# 애플리케이션 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]