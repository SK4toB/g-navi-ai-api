# app/test_api_detailed.py
import asyncio
import sys
import os

# 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_api_endpoints():
    """API 엔드포인트 상세 테스트"""
    
    print("🔍 API 엔드포인트 상세 테스트 시작")
    print("=" * 50)
    
    try:
        import httpx
    except ImportError:
        print("❌ httpx가 설치되지 않았습니다.")
        print("pip install httpx 실행 후 다시 시도하세요.")
        return
    
    base_url = "http://localhost:8000"
    
    # 테스트할 엔드포인트들
    endpoints = [
        {
            "name": "루트 엔드포인트",
            "method": "GET",
            "url": f"{base_url}/",
            "data": None
        },
        {
            "name": "헬스 체크",
            "method": "GET", 
            "url": f"{base_url}/health",
            "data": None
        },
        {
            "name": "API v1 헬스",
            "method": "GET",
            "url": f"{base_url}/api/v1/health",
            "data": None
        },
        {
            "name": "RAG 헬스",
            "method": "GET",
            "url": f"{base_url}/api/v1/rag/health",
            "data": None
        },
        {
            "name": "벡터 검색만",
            "method": "POST",
            "url": f"{base_url}/api/v1/rag/search-cases",
            "data": {
                "question": "개발자 경험",
                "top_k": 3
            }
        },
        {
            "name": "RAG 채팅",
            "method": "POST", 
            "url": f"{base_url}/api/v1/rag/simple-chat",
            "data": {
                "question": "Python 개발 경험이 필요한가요?",
                "top_k": 3
            }
        }
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for endpoint in endpoints:
            print(f"\n🔗 테스트: {endpoint['name']}")
            print(f"   URL: {endpoint['url']}")
            
            try:
                if endpoint['method'] == 'GET':
                    response = await client.get(endpoint['url'])
                else:
                    response = await client.post(
                        endpoint['url'],
                        json=endpoint['data'],
                        headers={"Content-Type": "application/json"}
                    )
                
                print(f"   상태 코드: {response.status_code}")
                
                if response.status_code == 200:
                    print("   ✅ 성공")
                    try:
                        data = response.json()
                        if isinstance(data, dict):
                            print(f"   응답 키: {list(data.keys())}")
                            
                            # 특별한 응답 확인
                            if 'answer' in data:
                                answer_len = len(data['answer'])
                                print(f"   답변 길이: {answer_len}자")
                    except:
                        print(f"   응답 길이: {len(response.text)}자")
                        
                else:
                    print(f"   ❌ 실패: {response.status_code}")
                    print(f"   에러 응답: {response.text[:200]}...")
                    
            except httpx.ConnectError:
                print(f"   ❌ 연결 실패: 서버가 실행되지 않았습니다")
                break
            except httpx.TimeoutException:
                print(f"   ❌ 타임아웃: 30초 초과")
            except Exception as e:
                print(f"   ❌ 예외 발생: {str(e)}")

async def test_specific_rag_endpoint():
    """RAG 엔드포인트 집중 테스트"""
    
    print(f"\n🎯 RAG 엔드포인트 집중 테스트")
    print("=" * 30)
    
    try:
        import httpx
        
        url = "http://localhost:8000/api/v1/rag/simple-chat"
        data = {
            "question": "시니어 개발자가 되려면 어떤 준비를 해야 하나요?",
            "top_k": 3
        }
        
        print(f"URL: {url}")
        print(f"데이터: {data}")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            print("요청 전송 중...")
            
            response = await client.post(
                url,
                json=data,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"응답 상태: {response.status_code}")
            print(f"응답 헤더: {dict(response.headers)}")
            
            if response.status_code == 200:
                result = response.json()
                print("✅ 성공!")
                print(f"답변: {result.get('answer', 'N/A')[:100]}...")
                print(f"소스 수: {len(result.get('sources', []))}")
                print(f"신뢰도: {result.get('confidence', 'N/A')}")
            else:
                print("❌ 실패!")
                print(f"에러 응답: {response.text}")
                
    except Exception as e:
        print(f"❌ 예외 발생: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_api_endpoints())
    asyncio.run(test_specific_rag_endpoint())