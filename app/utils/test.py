import requests
import base64

# 인증 정보
credentials = "skala:Skala25a!23$"
auth_header = f"Basic {base64.b64encode(credentials.encode()).decode()}"

# API 테스트
endpoints = [
    "/api/v1/heartbeat",
    "/api/v1/collections", 
    "/api/v2/heartbeat",
    "/api/v2/collections"
]

base_url = "https://chromadb-1.skala25a.project.skala-ai.com"

for endpoint in endpoints:
    try:
        response = requests.get(f"{base_url}{endpoint}", 
                              headers={"Authorization": auth_header}, 
                              timeout=10)
        print(f"{endpoint}: {response.status_code} - {response.text[:200]}")
    except Exception as e:
        print(f"{endpoint}: 에러 - {e}")