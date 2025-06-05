# app/test_integration.py
import asyncio
import sys
import os

# 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_openai_connection():
    """OpenAI 연결 테스트"""
    print("=== OpenAI 연결 테스트 ===")
    
    try:
        from services.openai_service import OpenAIService
        
        service = OpenAIService()
        
        # API 키 검증
        if not service.validate_api_key():
            print("❌ API 키가 유효하지 않습니다.")
            return False
        
        print("✅ API 키 유효성 확인")
        
        # 연결 테스트
        result = await service.test_connection()
        
        if result["status"] == "success":
            print(f"✅ OpenAI 연결 성공")
            print(f"   모델: {result['model']}")
            print(f"   응답 길이: {result['response_length']}자")
            return True
        else:
            print(f"❌ OpenAI 연결 실패: {result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ OpenAI 테스트 중 오류: {e}")
        return False

async def test_vector_db():
    """벡터 DB 연결 테스트"""
    print("\n=== ChromaDB 연결 테스트 ===")
    
    try:
        from services.vector_db_service import query_vector, collection
        
        # 컬렉션 상태 확인
        count = collection.count()
        print(f"✅ ChromaDB 연결 성공")
        print(f"   총 벡터 수: {count}개")
        
        # 간단한 검색 테스트
        test_query = "개발자 경험"
        results = query_vector(test_query, top_k=3)
        
        if results and results.get('documents'):
            docs_count = len(results['documents'][0])
            print(f"✅ 벡터 검색 성공")
            print(f"   검색 결과: {docs_count}개")
            return True
        else:
            print("❌ 벡터 검색 결과 없음")
            return False
            
    except Exception as e:
        print(f"❌ ChromaDB 테스트 중 오류: {e}")
        return False

async def test_rag_service():
    """RAG 서비스 통합 테스트"""
    print("\n=== RAG 서비스 통합 테스트 ===")
    
    try:
        from services.rag_service import RAGService
        
        service = RAGService()
        
        # 테스트 질문
        test_question = "시니어 개발자가 되려면 어떤 준비를 해야 하나요?"
        
        print(f"질문: {test_question}")
        print("답변 생성 중...")
        
        result = await service.generate_answer(test_question, top_k=3)
        
        if "error" in result:
            print(f"❌ RAG 서비스 오류: {result['error']}")
            return False
        
        print("✅ RAG 서비스 성공")
        print(f"   신뢰도: {result['confidence']:.3f}")
        print(f"   소스 개수: {len(result['sources'])}개")
        print(f"   답변 길이: {len(result['answer'])}자")
        
        # 답변 일부 출력
        answer_preview = result['answer'][:200] + "..." if len(result['answer']) > 200 else result['answer']
        print(f"   답변 미리보기: {answer_preview}")
        
        return True
        
    except Exception as e:
        print(f"❌ RAG 서비스 테스트 중 오류: {e}")
        return False

async def test_api_endpoint():
    """API 엔드포인트 테스트"""
    print("\n=== API 엔드포인트 테스트 ===")
    
    try:
        import httpx
        
        # 서버가 실행 중인지 확인
        async with httpx.AsyncClient() as client:
            try:
                # 헬스 체크
                response = await client.get("http://localhost:8000/health")
                if response.status_code == 200:
                    print("✅ 서버 연결 성공")
                else:
                    print(f"❌ 서버 응답 오류: {response.status_code}")
                    return False
                
                # RAG 엔드포인트 테스트
                test_data = {
                    "question": "Python 개발 경험이 필요한가요?",
                    "top_k": 3
                }
                
                response = await client.post(
                    "http://localhost:8000/api/v1/rag/simple-chat",
                    json=test_data
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print("✅ RAG 엔드포인트 성공")
                    print(f"   응답 데이터 키: {list(data.keys())}")
                    return True
                else:
                    print(f"❌ RAG 엔드포인트 오류: {response.status_code}")
                    print(f"   응답: {response.text}")
                    return False
                    
            except httpx.ConnectError:
                print("❌ 서버가 실행되지 않았습니다.")
                print("   먼저 'python -m app.main'으로 서버를 시작하세요.")
                return False
                
    except ImportError:
        print("⚠️  httpx가 설치되지 않아 API 테스트를 건너뜁니다.")
        print("   'pip install httpx'로 설치 후 다시 테스트하세요.")
        return None

async def main():
    """전체 통합 테스트 실행"""
    print("🚀 지나비 프로젝트 통합 테스트 시작\n")
    
    tests = [
        ("OpenAI 연결", test_openai_connection),
        ("ChromaDB 연결", test_vector_db),
        ("RAG 서비스", test_rag_service),
        ("API 엔드포인트", test_api_endpoint)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ {test_name} 테스트 중 예외 발생: {e}")
            results[test_name] = False
    
    # 최종 결과 요약
    print("\n" + "="*50)
    print("📊 테스트 결과 요약")
    print("="*50)
    
    success_count = 0
    total_count = 0
    
    for test_name, result in results.items():
        if result is True:
            print(f"✅ {test_name}: 성공")
            success_count += 1
        elif result is False:
            print(f"❌ {test_name}: 실패")
        else:
            print(f"⚠️  {test_name}: 건너뜀")
            continue
        total_count += 1
    
    print(f"\n성공률: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
    
    if success_count == total_count:
        print("🎉 모든 테스트가 성공했습니다!")
    else:
        print("⚠️  일부 테스트가 실패했습니다. 위 결과를 확인하세요.")

if __name__ == "__main__":
    asyncio.run(main())