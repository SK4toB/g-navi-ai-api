#!/usr/bin/env python3
"""
외부 트렌드 검색 로직 제거 확인 테스트
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.graphs.nodes.data_retrieval import DataRetrievalNode
from app.graphs.nodes.message_check import MessageCheckNode

async def test_external_trends_removal():
    """외부 트렌드 검색 로직이 제거되었는지 테스트"""
    
    print("=== 외부 트렌드 검색 로직 제거 확인 테스트 ===\n")
    
    # 1. 메시지 체크 노드에서 external_trends 초기화 확인
    print("1. 메시지 체크 노드 테스트...")
    message_check_node = MessageCheckNode()
    message_check_func = message_check_node.create_node()
    
    state = {"user_question": "프론트엔드 개발자가 되고 싶어요"}
    result_state = await message_check_func(state)
    
    print(f"   - external_trends 키 존재: {'external_trends' in result_state}")
    if 'external_trends' in result_state:
        print(f"   ❌ external_trends가 여전히 초기화되고 있음")
    else:
        print(f"   ✅ external_trends 초기화 제거됨")
    
    # 2. 데이터 검색 노드에서 external_trends 설정 확인
    print("\n2. 데이터 검색 노드 테스트...")
    data_retrieval_node = DataRetrievalNode()
    
    # 테스트용 상태 설정
    test_state = {
        "user_question": "AI 개발자가 되고 싶어요",
        "intent_analysis": {"intent": "career_consultation", "career_history": ["AI", "개발"]},
        "processing_log": [],
        "error_messages": []
    }
    
    try:
        result_state = data_retrieval_node.retrieve_additional_data_node(test_state)
        
        print(f"   - external_trends 키 존재: {'external_trends' in result_state}")
        if 'external_trends' in result_state:
            print(f"   - external_trends 값: {result_state['external_trends']}")
            print(f"   ❌ external_trends가 여전히 설정되고 있음")
        else:
            print(f"   ✅ external_trends 설정 제거됨")
        
        # 다른 필드들은 정상적으로 설정되었는지 확인
        print(f"   - career_cases 존재: {'career_cases' in result_state}")
        print(f"   - education_courses 존재: {'education_courses' in result_state}")
        
    except Exception as e:
        print(f"   ❌ 데이터 검색 노드 테스트 실패: {e}")
        return False
    
    # 3. 전체 결과 확인
    print("\n=== 테스트 결과 ===")
    external_trends_removed = 'external_trends' not in result_state
    
    if external_trends_removed:
        print("✅ 외부 트렌드 검색 로직이 성공적으로 제거되었습니다!")
        print("\n📋 변경 사항:")
        print("   - message_check.py: external_trends 초기화 제거")
        print("   - data_retrieval.py: external_trends 설정 및 참조 제거")
        print("   - 현재 데이터 검색: 커리어 사례 + 교육과정만 포함")
        return True
    else:
        print("❌ 외부 트렌드 검색 로직이 완전히 제거되지 않았습니다.")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_external_trends_removal())
    sys.exit(0 if result else 1)
