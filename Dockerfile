ARG BASE_IMAGE_TAG=1.0.0
FROM amdp-registry.skala-ai.com/skala25a/sk-gnavi4-ai-base:${BASE_IMAGE_TAG}

# 애플리케이션 코드 복사
COPY app/ ./app/

# 권한 설정
RUN chown -R appuser:appuser /app
USER appuser

# 포트 노출 및 실행
EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]