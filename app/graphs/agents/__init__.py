# app/graphs/nodes/__init__.py
# G.Navi AgentRAG 시스템용 노드 모듈

"""
G.Navi AgentRAG 시스템에서는 개별 노드들을 사용하지 않고
ChatGraphBuilder 내부에서 직접 노드 함수들을 정의합니다.

4단계 AgentRAG 워크플로우:
1. retrieve_chat_history - 과거 대화내역 검색
2. analyze_intent - 의도 분석 및 상황 이해  
3. retrieve_additional_data - 추가 데이터 검색 (커리어 사례 + 트렌드)
4. format_response - 적응적 응답 포맷팅

기존 개별 노드들은 더 이상 사용하지 않습니다.
"""

__all__ = []