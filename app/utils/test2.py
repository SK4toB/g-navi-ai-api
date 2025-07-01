import requests

# 🔧 수정: 내부 ChromaDB URL로 변경
base_urls = [
    "http://localhost:8000",  # 포트포워딩용
    "http://chromadb-1-0:8000",  # Pod 직접 접근
    "http://chromadb-1-0.sk-team-04.svc.cluster.local:8000",  # K8s FQDN
]

# 🔧 수정: v2 API 엔드포인트 (인증 없음)
endpoints = [
    "/api/v2/heartbeat",
    "/api/v2/collections", 
    "/api/v2/version",
    "/api/v1/heartbeat",  # 폴백용
    "/api/v1/collections"
]

print("🔍 ChromaDB v2 API 테스트 (인증 없음)")
print("=" * 50)

for base_url in base_urls:
    print(f"\n📡 {base_url}")
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            
            if response.status_code == 200:
                print(f"   ✅ {endpoint}: {response.status_code}")
                try:
                    json_data = response.json()
                    if "collections" in endpoint and isinstance(json_data, list):
                        print(f"      📚 컬렉션 수: {len(json_data)}")
                    else:
                        print(f"      📄 {json_data}")
                except:
                    print(f"      📄 {response.text[:100]}")
            else:
                print(f"   ❌ {endpoint}: {response.status_code} - {response.text[:100]}")
                
        except Exception as e:
            print(f"   ❌ {endpoint}: 에러 - {e}")
    
    print()  # 빈 줄

print("💡 포트포워딩으로 테스트하려면:")
print("kubectl port-forward chromadb-1-0 8000:8000 -n sk-team-04")