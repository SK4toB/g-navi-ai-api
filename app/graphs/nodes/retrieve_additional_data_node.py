# G.Navi 3단계: 추가 데이터 수집 (커리어 사례 + 트렌드 정보)

from app.graphs.state import ChatState

async def process(state: ChatState) -> ChatState:
    """G.Navi 3단계: 추가 데이터 수집"""
    print("=== G.Navi 3단계: 추가 데이터 수집 ===")
    
    # TODO: 커리어 사례 검색 로직 구현
    state["career_cases"] = []
    
    # TODO: 트렌드 정보 수집 로직 구현
    state["external_trends"] = []
    
    return state