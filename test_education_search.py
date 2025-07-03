#!/usr/bin/env python3
import sys
import os
sys.path.append('/Users/ijaewon/4toB/g-navi-ai-api')

from app.graphs.agents.retriever import CareerEnsembleRetrieverAgent

# 교육과정 검색 테스트
retriever = CareerEnsembleRetrieverAgent()

test_query = "클라우드 아키텍처 학습"
test_user_profile = {
    "skills": ["Python", "AWS", "Backend Development"],
    "experience": "5년차 개발자",
    "domain": "IT"
}
test_intent_analysis = {
    "intent": "course_recommendation",
    "career_history": ["Cloud Computing", "DevOps"]
}

print("교육과정 검색 테스트 시작...")

# 15개 검색 테스트
result = retriever.search_education_courses(
    query=test_query,
    user_profile=test_user_profile,
    intent_analysis=test_intent_analysis,
    max_results=15
)

print(f"\n검색 결과:")
print(f"- 총 추천 과정 수: {len(result.get('recommended_courses', []))}")
if result.get('recommended_courses'):
    for i, course in enumerate(result['recommended_courses'][:5], 1):
        print(f"  {i}. {course.get('title', '제목 없음')} ({course.get('source', '소스 없음')})")
    if len(result['recommended_courses']) > 5:
        print(f"  ... 외 {len(result['recommended_courses']) - 5}개 더")

print("\n✅ 교육과정 검색 테스트 완료")
